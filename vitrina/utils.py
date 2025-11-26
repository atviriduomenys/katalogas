import logging
import requests
from vitrina.settings import TRANSLATION_CLIENT_ID, TRANSLATION_URL, TRANSLATION_REQUEST_TIMEOUT


logger = logging.getLogger()


def translate_text(text: str, field_name: str = "") -> str | None:
    if not text:
        return None

    try:
        response = requests.post(
            TRANSLATION_URL,
            json={
                "appId": "",
                "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                "text": text,
                "options": "",
            },
            headers={
                "client-id": TRANSLATION_CLIENT_ID,
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=TRANSLATION_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.warning(f"Translation timeout for {field_name}")
        return text
    except requests.exceptions.RequestException as e:
        logger.warning(f"Translation failed for {field_name}: {e}")
        return text
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid translation response for {field_name}: {e}")
        return text
    except Exception as e:
        logger.exception(f"Unexpected error during translation for {field_name}: {e}")
        return text
