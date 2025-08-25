import logging

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

DEFAULT_FETCH_TIMEOUT = 2


def fetch_page_title(url: str, timeout: int = DEFAULT_FETCH_TIMEOUT) -> str | None:
    # TODO: Once Celery is installed, move this to a Celery task to avoid blocking request threads.
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        return title[:255] if title else None
    except Exception:  # Broad exception used to handle all possible cases.
        logger.exception(f"Calling/Parsing title failed from {url}")
        return None
