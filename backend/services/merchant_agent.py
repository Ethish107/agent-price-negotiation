from .llm_service import generate_json_decision


def calculate_merchant_boundaries(
    list_price: float,
    floor_price: float,
    pricing_context: dict,
    buyer_persona: str,
):
    historical_average = pricing_context.get(
        "average_historical_sale"
    )

    discount_score = 0.0
    reasons = []

    # ---------------------------------------------------------
    # 1. Historical average sale price
    # ---------------------------------------------------------

    if (
        historical_average is not None
        and historical_average < list_price
    ):
        historical_discount = (
            (list_price - historical_average)
            / list_price
        )

        discount_score += min(
            historical_discount,
            0.10
        )

        reasons.append(
            "historical sales show customers have accepted "
            "prices below list price"
        )

    # ---------------------------------------------------------
    # 2. Inventory pressure
    # ---------------------------------------------------------

    pressure = pricing_context.get(
        "inventory_pressure"
    )

    if pressure == "moderate":

        discount_score += 0.03

        reasons.append(
            "moderate inventory pressure"
        )

    elif pressure == "high":

        discount_score += 0.07

        reasons.append(
            "high inventory pressure"
        )

    elif pressure == "critical":

        discount_score += 0.12

        reasons.append(
            "critical inventory pressure"
        )

    # ---------------------------------------------------------
    # 3. WOS vs weeks remaining
    # ---------------------------------------------------------

    wos = pricing_context.get("wos")
    weeks_remaining = pricing_context.get(
        "weeks_remaining"
    )

    if (
        wos is not None
        and weeks_remaining
    ):

        ratio = wos / weeks_remaining

        if ratio > 2:

            discount_score += 0.06

            reasons.append(
                "weeks of supply is significantly above "
                "the remaining selling period"
            )

        elif ratio > 1.5:

            discount_score += 0.04

            reasons.append(
                "weeks of supply is above "
                "the remaining selling period"
            )

        elif ratio > 1:

            discount_score += 0.02

            reasons.append(
                "weeks of supply is slightly above "
                "the remaining selling period"
            )

    # ---------------------------------------------------------
    # 4. Sales velocity
    # ---------------------------------------------------------

    target_velocity = pricing_context.get(
        "target_velocity"
    )

    average_weekly_sales = pricing_context.get(
        "average_weekly_sales"
    )

    if (
        target_velocity is not None
        and average_weekly_sales is not None
        and average_weekly_sales > 0
    ):

        velocity_ratio = (
            target_velocity
            / average_weekly_sales
        )

        if velocity_ratio > 2:

            discount_score += 0.07

            reasons.append(
                "sales velocity needs improvement"
            )

        elif velocity_ratio > 1.5:

            discount_score += 0.04

            reasons.append(
                "sales velocity is below the required target"
            )

    # ---------------------------------------------------------
    # 5. Buyer persona
    # ---------------------------------------------------------

    if buyer_persona == "price-sensitive":

        discount_score += 0.02

        reasons.append(
            "buyer is price-sensitive"
        )

    elif buyer_persona == "urgent":

        discount_score -= 0.02

        reasons.append(
            "buyer is urgent"
        )

    # ---------------------------------------------------------
    # 6. Bound discount between 0% and 25%
    # ---------------------------------------------------------

    discount_score = max(
        0.0,
        min(discount_score, 0.25)
    )

    # ---------------------------------------------------------
    # 7. Economic target
    # ---------------------------------------------------------

    economic_target = (
        list_price
        * (1 - discount_score)
    )

    # ---------------------------------------------------------
    # 8. Apply hard floor
    # ---------------------------------------------------------

    acceptable_price = max(
        economic_target,
        floor_price
    )

    # ---------------------------------------------------------
    # 9. Determine whether floor is binding
    # ---------------------------------------------------------

    floor_binding = (
        economic_target < floor_price
    )

    return {
        "economic_target_price": round(
            economic_target,
            2
        ),
        "acceptable_price": round(
            acceptable_price,
            2
        ),
        "discount_score": round(
            discount_score,
            4
        ),
        "floor_binding": floor_binding,
        "reasons": reasons,
    }


def calculate_merchant_strategy(
    offer_amount,
    list_price,
    floor_price,
    round_no,
    max_rounds,
    pricing_context,
    buyer_persona,
):
    """
    Deterministic merchant strategy.

    This is the fallback used when Gemini is unavailable.
    """

    strategy = calculate_merchant_boundaries(
        list_price=list_price,
        floor_price=floor_price,
        pricing_context=pricing_context,
        buyer_persona=buyer_persona,
    )

    acceptable_price = strategy[
        "acceptable_price"
    ]

    # ---------------------------------------------------------
    # Buyer has offered enough
    # ---------------------------------------------------------

    if offer_amount >= acceptable_price:

        return {
            "action": "accept",
            "offer_amount": offer_amount,
            "reasoning": (
                f"The buyer's offer of ₹{offer_amount:,.2f} "
                f"meets the merchant's acceptable price of "
                f"₹{acceptable_price:,.2f}."
            ),
            **strategy,
        }

    # ---------------------------------------------------------
    # Maximum rounds reached
    # ---------------------------------------------------------

    if round_no >= max_rounds:

        return {
            "action": "reject",
            "offer_amount": None,
            "reasoning": (
                f"The buyer's offer of ₹{offer_amount:,.2f} "
                f"is below the merchant's acceptable price "
                f"of ₹{acceptable_price:,.2f}, and no rounds remain."
            ),
            **strategy,
        }

    # ---------------------------------------------------------
    # Counter
    # ---------------------------------------------------------

    midpoint = (
        offer_amount
        + acceptable_price
    ) / 2

    # NEVER go below floor
    merchant_offer = max(
        midpoint,
        floor_price
    )

    # NEVER exceed list price
    merchant_offer = min(
        merchant_offer,
        list_price
    )

    merchant_offer = round(
        merchant_offer,
        2
    )

    return {
        "action": "counter",
        "offer_amount": merchant_offer,
        "reasoning": (
            f"The buyer's offer of ₹{offer_amount:,.2f} "
            f"is below the merchant's acceptable price. "
            f"The merchant counters at "
            f"₹{merchant_offer:,.2f} while respecting "
            f"the ₹{floor_price:,.2f} hard floor."
        ),
        **strategy,
    }


def evaluate_offer(
    offer_amount,
    list_price,
    floor_price,
    round_no,
    max_rounds,
    pricing_context,
    buyer_persona,
):
    """
    Gemini-enhanced merchant agent with deterministic fallback.
    """

    strategy = calculate_merchant_boundaries(
        list_price=list_price,
        floor_price=floor_price,
        pricing_context=pricing_context,
        buyer_persona=buyer_persona,
    )

    acceptable_price = strategy[
        "acceptable_price"
    ]

    # ---------------------------------------------------------
    # Python determines the actual financial decision.
    # ---------------------------------------------------------

    if offer_amount >= acceptable_price:

        python_action = "accept"
        python_offer = offer_amount

    elif round_no >= max_rounds:

        python_action = "reject"
        python_offer = None

    else:

        midpoint = (
            offer_amount
            + acceptable_price
        ) / 2

        python_offer = max(
            midpoint,
            floor_price
        )

        python_offer = min(
            python_offer,
            list_price
        )

        python_offer = round(
            python_offer,
            2
        )

        python_action = "counter"

    # ---------------------------------------------------------
    # Gemini reasoning
    # ---------------------------------------------------------

    prompt = f"""
You are an autonomous MERCHANT agent.

Your objective is to negotiate a profitable sale while
considering historical sales and current inventory conditions.

Python has already calculated the financially valid decision.

Python's decision is AUTHORITATIVE.

Merchant information:

- List price: ₹{list_price:.2f}
- Hard floor: ₹{floor_price:.2f}
- Buyer offer: ₹{offer_amount:.2f}
- Buyer persona: {buyer_persona}
- Round: {round_no}
- Maximum rounds: {max_rounds}

Historical information:

- Average historical sale: ₹{
    pricing_context.get("average_historical_sale")
}
- Median historical sale: ₹{
    pricing_context.get("median_historical_sale")
}
- Current inventory: {
    pricing_context.get("current_inventory")
}
- Beginning inventory: {
    pricing_context.get("beginning_inventory")
}
- Weeks remaining: {
    pricing_context.get("weeks_remaining")
}
- WOS: {
    pricing_context.get("wos")
}
- Inventory pressure: {
    pricing_context.get("inventory_pressure")
}
- Average weekly sales: {
    pricing_context.get("average_weekly_sales")
}
- Target velocity: {
    pricing_context.get("target_velocity")
}

Pricing strategy:

- Economic target: ₹{
    strategy["economic_target_price"]
}
- Acceptable price: ₹{
    strategy["acceptable_price"]
}
- Floor binding: {
    strategy["floor_binding"]
}
- Discount score: {
    strategy["discount_score"] * 100
:.2f}%

Reasons:

{", ".join(strategy["reasons"])}

---------------------------------------------------------
AUTHORITATIVE PYTHON DECISION
---------------------------------------------------------

Action: {python_action}

Actual merchant offer:
{
    f"₹{python_offer:.2f}"
    if python_offer is not None
    else "None"
}

---------------------------------------------------------

Explain this exact Python decision.

Do not invent another price.

If Python says counter at ₹85000,
your reasoning must explain the counter at ₹85000.

Never describe a merchant price below
₹{floor_price:.2f}.

Return ONLY valid JSON:

{{
    "action": "{python_action}",
    "offer_amount": {
        python_offer
        if python_offer is not None
        else "null"
    },
    "reasoning": "brief explanation"
}}
"""

    try:

        llm_decision = generate_json_decision(
            prompt
        )

        reasoning = llm_decision.get(
            "reasoning",
            "Merchant decision generated from pricing strategy."
        )

        print("[MERCHANT] Gemini reasoning used.")

    except Exception as exc:

        print(
            f"[MERCHANT] Gemini unavailable. "
            f"Using deterministic fallback. Reason: {exc}"
        )

        fallback = calculate_merchant_strategy(
            offer_amount=offer_amount,
            list_price=list_price,
            floor_price=floor_price,
            round_no=round_no,
            max_rounds=max_rounds,
            pricing_context=pricing_context,
            buyer_persona=buyer_persona,
        )

        reasoning = (
            "[Deterministic fallback] "
            + fallback["reasoning"]
        )

    # ---------------------------------------------------------
    # ALWAYS return Python's financial decision
    # ---------------------------------------------------------

    return {
        "action": python_action,
        "offer_amount": python_offer,
        "reasoning": reasoning,
        "economic_target_price": strategy[
            "economic_target_price"
        ],
        "acceptable_price": strategy[
            "acceptable_price"
        ],
        "floor_binding": strategy[
            "floor_binding"
        ],
        "discount_score": strategy[
            "discount_score"
        ],
        "reasons": strategy[
            "reasons"
        ],
    }