from .llm_service import generate_json_decision


def calculate_buyer_boundaries(
    target: float,
    budget: float,
    persona: str,
    round_no: int,
    max_rounds: int,
):
    acceptance_tolerance = {
        "price-sensitive": 0.03,
        "casual": 0.05,
        "urgent": 0.08,
    }.get(persona, 0.05)

    if round_no >= max_rounds:
        acceptance_tolerance += 0.03

    acceptance_price = min(
        target * (1 + acceptance_tolerance),
        budget
    )

    opening_discount = {
        "price-sensitive": 0.10,
        "casual": 0.07,
        "urgent": 0.03,
    }.get(persona, 0.07)

    opening_offer = min(
        target * (1 - opening_discount),
        budget
    )

    return {
        "acceptance_price": round(acceptance_price, 2),
        "opening_offer": round(opening_offer, 2),
    }


def calculate_buyer_strategy(
    target: float,
    budget: float,
    persona: str,
    previous_merchant_offer: float | None,
    round_no: int,
    max_rounds: int,
):
    """
    Deterministic buyer strategy.

    This is the fallback used when Gemini is unavailable.
    """

    boundaries = calculate_buyer_boundaries(
        target=target,
        budget=budget,
        persona=persona,
        round_no=round_no,
        max_rounds=max_rounds,
    )

    acceptance_price = boundaries["acceptance_price"]

    # ---------------------------------------------------------
    # Opening offer
    # ---------------------------------------------------------

    if previous_merchant_offer is None:

        return {
            "action": "counter",
            "offer_amount": boundaries["opening_offer"],
            "reasoning": (
                f"As a {persona} buyer, I am opening at "
                f"₹{boundaries['opening_offer']:,.2f}, "
                f"below my target of ₹{target:,.2f}."
            ),
        }

    merchant_offer = previous_merchant_offer

    # ---------------------------------------------------------
    # Merchant offer is acceptable
    # ---------------------------------------------------------

    if merchant_offer <= acceptance_price:

        return {
            "action": "accept",
            "offer_amount": merchant_offer,
            "reasoning": (
                f"The merchant's price of ₹{merchant_offer:,.2f} "
                f"is within my acceptable range of "
                f"₹{acceptance_price:,.2f}."
            ),
        }

    # ---------------------------------------------------------
    # No rounds remaining
    # ---------------------------------------------------------

    if round_no >= max_rounds:

        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                f"The merchant's price of ₹{merchant_offer:,.2f} "
                f"is above my acceptable price and no negotiation "
                f"rounds remain."
            ),
        }

    # ---------------------------------------------------------
    # Counter offer
    # ---------------------------------------------------------

    concession_ratio = {
        "price-sensitive": 0.25,
        "casual": 0.50,
        "urgent": 0.75,
    }.get(persona, 0.50)

    rounds_remaining = max_rounds - round_no

    if rounds_remaining == 1:
        concession_ratio += 0.10

    concession_ratio = min(
        concession_ratio,
        1.0
    )

    offer = target + (
        merchant_offer - target
    ) * concession_ratio

    offer = min(
        offer,
        budget
    )

    offer = round(
        offer,
        2
    )

    return {
        "action": "counter",
        "offer_amount": offer,
        "reasoning": (
            f"The merchant's price of ₹{merchant_offer:,.2f} "
            f"is above my acceptable range, so I am increasing "
            f"my offer to ₹{offer:,.2f} while staying within my "
            f"₹{budget:,.2f} budget."
        ),
    }


def validate_buyer_decision(
    decision: dict,
    budget: float,
):
    """
    Python validation of Gemini's buyer decision.
    """

    action = decision.get("action")
    offer_amount = decision.get("offer_amount")

    if action not in {
        "accept",
        "counter",
        "reject",
    }:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Buyer decision blocked because the action "
                "was invalid."
            ),
        }

    if action == "reject":
        return decision

    if offer_amount is None:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Buyer decision blocked because no offer "
                "amount was provided."
            ),
        }

    if offer_amount <= 0:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Buyer decision blocked because the offer "
                "must be positive."
            ),
        }

    if offer_amount > budget:
        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                "Buyer decision blocked by guardrail: "
                "offer exceeds the buyer budget."
            ),
        }

    return decision


def generate_buyer_offer(
    target,
    budget,
    round_no,
    max_rounds,
    persona,
    previous_merchant_offer=None,
):
    """
    Gemini-powered Buyer Agent with deterministic fallback.
    """

    boundaries = calculate_buyer_boundaries(
        target=target,
        budget=budget,
        persona=persona,
        round_no=round_no,
        max_rounds=max_rounds,
    )

    prompt = f"""
You are an autonomous BUYER agent negotiating the price
of a product.

Your objective is to obtain the lowest reasonable price
while staying within your budget.

Buyer information:

- Target price: ₹{target:.2f}
- Maximum budget: ₹{budget:.2f}
- Persona: {persona}
- Current round: {round_no}
- Maximum rounds: {max_rounds}
- Previous merchant offer: {
    f"₹{previous_merchant_offer:.2f}"
    if previous_merchant_offer is not None
    else "None"
}

Python-calculated boundaries:

- Maximum acceptable price: ₹{boundaries["acceptance_price"]:.2f}
- Suggested opening offer: ₹{boundaries["opening_offer"]:.2f}

Rules:

1. Never exceed the buyer budget.
2. If the merchant offer is within the acceptable price,
   accept it.
3. If the merchant offer is above the acceptable price and
   rounds remain, counter.
4. If no agreement is possible, reject.
5. Price-sensitive buyers negotiate aggressively.
6. Urgent buyers are more willing to concede.
7. Casual buyers negotiate moderately.

Python has calculated the financial boundaries.
Do not violate them.

Return ONLY valid JSON:

{{
    "action": "accept | counter | reject",
    "offer_amount": number or null,
    "reasoning": "brief explanation"
}}
"""

    try:

        decision = generate_json_decision(prompt)

        decision = validate_buyer_decision(
            decision=decision,
            budget=budget,
        )

        print("[BUYER] Gemini decision used.")

        return decision

    except Exception as exc:

        print(
            f"[BUYER] Gemini unavailable. "
            f"Using deterministic fallback. Reason: {exc}"
        )

        fallback = calculate_buyer_strategy(
            target=target,
            budget=budget,
            persona=persona,
            previous_merchant_offer=previous_merchant_offer,
            round_no=round_no,
            max_rounds=max_rounds,
        )

        fallback["reasoning"] = (
            "[Deterministic fallback] "
            + fallback["reasoning"]
        )

        return fallback