from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from vitrina.messages.models import Subscription


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_object', 'created')

    @admin.display()
    def content_object(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.content_object.get_absolute_url(),
            Truncator(obj.content_object).chars(42),
        )


admin.site.register(Subscription, SubscriptionAdmin)
