from datetime import datetime, timezone


def calculate_sales_period_weeks(sales):
    """
    Calculate the historical observation period from Sale.sold_at.

    We use the time between the earliest and latest historical sale.
    A minimum observation period of 1 week prevents unrealistically
    high velocity when sales happen close together.
    """

    if not sales:
        return 0

    timestamps = [
        sale.sold_at
        for sale in sales
        if sale.sold_at is not None
    ]

    if not timestamps:
        return 0

    earliest = min(timestamps)
    latest = max(timestamps)

    elapsed_seconds = (
        latest - earliest
    ).total_seconds()

    elapsed_weeks = elapsed_seconds / (7 * 24 * 60 * 60)

    # Prevent extremely high velocity from a very short period.
    return max(elapsed_weeks, 1.0)


def calculate_sales_velocity(
    sales_units: int,
    weeks: float
):
    if weeks <= 0:
        return 0

    return sales_units / weeks


def calculate_wos(
    current_inventory: int,
    average_weekly_sales: float
):
    if average_weekly_sales <= 0:
        return float("inf")

    return current_inventory / average_weekly_sales


def calculate_target_velocity(
    inventory: int,
    weeks_remaining: float
):
    if weeks_remaining <= 0:
        return float("inf")

    return inventory / weeks_remaining


def calculate_inventory_pressure(
    wos: float,
    weeks_remaining: float
):
    if weeks_remaining <= 0:
        return "critical"

    ratio = wos / weeks_remaining

    if ratio < 1:
        return "low"

    if ratio < 1.5:
        return "moderate"

    if ratio < 2:
        return "high"

    return "critical"


def calculate_sales_statistics(sales):

    if not sales:
        return {
            "average_sale_price": None,
            "median_sale_price": None,
            "lowest_sale_price": None,
            "highest_sale_price": None,
            "total_units_sold": 0,
        }

    prices = []
    total_units = 0

    for sale in sales:

        # Expand the price according to quantity so that
        # statistics represent individual units rather than
        # just the number of Sale records.
        quantity = max(sale.quantity or 1, 1)

        for _ in range(quantity):
            prices.append(sale.final_price)

        total_units += quantity

    prices.sort()

    average_price = sum(prices) / len(prices)

    middle = len(prices) // 2

    if len(prices) % 2 == 0:
        median_price = (
            prices[middle - 1] +
            prices[middle]
        ) / 2
    else:
        median_price = prices[middle]

    return {
        "average_sale_price": round(
            average_price,
            2
        ),
        "median_sale_price": round(
            median_price,
            2
        ),
        "lowest_sale_price": min(prices),
        "highest_sale_price": max(prices),
        "total_units_sold": total_units,
    }


def build_pricing_context(
    product,
    sales
):

    statistics = calculate_sales_statistics(
        sales
    )

    total_units_sold = (
        statistics["total_units_sold"]
    )

    # ---------------------------------------------------------
    # ACTUAL HISTORICAL PERIOD
    # ---------------------------------------------------------

    sales_period_weeks = (
        calculate_sales_period_weeks(
            sales
        )
    )

    # ---------------------------------------------------------
    # SALES VELOCITY
    # ---------------------------------------------------------

    average_weekly_sales = (
        calculate_sales_velocity(
            total_units_sold,
            sales_period_weeks
        )
    )

    # ---------------------------------------------------------
    # WEEKS OF SUPPLY
    # ---------------------------------------------------------

    wos = calculate_wos(
        product.current_inventory,
        average_weekly_sales
    )

    # ---------------------------------------------------------
    # TARGET VELOCITY
    # ---------------------------------------------------------

    target_velocity = calculate_target_velocity(
        product.current_inventory,
        product.weeks_remaining
    )

    # ---------------------------------------------------------
    # INVENTORY PRESSURE
    # ---------------------------------------------------------

    pressure = calculate_inventory_pressure(
        wos,
        product.weeks_remaining
    )

    # ---------------------------------------------------------
    # RETURN COMPLETE PRICING CONTEXT
    # ---------------------------------------------------------

    return {
        "list_price": product.list_price,
        "floor_price": product.floor_price,

        "current_inventory":
            product.current_inventory,

        "beginning_inventory":
            product.beginning_inventory,

        "weeks_remaining":
            product.weeks_remaining,

        "historical_period_weeks":
            round(sales_period_weeks, 2),

        "total_units_sold":
            total_units_sold,

        "average_weekly_sales":
            round(
                average_weekly_sales,
                2
            ),

        "wos":
            round(wos, 2)
            if wos != float("inf")
            else None,

        "target_velocity":
            round(target_velocity, 2),

        "inventory_pressure":
            pressure,

        "average_historical_sale":
            statistics["average_sale_price"],

        "median_historical_sale":
            statistics["median_sale_price"],

        "lowest_historical_sale":
            statistics["lowest_sale_price"],

        "highest_historical_sale":
            statistics["highest_sale_price"],
    }