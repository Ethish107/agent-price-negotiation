from backend.services.pricing_engine import (
    calculate_sales_velocity,
    calculate_wos,
    calculate_target_velocity,
    calculate_inventory_pressure,
)


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