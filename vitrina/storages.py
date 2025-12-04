from django.conf import settings
from django.core.files.storage import FileSystemStorage


class InternalFileSystemStorage(FileSystemStorage):
    @property
    def location(self) -> str:
        return settings.INTERNAL_MEDIA_ROOT

    @property
    def base_url(self) -> str:
        return settings.INTERNAL_MEDIA_URL


internal_media_storage = InternalFileSystemStorage()
