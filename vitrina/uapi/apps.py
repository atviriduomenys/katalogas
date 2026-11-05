from django.apps import AppConfig


class UapiConfig(AppConfig):
    name = "vitrina.uapi"
    label = "vitrina_uapi"
    verbose_name = "UAPI"

    def ready(self) -> None:
        import vitrina.uapi.signals  # noqa: F401
