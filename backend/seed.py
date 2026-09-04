from datetime import datetime, timedelta

from backend.database import SessionLocal, engine, Base
from backend.models import Product, Sale


Base.metadata.create_all(bind=engine)

db = SessionLocal()


products = [
    {
        "name": "Mechanical Keyboard",
        "list_price": 8000,
        "floor_price": 6500,
        "beginning_inventory": 50,
        "current_inventory": 35,
        "weeks_remaining": 6,
        "sales": [
            (7800, "casual"),
            (7500, "price-sensitive"),
            (7400, "casual"),
            (7600, "urgent"),
            (7300, "price-sensitive"),
        ],
    },
    {
        "name": "Wireless Headphones",
        "list_price": 6000,
        "floor_price": 4800,
        "beginning_inventory": 70,
        "current_inventory": 50,
        "weeks_remaining": 8,
        "sales": [
            (5800, "casual"),
            (5500, "price-sensitive"),
            (5400, "price-sensitive"),
            (5700, "urgent"),
            (5300, "casual"),
        ],
    },
    {
        "name": "Smartwatch",
        "list_price": 9000,
        "floor_price": 7200,
        "beginning_inventory": 40,
        "current_inventory": 25,
        "weeks_remaining": 5,
        "sales": [
            (8600, "urgent"),
            (8300, "casual"),
            (8100, "price-sensitive"),
            (8400, "casual"),
            (8000, "price-sensitive"),
        ],
    },
    {
        "name": "Gaming Mouse",
        "list_price": 4000,
        "floor_price": 3000,
        "beginning_inventory": 80,
        "current_inventory": 60,
        "weeks_remaining": 10,
        "sales": [
            (3800, "casual"),
            (3600, "price-sensitive"),
            (3500, "price-sensitive"),
            (3700, "urgent"),
            (3400, "casual"),
        ],
    },
]


def seed():
    for product_data in products:

        existing = (
            db.query(Product)
            .filter(Product.name == product_data["name"])
            .first()
        )

        if existing:
            product = existing
        else:
            product = Product(
                name=product_data["name"],
                list_price=product_data["list_price"],
                floor_price=product_data["floor_price"],
                beginning_inventory=product_data["beginning_inventory"],
                current_inventory=product_data["current_inventory"],
                weeks_remaining=product_data["weeks_remaining"],
            )

            db.add(product)
            db.flush()

        existing_sales = (
            db.query(Sale)
            .filter(Sale.product_id == product.id)
            .count()
        )

        if existing_sales == 0:
            for index, (price, persona) in enumerate(
                product_data["sales"]
            ):
                sale = Sale(
                    product_id=product.id,
                    final_price=price,
                    quantity=1,
                    buyer_persona=persona,
                    negotiation_rounds=index + 1,
                    sold_at=datetime.utcnow() - timedelta(
                        weeks=5 - index
                    ),
                )

                db.add(sale)

    db.commit()

    print("Demo products and historical sales seeded successfully.")

    db.close()


if __name__ == "__main__":
    seed()