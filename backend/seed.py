from backend.database import (
    SessionLocal,
    engine,
    Base
)

from backend.models import Product, Sale


Base.metadata.create_all(
    bind=engine
)


db = SessionLocal()


# ==========================================
# PRODUCTS
# ==========================================

products = [
    Product(
        name="MacBook Air M3",
        list_price=100000,
        floor_price=85000,
        beginning_inventory=100,
        current_inventory=60,
        weeks_remaining=6
    ),

    Product(
        name="Sony WH-1000XM5",
        list_price=30000,
        floor_price=24000,
        beginning_inventory=80,
        current_inventory=35,
        weeks_remaining=8
    ),

    Product(
        name="iPhone 16",
        list_price=80000,
        floor_price=68000,
        beginning_inventory=100,
        current_inventory=50,
        weeks_remaining=10
    )
]


db.add_all(products)
db.commit()


# ==========================================
# HISTORICAL SALES
# ==========================================

sales = [

    # --------------------------
    # MacBook Air M3
    # --------------------------

    Sale(
        product_id=1,
        final_price=95000,
        quantity=1,
        buyer_persona="casual",
        negotiation_rounds=1
    ),

    Sale(
        product_id=1,
        final_price=94000,
        quantity=1,
        buyer_persona="urgent",
        negotiation_rounds=2
    ),

    Sale(
        product_id=1,
        final_price=92000,
        quantity=1,
        buyer_persona="price-sensitive",
        negotiation_rounds=3
    ),

    Sale(
        product_id=1,
        final_price=91000,
        quantity=1,
        buyer_persona="price-sensitive",
        negotiation_rounds=3
    ),

    Sale(
        product_id=1,
        final_price=94000,
        quantity=1,
        buyer_persona="casual",
        negotiation_rounds=2
    ),


    # --------------------------
    # Sony WH-1000XM5
    # --------------------------

    Sale(
        product_id=2,
        final_price=28000,
        quantity=1,
        buyer_persona="casual",
        negotiation_rounds=1
    ),

    Sale(
        product_id=2,
        final_price=27000,
        quantity=1,
        buyer_persona="price-sensitive",
        negotiation_rounds=2
    ),

    Sale(
        product_id=2,
        final_price=26000,
        quantity=1,
        buyer_persona="price-sensitive",
        negotiation_rounds=3
    ),


    # --------------------------
    # iPhone 16
    # --------------------------

    Sale(
        product_id=3,
        final_price=76000,
        quantity=1,
        buyer_persona="urgent",
        negotiation_rounds=1
    ),

    Sale(
        product_id=3,
        final_price=74000,
        quantity=1,
        buyer_persona="casual",
        negotiation_rounds=2
    ),

    Sale(
        product_id=3,
        final_price=72000,
        quantity=1,
        buyer_persona="price-sensitive",
        negotiation_rounds=3
    )
]


db.add_all(sales)
db.commit()


print("Products and historical sales seeded successfully.")


db.close()