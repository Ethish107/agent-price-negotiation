import json
import time

from google import genai

from ..config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.6-flash"


def generate_json_decision(prompt: str) -> dict:
    """
    Ask Gemini for a JSON decision.

    Returns:
        dict: Parsed Gemini JSON response.

    Raises:
        Exception: If Gemini remains unavailable after retries.
    """

    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                },
            )

            return json.loads(response.text)

        except Exception as exc:
            error_text = str(exc)

            # Retry temporary Gemini availability failures.
            if "503" in error_text or "UNAVAILABLE" in error_text:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt

                    print(
                        f"[GEMINI] Temporarily unavailable. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)
                    continue

            raise


def test_gemini():
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="Respond with exactly: Gemini connection successful."
    )

    return response.text