import requests
from bs4 import BeautifulSoup

DEFAULT_FETCH_TIMEOUT = 2

def fetch_page_title(url: str, timeout=DEFAULT_FETCH_TIMEOUT) -> str | None:
    # TODO: Once Celery is installed, move this to a Celery task to avoid blocking request threads.
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        return (title or "")[:255] or None
    except Exception:
        return None
    