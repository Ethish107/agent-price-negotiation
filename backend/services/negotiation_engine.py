from sqlalchemy.orm import Session

from ..models import Negotiation, Product, Round, Sale

from .buyer_agent import generate_buyer_offer
from .merchant_agent import evaluate_offer
from .guardrails import validate_merchant_decision
from .pricing_engine import build_pricing_context


MAX_TRANSACTION_AMOUNT = 500000


def run_negotiation(
    negotiation: Negotiation,
    product: Product,
    db: Session
):
    # =========================================================
    # LOAD HISTORICAL SALES
    # =========================================================

    sales = (
        db.query(Sale)
        .filter(
            Sale.product_id == product.id
        )
        .all()
    )

    # =========================================================
    # BUILD DATA-DRIVEN PRICING CONTEXT
    # =========================================================

    pricing_context = build_pricing_context(
        product=product,
        sales=sales
    )

    print("\n================================")
    print("PRICING CONTEXT")
    print(pricing_context)
    print("================================\n")

    previous_merchant_offer = None

    # =========================================================
    # NEGOTIATION LOOP
    # =========================================================

    for round_no in range(
        1,
        negotiation.max_rounds + 1
    ):

        # =====================================================
        # BUYER AGENT
        # =====================================================

        buyer_result = generate_buyer_offer(
            target=negotiation.buyer_target,
            budget=negotiation.buyer_budget,
            round_no=round_no,
            max_rounds=negotiation.max_rounds,
            persona=negotiation.persona,
            previous_merchant_offer=previous_merchant_offer
        )

        buyer_action = buyer_result["action"]
        buyer_offer = buyer_result.get(
            "offer_amount"
        )

        print("\n[BUYER DECISION]")
        print(
            f"Action: {buyer_action}"
        )
        print(
            f"Offer: ₹{buyer_offer:,.2f}"
            if buyer_offer is not None
            else "Offer: None"
        )
        print(
            f"Reasoning: "
            f"{buyer_result['reasoning']}"
        )

        # =====================================================
        # BUYER ACCEPTS MERCHANT OFFER
        # =====================================================

        if buyer_action == "accept":

            negotiation.status = "agreed"
            negotiation.agreed_price = buyer_offer

            buyer_round = Round(
                negotiation_id=negotiation.id,
                round_no=round_no,
                actor="buyer",
                offer_amount=buyer_offer,
                action="accept",
                reasoning=buyer_result[
                    "reasoning"
                ]
            )

            db.add(buyer_round)
            db.commit()

            return negotiation

        # =====================================================
        # BUYER REJECTS / WALKS AWAY
        # =====================================================

        if buyer_action == "reject":

            negotiation.status = "rejected"

            buyer_round = Round(
                negotiation_id=negotiation.id,
                round_no=round_no,
                actor="buyer",
                offer_amount=None,
                action="reject",
                reasoning=buyer_result[
                    "reasoning"
                ]
            )

            db.add(buyer_round)
            db.commit()

            return negotiation

        # =====================================================
        # BUYER COUNTER
        # =====================================================

        # Safety check:
        # Buyer must never offer above its budget.

        if buyer_offer is None:

            negotiation.status = "rejected"

            buyer_round = Round(
                negotiation_id=negotiation.id,
                round_no=round_no,
                actor="buyer",
                offer_amount=None,
                action="reject",
                reasoning=(
                    "Buyer decision was invalid because "
                    "no offer amount was provided."
                )
            )

            db.add(buyer_round)
            db.commit()

            return negotiation

        if buyer_offer > negotiation.buyer_budget:

            negotiation.status = "rejected"

            buyer_round = Round(
                negotiation_id=negotiation.id,
                round_no=round_no,
                actor="buyer",
                offer_amount=None,
                action="reject",
                reasoning=(
                    "Buyer offer blocked by guardrail: "
                    "offer exceeds buyer budget."
                )
            )

            db.add(buyer_round)
            db.commit()

            return negotiation

        buyer_round = Round(
            negotiation_id=negotiation.id,
            round_no=round_no,
            actor="buyer",
            offer_amount=buyer_offer,
            action="offer",
            reasoning=buyer_result[
                "reasoning"
            ]
        )

        db.add(buyer_round)
        db.commit()

        # =====================================================
        # MERCHANT AGENT
        # =====================================================

        merchant_result = evaluate_offer(
            offer_amount=buyer_offer,
            list_price=product.list_price,
            floor_price=product.floor_price,
            round_no=round_no,
            max_rounds=negotiation.max_rounds,
            pricing_context=pricing_context,
            buyer_persona=negotiation.persona
        )

        # =====================================================
        # MERCHANT GUARDRAILS
        # =====================================================

        merchant_result = validate_merchant_decision(
            decision=merchant_result,
            floor_price=product.floor_price,
            max_transaction_amount=MAX_TRANSACTION_AMOUNT
        )

        merchant_action = merchant_result["action"]

        merchant_offer = merchant_result.get(
            "offer_amount"
        )

        # =====================================================
        # SAVE MERCHANT ROUND
        # =====================================================

        merchant_round = Round(
            negotiation_id=negotiation.id,
            round_no=round_no,
            actor="merchant",
            offer_amount=merchant_offer,
            action=merchant_action,
            reasoning=merchant_result[
                "reasoning"
            ]
        )

        db.add(merchant_round)
        db.commit()

        # =====================================================
        # MERCHANT ACCEPTS
        # =====================================================

        if merchant_action == "accept":

            negotiation.status = "agreed"
            negotiation.agreed_price = merchant_offer

            db.commit()

            return negotiation

        # =====================================================
        # MERCHANT REJECTS
        # =====================================================

        if merchant_action == "reject":

            negotiation.status = "rejected"

            db.commit()

            return negotiation

        # =====================================================
        # MERCHANT COUNTERS
        # =====================================================

        previous_merchant_offer = merchant_offer

    # =========================================================
    # MAXIMUM ROUNDS REACHED
    # =========================================================

    negotiation.status = "escalated"

    db.commit()

    return negotiation