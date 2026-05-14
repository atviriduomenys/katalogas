from django.apps import AppConfig


class StructureConfig(AppConfig):
    name = "vitrina.structure"
    label = "vitrina_structure"

    def ready(self):
        import vitrina.structure.signals  # noqa: F401
