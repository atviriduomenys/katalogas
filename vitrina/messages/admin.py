from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from vitrina.messages.models import Subscription, EmailTemplate, SentMail
from django.template import Template


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_object', 'created')

    @admin.display()
    def content_object(self, obj):
        if obj.content_object and hasattr(obj.content_object, 'get_absolute_url'):
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.content_object.get_absolute_url(),
                Truncator(obj.content_object).chars(42),
            )
        else:
            return str(obj.content_type)


class NotValidKeyException(Exception):
    pass


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created')

    def add_view(self, request, form_url='', extra_context=None):
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        return super(EmailTemplateAdmin, self).add_view(request)

    def change_view(self, request, object_id, extra_content=None):
        email_keys_from_db = []
        email_keys_from_form = []
        self.exclude = ('created', 'deleted', 'deleted_on', 'modified_on')
        email_template = EmailTemplate.objects.filter(id=object_id).first()
        if request.method == "POST":
            template_db = email_template.template
            template_db = Template(template_db)
            template_form = Template(request.POST['template'])
            for key in template_db.nodelist:
                if type(key).__name__ == 'VariableNode':
                    email_keys_from_db.append(key.filter_expression.token)
            for key in template_form:
                if type(key).__name__ == 'VariableNode':
                    email_keys_from_form.append(key.filter_expression.token)
            for key in email_keys_from_form:
                if key not in email_keys_from_db:
                    return "<p> Not valid key template. Check email template. </p>"
                    # raise NotValidKeyException("Not valid key template. Check email template.")
        return super(EmailTemplateAdmin, self).change_view(request, object_id)


class SentMailAdmin(admin.ModelAdmin):
    list_display = ('recipient_list', 'email_subject', 'email_content_shortened', 'email_sent',)

    def recipient_list(self, obj):
        if len(obj.recipient) >= 50:
            return obj.recipient[:50] + "..."
        else:
            return obj.recipient

    recipient_list.short_description = _('Gavėjai')

    def email_content_shortened(self, obj):
        if len(obj.email_content) >= 50:
            return obj.email_content[:50] + "..."
        else:
            return obj.email_content

    email_content_shortened.short_description = _('Turinys')


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(SentMail, SentMailAdmin)
