import os

from dotenv import load_dotenv


load_dotenv()


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID"
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET"
)

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET"
)


if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set"
    )


if not RAZORPAY_KEY_ID:
    raise RuntimeError(
        "RAZORPAY_KEY_ID is not set"
    )


if not RAZORPAY_KEY_SECRET:
    raise RuntimeError(
        "RAZORPAY_KEY_SECRET is not set"
    )


if not RAZORPAY_WEBHOOK_SECRET:
    raise RuntimeError(
        "RAZORPAY_WEBHOOK_SECRET is not set"
    )