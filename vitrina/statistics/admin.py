from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from vitrina.statistics.models import StatRoute


class StatRouteAdmin(TranslatableAdmin):
    list_display = ('title', 'formatted_url', 'featured',)
    ordering = ('order',)
    fields = ('title', 'description', 'url', 'order', 'featured', 'image',)

    @admin.display(description=_("Nuoroda"))
    def formatted_url(self, obj):
        if len(obj.url) > 50:
            url = f"{obj.url[:50]}..."
        else:
            url = obj.url
        return mark_safe(f'<a href="{obj.url}">{url}</a>')


admin.site.register(StatRoute, StatRouteAdmin)
