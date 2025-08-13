import requests
from bs4 import BeautifulSoup

def fetch_page_title(url: str, timeout=2.5) -> str | None:
    #TODO: Use Celery for background jobs
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        return (title or "")[:255] or None
    except Exception:
        return None
    