def validate_merchant_decision(
    decision: dict,
    floor_price: float,
    max_transaction_amount: float
):
    action = decision["action"]
    offer_amount = decision.get("offer_amount")

    # Reject decisions don't need an amount
    if action == "reject":
        return decision

    # Every accept/counter must have a price
    if offer_amount is None:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Merchant decision was invalid because no "
                "offer amount was provided."
            )
        }

    # HARD FLOOR
    if offer_amount < floor_price:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Merchant decision blocked by guardrail: "
                "offer is below the hard floor price."
            )
        }

    # HARD TRANSACTION CEILING
    if offer_amount > max_transaction_amount:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Merchant decision blocked by guardrail: "
                "offer exceeds the maximum transaction amount."
            )
        }

    return decision