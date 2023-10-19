from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from vitrina.messages.models import Subscription, EmailTemplate


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_object', 'created')

    @admin.display()
    def content_object(self, obj):
        if obj.content_object is not None:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.content_object.get_absolute_url(),
                Truncator(obj.content_object).chars(42),
            )
        else:
            return obj.content_type


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created')

    def add_view(self, request, form_url='', extra_context=None):
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        return super(EmailTemplateAdmin, self).add_view(request)

    def change_view(self, request, object_id, extra_content=None):
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        return super(EmailTemplateAdmin, self).change_view(request, object_id)


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)