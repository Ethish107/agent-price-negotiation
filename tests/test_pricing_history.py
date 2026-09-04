from datetime import datetime

from backend.services.pricing_engine import (
    calculate_sales_period_weeks,
    calculate_sales_velocity,
    calculate_wos,
    calculate_target_velocity,
    calculate_inventory_pressure,
)


class FakeSale:
    def __init__(self, quantity, sold_at):
        self.quantity = quantity
        self.sold_at = sold_at


def test_sales_period_from_timestamps():

    sales = [
        FakeSale(
            1,
            datetime(2026, 7, 1)
        ),
        FakeSale(
            1,
            datetime(2026, 7, 15)
        ),
        FakeSale(
            1,
            datetime(2026, 8, 1)
        ),
    ]

    weeks = calculate_sales_period_weeks(
        sales
    )

    assert round(weeks, 2) == 4.43


def test_sales_velocity():

    velocity = calculate_sales_velocity(
        sales_units=20,
        weeks=4
    )

    assert velocity == 5


def test_wos():

    wos = calculate_wos(
        current_inventory=60,
        average_weekly_sales=5
    )

    assert wos == 12


def test_target_velocity():

    target = calculate_target_velocity(
        inventory=60,
        weeks_remaining=6
    )

    assert target == 10


def test_inventory_pressure():

    pressure = calculate_inventory_pressure(
        wos=12,
        weeks_remaining=6
    )

    assert pressure == "critical"