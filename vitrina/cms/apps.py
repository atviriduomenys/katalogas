from django.apps import AppConfig


class CmsConfig(AppConfig):
    name = "vitrina.cms"
    label = "vitrina_cms"

    def ready(self):
        from django.db.models.signals import post_save

        post_save.connect(_add_default_text_plugin, sender="djangocms_stories.PostContent")


def _add_default_text_plugin(sender, instance, created, **kwargs):
    if not created or not instance.content:
        return
    from cms.api import add_plugin
    from cms.models import CMSPlugin

    if not CMSPlugin.objects.filter(placeholder=instance.content).exists():
        add_plugin(instance.content, "TextPlugin", instance.language, body="<Vieta Jūsų tekstui.>")
