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


class NotValidKeyException(Exception):
    pass


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created')

    def add_view(self, request, form_url='', extra_context=None):
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        return super(EmailTemplateAdmin, self).add_view(request)

    def change_view(self, request, object_id, extra_content=None):
        import re
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        email_template = EmailTemplate.objects.filter(id=object_id).first()
        if request.method == "POST":
            list_keys = request.POST['template'][
                        request.POST['template'].find("{") + 1:request.POST['template'].rfind("}")].split()
            template_keys_from_form = [word for word in list_keys if word.startswith("{") or word.endswith("}")]
            template_keys_from_form = [re.sub('[^a-zA-Z0-9 \n\.]', '', key.strip(".")) for key in template_keys_from_form]
            for key in template_keys_from_form:
                if key not in email_template.email_keys:
                    raise NotValidKeyException("Not valid key template. Check email template.")
        return super(EmailTemplateAdmin, self).change_view(request, object_id)


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)