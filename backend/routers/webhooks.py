import json

import razorpay

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request
)

from sqlalchemy.orm import Session

from ..config import (
    RAZORPAY_WEBHOOK_SECRET
)

from ..database import get_db

from ..models import (
    Negotiation,
    Product,
    Sale
)


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


# ==========================================
# RAZORPAY CLIENT
# ==========================================

client = razorpay.Client()


# ==========================================
# RAZORPAY WEBHOOK
# ==========================================

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):

    # ==========================================
    # READ RAW REQUEST BODY
    # ==========================================

    body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:

        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature"
        )


    # ==========================================
    # VERIFY WEBHOOK SIGNATURE
    # ==========================================

    try:

        client.utility.verify_webhook_signature(
            body.decode("utf-8"),
            signature,
            RAZORPAY_WEBHOOK_SECRET
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature"
        )


    # ==========================================
    # PARSE EVENT
    # ==========================================

    try:

        payload = json.loads(
            body.decode("utf-8")
        )

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )


    event = payload.get(
        "event"
    )


    print(
        f"[RAZORPAY WEBHOOK] Event: {event}"
    )


    # ==========================================
    # ONLY PROCESS PAYMENT CAPTURE
    # ==========================================

    if event != "payment.captured":

        return {
            "status": "ignored",
            "event": event
        }


    # ==========================================
    # EXTRACT PAYMENT DATA
    # ==========================================

    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )


    payment_id = payment_entity.get(
        "id"
    )

    payment_link_id = payment_entity.get(
        "payment_link_id"
    )


    if not payment_link_id:

        print(
            "[RAZORPAY WEBHOOK] "
            "No payment_link_id found."
        )

        return {
            "status": "ignored",
            "reason": "No payment_link_id"
        }


    # ==========================================
    # FIND NEGOTIATION
    # ==========================================

    negotiation = (
        db.query(Negotiation)
        .filter(
            Negotiation.payment_link_id
            == payment_link_id
        )
        .first()
    )


    if not negotiation:

        raise HTTPException(
            status_code=404,
            detail="Negotiation for payment link not found"
        )


    # ==========================================
    # IDEMPOTENCY CHECK
    # ==========================================

    if negotiation.payment_status == "paid":

        print(
            "[RAZORPAY WEBHOOK] "
            f"Negotiation {negotiation.id} "
            "already marked as paid."
        )

        return {
            "status": "already_processed",
            "negotiation_id": negotiation.id
        }


    # ==========================================
    # VALIDATE AGREEMENT
    # ==========================================

    if negotiation.status != "agreed":

        raise HTTPException(
            status_code=400,
            detail=(
                "Payment received for a negotiation "
                "that is not agreed"
            )
        )


    if negotiation.agreed_price is None:

        raise HTTPException(
            status_code=400,
            detail="Negotiation has no agreed price"
        )


    # ==========================================
    # VALIDATE PAYMENT AMOUNT
    # ==========================================

    expected_amount = int(
        round(
            negotiation.agreed_price * 100
        )
    )

    received_amount = payment_entity.get(
        "amount"
    )


    if received_amount != expected_amount:

        print(
            "[RAZORPAY WEBHOOK] Amount mismatch:"
        )

        print(
            f"Expected: {expected_amount}"
        )

        print(
            f"Received: {received_amount}"
        )

        raise HTTPException(
            status_code=400,
            detail="Payment amount does not match agreed price"
        )


    # ==========================================
    # FIND PRODUCT
    # ==========================================

    product = (
        db.query(Product)
        .filter(
            Product.id
            == negotiation.product_id
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )


    # ==========================================
    # INVENTORY CHECK
    # ==========================================

    if product.current_inventory <= 0:

        raise HTTPException(
            status_code=400,
            detail="Product is out of inventory"
        )


    # ==========================================
    # CREATE SALE
    # ==========================================

    sale = Sale(

        product_id=product.id,

        final_price=negotiation.agreed_price,

        quantity=1,

        buyer_persona=negotiation.persona,

        negotiation_rounds=negotiation.max_rounds
    )


    db.add(
        sale
    )


    # ==========================================
    # UPDATE INVENTORY
    # ==========================================

    product.current_inventory -= 1


    # ==========================================
    # UPDATE NEGOTIATION
    # ==========================================

    negotiation.payment_status = "paid"


    # ==========================================
    # COMMIT EVERYTHING
    # ==========================================

    db.commit()


    print(
        "[RAZORPAY WEBHOOK] Payment processed:"
    )

    print(
        f"Negotiation: {negotiation.id}"
    )

    print(
        f"Payment: {payment_id}"
    )

    print(
        f"Amount: ₹{negotiation.agreed_price:,.2f}"
    )

    print(
        f"Inventory remaining: "
        f"{product.current_inventory}"
    )


    return {
        "status": "processed",
        "negotiation_id": negotiation.id,
        "payment_id": payment_id,
        "amount": negotiation.agreed_price
    }