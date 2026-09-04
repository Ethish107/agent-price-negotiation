from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from ..database import get_db

from ..models import (
    Negotiation,
    Product,
    Round
)

from ..schemas import (
    NegotiationCreate,
    NegotiationResponse,
    NegotiationDetailResponse
)

from ..services.negotiation_engine import (
    run_negotiation
)

from ..services.razorpay_service import (
    create_payment_link
)


router = APIRouter(
    prefix="/negotiations",
    tags=["Negotiations"]
)


# Maximum amount that can ever be sent to Razorpay.
# This is a Python-side safety guardrail.
MAX_TRANSACTION_AMOUNT = 500000


@router.post(
    "/",
    response_model=NegotiationResponse
)
def create_negotiation(
    data: NegotiationCreate,
    db: Session = Depends(get_db)
):

    # ==========================================
    # FIND PRODUCT
    # ==========================================

    product = (
        db.query(Product)
        .filter(
            Product.id == data.product_id
        )
        .first()
    )

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )


    # ==========================================
    # VALIDATE BUYER
    # ==========================================

    if (
        data.buyer_target
        > data.buyer_budget
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Buyer target cannot be "
                "greater than buyer budget"
            )
        )


    # ==========================================
    # VALIDATE TRANSACTION LIMIT
    # ==========================================

    if data.buyer_budget > MAX_TRANSACTION_AMOUNT:

        raise HTTPException(
            status_code=400,
            detail=(
                "Buyer budget exceeds the "
                "maximum transaction amount"
            )
        )


    # ==========================================
    # CREATE NEGOTIATION
    # ==========================================

    negotiation = Negotiation(

        product_id=data.product_id,

        buyer_target=data.buyer_target,

        buyer_budget=data.buyer_budget,

        persona=data.persona,

        max_rounds=data.max_rounds,

        status="in_progress",

        payment_status="not_created"
    )

    db.add(
        negotiation
    )

    db.commit()

    db.refresh(
        negotiation
    )


    # ==========================================
    # RUN NEGOTIATION
    # ==========================================

    run_negotiation(

        negotiation=negotiation,

        product=product,

        db=db
    )


    db.refresh(
        negotiation
    )


    # ==========================================
    # CREATE PAYMENT LINK ONLY IF AGREED
    # ==========================================

    if negotiation.status == "agreed":

        agreed_price = negotiation.agreed_price


        # --------------------------------------
        # SAFETY CHECK
        # --------------------------------------

        if agreed_price is None:

            negotiation.status = "rejected"

            negotiation.payment_status = "not_created"

            db.commit()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Negotiation was marked agreed "
                    "but no agreed price was recorded"
                )
            )


        # --------------------------------------
        # BUYER BUDGET CHECK
        # --------------------------------------

        if agreed_price > negotiation.buyer_budget:

            negotiation.status = "rejected"

            negotiation.agreed_price = None

            negotiation.payment_status = "not_created"

            db.commit()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Agreed price exceeds buyer budget"
                )
            )


        # --------------------------------------
        # MAX TRANSACTION CHECK
        # --------------------------------------

        if agreed_price > MAX_TRANSACTION_AMOUNT:

            negotiation.status = "rejected"

            negotiation.agreed_price = None

            negotiation.payment_status = "not_created"

            db.commit()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Agreed price exceeds maximum "
                    "transaction amount"
                )
            )


        # --------------------------------------
        # RAZORPAY PAYMENT LINK
        # --------------------------------------

        try:

            payment_link = create_payment_link(

                amount=agreed_price,

                negotiation_id=negotiation.id,

                product_name=product.name
            )

        except Exception as exc:

            print(
                "[RAZORPAY] Payment link creation failed:",
                exc
            )

            negotiation.payment_status = "failed"

            db.commit()

            raise HTTPException(
                status_code=502,
                detail=(
                    "Negotiation succeeded but "
                    "Razorpay payment link creation failed"
                )
            )


        # --------------------------------------
        # SAVE PAYMENT INFORMATION
        # --------------------------------------

        negotiation.payment_link_id = (
            payment_link["id"]
        )

        negotiation.payment_link_url = (
            payment_link["short_url"]
        )

        negotiation.payment_status = "created"

        db.commit()

        db.refresh(
            negotiation
        )


    # ==========================================
    # RETURN NEGOTIATION
    # ==========================================

    return negotiation


@router.get(
    "/",
    response_model=list[NegotiationResponse]
)
def get_negotiations(
    db: Session = Depends(get_db)
):

    return (
        db.query(
            Negotiation
        ).all()
    )


@router.get(
    "/{negotiation_id}",
    response_model=NegotiationDetailResponse
)
def get_negotiation(
    negotiation_id: int,
    db: Session = Depends(get_db)
):

    negotiation = (
        db.query(Negotiation)
        .filter(
            Negotiation.id
            == negotiation_id
        )
        .first()
    )


    if not negotiation:

        raise HTTPException(
            status_code=404,
            detail="Negotiation not found"
        )


    rounds = (
        db.query(Round)
        .filter(
            Round.negotiation_id
            == negotiation_id
        )
        .order_by(
            Round.round_no,
            Round.id
        )
        .all()
    )


    result = (
        NegotiationDetailResponse
        .model_validate(
            negotiation
        )
    )


    result.rounds = rounds


    return result