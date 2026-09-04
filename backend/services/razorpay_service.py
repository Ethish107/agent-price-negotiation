import razorpay

from ..config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET,
    )
)


def create_payment_link(
    amount: float,
    negotiation_id: int,
    product_name: str,
):
    """
    Create a Razorpay Test Mode Payment Link.

    Razorpay expects INR amounts in paise.
    Example:
        ₹85,000 -> 8,500,000 paise
    """

    amount_paise = int(round(amount * 100))

    reference_id = f"NEG-{negotiation_id}"

    payment_data = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": reference_id,
        "description": (
            f"Agent negotiation purchase - {product_name}"
        ),
        "reminder_enable": False,
        "notes": {
            "negotiation_id": str(negotiation_id),
            "product_name": product_name,
        },
    }

    payment_link = client.payment_link.create(
        payment_data
    )

    return {
        "id": payment_link["id"],
        "short_url": payment_link["short_url"],
        "status": payment_link["status"],
    }