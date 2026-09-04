import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import RAZORPAY_WEBHOOK_SECRET
from ..database import get_db
from ..models import Negotiation, Product, Round, Sale


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


def verify_signature(
    body: bytes,
    signature: str
) -> bool:
    """
    Verify that the webhook request
    was sent by Razorpay.
    """

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature
    )


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Razorpay webhook events.

    Currently handles:
        payment.captured
    """

    # ---------------------------------------------------------
    # 1. Read raw request body
    # ---------------------------------------------------------

    body = await request.body()

    # ---------------------------------------------------------
    # 2. Get Razorpay signature
    # ---------------------------------------------------------

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature"
        )

    # ---------------------------------------------------------
    # 3. Verify signature
    # ---------------------------------------------------------

    if not verify_signature(
        body,
        signature
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature"
        )

    # ---------------------------------------------------------
    # 4. Parse JSON
    # ---------------------------------------------------------

    try:
        payload = json.loads(
            body.decode("utf-8")
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )

    event = payload.get("event")

    print(
        f"[RAZORPAY WEBHOOK] Event received: {event}"
    )

    # ---------------------------------------------------------
    # 5. Ignore unsupported events
    # ---------------------------------------------------------

    if event != "payment.captured":
        return {
            "status": "ignored",
            "event": event
        }

    # ---------------------------------------------------------
    # 6. Extract payment entity
    # ---------------------------------------------------------

    try:
        payment_entity = (
            payload["payload"]
            ["payment"]
            ["entity"]
        )

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment payload"
        )

    payment_id = payment_entity.get("id")

    payment_amount_paise = payment_entity.get(
        "amount"
    )

    payment_status = payment_entity.get(
        "status"
    )

    # ---------------------------------------------------------
    # 7. Validate payment status
    # ---------------------------------------------------------

    if payment_status != "captured":
        return {
            "status": "ignored",
            "reason": "Payment is not captured"
        }

    if payment_amount_paise is None:
        raise HTTPException(
            status_code=400,
            detail="Payment amount missing"
        )

    payment_amount = (
        payment_amount_paise / 100
    )

    # ---------------------------------------------------------
    # 8. Extract payment-link information
    # ---------------------------------------------------------

    payment_link_id = payment_entity.get(
        "payment_link_id"
    )

    notes = payment_entity.get(
        "notes"
    ) or {}

    negotiation_id = notes.get(
        "negotiation_id"
    )

    # ---------------------------------------------------------
    # 9. Find negotiation
    # ---------------------------------------------------------

    negotiation = None

    # Preferred:
    # negotiation ID stored in Razorpay notes.

    if negotiation_id:

        try:
            negotiation_id = int(
                negotiation_id
            )

        except (TypeError, ValueError):
            negotiation_id = None

        if negotiation_id:

            negotiation = (
                db.query(Negotiation)
                .filter(
                    Negotiation.id
                    == negotiation_id
                )
                .first()
            )

    # Fallback:
    # Find using Razorpay payment-link ID.

    if (
        negotiation is None
        and payment_link_id
    ):

        negotiation = (
            db.query(Negotiation)
            .filter(
                Negotiation.payment_link_id
                == payment_link_id
            )
            .first()
        )

    if negotiation is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation not found"
        )

    # ---------------------------------------------------------
    # 10. Idempotency protection
    # ---------------------------------------------------------

    # Razorpay can retry webhook delivery.
    # Do not process the same payment twice.

    if negotiation.payment_status == "paid":

        print(
            "[RAZORPAY WEBHOOK] "
            f"Payment already processed "
            f"for negotiation {negotiation.id}"
        )

        return {
            "status": "already_processed",
            "negotiation_id": negotiation.id,
            "payment_id": payment_id
        }

    # ---------------------------------------------------------
    # 11. Validate negotiation
    # ---------------------------------------------------------

    if negotiation.status != "agreed":
        raise HTTPException(
            status_code=400,
            detail=(
                "Payment received for a "
                "negotiation that is not agreed"
            )
        )

    if negotiation.agreed_price is None:
        raise HTTPException(
            status_code=400,
            detail="Negotiation has no agreed price"
        )

    # ---------------------------------------------------------
    # 12. Validate payment amount
    # ---------------------------------------------------------

    agreed_price = float(
        negotiation.agreed_price
    )

    expected_amount_paise = int(
        round(agreed_price * 100)
    )

    if payment_amount_paise != expected_amount_paise:

        print(
            "[RAZORPAY WEBHOOK] "
            f"Amount mismatch. "
            f"Expected ₹{agreed_price}, "
            f"received ₹{payment_amount}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Payment amount does not "
                "match agreed price"
            )
        )

    # ---------------------------------------------------------
    # 13. Find product
    # ---------------------------------------------------------

    product = (
        db.query(Product)
        .filter(
            Product.id
            == negotiation.product_id
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # ---------------------------------------------------------
    # 14. Check inventory
    # ---------------------------------------------------------

    if product.current_inventory <= 0:
        raise HTTPException(
            status_code=400,
            detail="Product is out of stock"
        )

    # ---------------------------------------------------------
    # 15. Count ACTUAL negotiation rounds
    # ---------------------------------------------------------

    actual_rounds = (
        db.query(Round)
        .filter(
            Round.negotiation_id
            == negotiation.id
        )
        .count()
    )

    # ---------------------------------------------------------
    # 16. Create Sale
    # ---------------------------------------------------------

    sale = Sale(
        product_id=product.id,
        final_price=agreed_price,
        quantity=1,
        buyer_persona=negotiation.persona,
        negotiation_rounds=actual_rounds
    )

    db.add(sale)

    # ---------------------------------------------------------
    # 17. Decrease inventory
    # ---------------------------------------------------------

    product.current_inventory -= 1

    # ---------------------------------------------------------
    # 18. Mark payment as paid
    # ---------------------------------------------------------

    negotiation.payment_status = "paid"

    # ---------------------------------------------------------
    # 19. Commit atomically
    # ---------------------------------------------------------

    try:
        db.commit()

    except Exception as exc:
        db.rollback()

        print(
            "[RAZORPAY WEBHOOK] "
            f"Database error: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to record payment"
        )

    # ---------------------------------------------------------
    # 20. Log successful payment
    # ---------------------------------------------------------

    print(
        "[RAZORPAY WEBHOOK] "
        f"Payment successful | "
        f"negotiation={negotiation.id} | "
        f"payment={payment_id} | "
        f"amount=₹{agreed_price} | "
        f"rounds={actual_rounds}"
    )

    return {
        "status": "success",
        "negotiation_id": negotiation.id,
        "payment_id": payment_id,
        "amount": agreed_price,
        "rounds": actual_rounds
    }