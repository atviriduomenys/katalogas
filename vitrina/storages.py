from django.conf import settings
from django.core.files.storage import FileSystemStorage

internal_media_storage = FileSystemStorage(location=settings.INTERNAL_MEDIA_ROOT, base_url=settings.INTERNAL_MEDIA_URL)
