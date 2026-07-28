from urllib.parse import urlparse

from django.contrib import admin
from django.utils.html import format_html, escape
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from vitrina.statistics.models import StatRoute
from vitrina.admin import RevisionCommentVersionAdmin


class StatRouteAdmin(TranslatableAdmin, RevisionCommentVersionAdmin):
    list_display = (
        "title",
        "formatted_url",
        "featured",
    )
    ordering = ("order",)
    fields = (
        "title",
        "description",
        "url",
        "order",
        "featured",
        "image",
    )

    @admin.display(description=_("Nuoroda"))
    def formatted_url(self, obj):
        parsed = urlparse(obj.url)
        if parsed.scheme not in ("http", "https"):
            return escape(obj.url)
        url = f"{obj.url[:50]}..." if len(obj.url) > 50 else obj.url
        return format_html('<a href="{}">{}</a>', obj.url, url)


admin.site.register(StatRoute, StatRouteAdmin)
