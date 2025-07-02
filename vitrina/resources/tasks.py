import logging
from dataclasses import dataclass
from typing import Optional

import requests
from django.db import models

from .models import DatasetDistribution

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    size: Optional[int] = None
    last_modified: Optional[str] = None


def check_and_update_remote_file_sizes() -> dict:
    results = {"total": 0, "updated": 0, "unchanged": 0, "errors": 0}

    distributions = DatasetDistribution.objects.filter(
        models.Q(download_url__isnull=False) & ~models.Q(download_url="")
        | models.Q(access_url__isnull=False) & ~models.Q(access_url="")
        | models.Q(file__isnull=False)
    )

    results["total"] = distributions.count()
    if not distributions:
        return results

    for dist in distributions:
        try:
            if url := dist.get_download_url():
                update_remote_file_size(dist, url, results)
        except Exception as e:
            logger.error(
                f"Error checking file size for distribution {dist.pk}: {str(e)}"
            )
            results["errors"] += 1

    return results


def update_remote_file_size(
    dist: DatasetDistribution,
    url: str,
    results: dict,
)-> None:
    file_info = get_remote_file_info(url)

    if file_info.size is None:
        results["errors"] += 1
        return

    if dist.size == file_info.size:
        results["unchanged"] += 1
        return

    logger.info(
        f"Updating remote file size for distribution {dist.pk}: "
        f"old={dist.size}, new={file_info.size}"
    )
    dist.size = file_info.size

    update_fields = ["size"]
    if file_info.last_modified and hasattr(dist, 'last_modified'):
        dist.last_modified = file_info.last_modified
        update_fields.append("last_modified")

    dist.save(update_fields=update_fields)
    results["updated"] += 1


def get_remote_file_info(
    url: str,
    max_size: int = 10 * 1024 * 1024,
    timeout: int = 30,
) -> FileInfo:
    try:
        head_response = requests.head(url, allow_redirects=True, timeout=timeout)
        head_response.raise_for_status()

        last_modified = head_response.headers.get("Last-Modified")

        if "Content-Length" in head_response.headers:
            try:
                size = int(head_response.headers["Content-Length"])
                return FileInfo(size=size, last_modified=last_modified)
            except (ValueError, TypeError):
                logger.warning(f"Invalid Content-Length header for URL {url}")

        logger.debug(f"Content-Length not available for {url}, downloading to determine size")

        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()

            size = 0
            for chunk in response.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > max_size:
                    logger.warning(
                        f"File size exceeds maximum limit ({max_size} bytes) for URL {url}"
                    )
                    return FileInfo(size=size, last_modified=last_modified)

            return FileInfo(size=size, last_modified=last_modified)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing URL {url}: {str(e)}")
        return FileInfo()
    except Exception as e:
        logger.error(f"Unexpected error accessing URL {url}: {str(e)}")
