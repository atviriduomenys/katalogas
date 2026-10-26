import markdown
from django.contrib import admin
from django.core.mail import EmailMultiAlternatives
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.helpers import logger
from vitrina.messages.forms import MassMailAdminForm
from vitrina.messages.models import Subscription, EmailTemplate, SentMail, MassMail
from django.template import Template
from vitrina.admin import RevisionCommentVersionAdmin


class SubscriptionAdmin(RevisionCommentVersionAdmin):
    list_display = ("user", "content_object", "created")

    @admin.display()
    def content_object(self, obj):
        if obj.content_object and hasattr(obj.content_object, "get_absolute_url"):
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.content_object.get_absolute_url(),
                Truncator(obj.content_object).chars(42),
            )
        else:
            return str(obj.content_type)


class NotValidKeyException(Exception):
    pass


class EmailTemplateAdmin(RevisionCommentVersionAdmin):
    list_display = ("title", "subject", "created")

    def add_view(self, request, form_url="", extra_context=None):
        self.exclude = ("created", "deleted", "deleted_on", "modified_on")
        return super(EmailTemplateAdmin, self).add_view(request)

    def change_view(self, request, object_id, extra_content=None):
        email_keys_from_db = []
        email_keys_from_form = []
        self.exclude = ("created", "deleted", "deleted_on", "modified_on")
        email_template = EmailTemplate.objects.filter(id=object_id).first()
        if request.method == "POST":
            template_db = email_template.template
            template_db = Template(template_db)
            template_form = Template(request.POST["template"])
            for key in template_db.nodelist:
                if type(key).__name__ == "VariableNode":
                    email_keys_from_db.append(key.filter_expression.token)
            for key in template_form:
                if type(key).__name__ == "VariableNode":
                    email_keys_from_form.append(key.filter_expression.token)
            for key in email_keys_from_form:
                if key not in email_keys_from_db:
                    return "<p> Not valid key template. Check email template. </p>"
                    # raise NotValidKeyException("Not valid key template. Check email template.")
        return super(EmailTemplateAdmin, self).change_view(request, object_id)


class SentMailAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "recipient_list",
        "email_subject",
        "email_content_shortened",
        "email_sent",
    )
    search_fields = ("recipient", "email_subject")
    ordering = ("-created",)

    def recipient_list(self, obj):
        if len(obj.recipient) >= 50:
            return obj.recipient[:50] + "..."
        else:
            return obj.recipient

    recipient_list.short_description = _("Gavėjai")

    def email_content_shortened(self, obj):
        if len(obj.email_content) >= 50:
            return obj.email_content[:50] + "..."
        else:
            return obj.email_content

    email_content_shortened.short_description = _("Turinys")


class MassMailAdmin(RevisionCommentVersionAdmin):
    list_display = (
        "send",
        "recipient_group",
        "email_subject",
        "email_content_shortened",
    )
    ordering = ("-created",)
    change_form_template = "vitrina/messages/admin/mass_mail_form.html"
    list_editable = ("send",)
    list_display_links = ("recipient_group",)
    form = MassMailAdminForm

    def email_content_shortened(self, obj):
        if len(obj.email_content) >= 50:
            return obj.email_content[:50] + "..."
        else:
            return obj.email_content

    email_content_shortened.short_description = _("Turinys")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if "send" in form.changed_data and obj.send:
            recipients = [recipient.strip() for recipient in obj.recipients.split(",") if recipient.strip()]
            html_content = markdown.markdown(obj.email_content)
            email = EmailMultiAlternatives(
                subject=obj.email_subject,
                body=obj.email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[],
                bcc=recipients,
            )
            email.attach_alternative(html_content, "text/html")

            try:
                email_send = email.send() > 0
            except Exception as e:
                logger.warning(
                    "Email was not sent: subject=%s recipients=%s error=%s",
                    obj.email_subject,
                    recipients,
                    e,
                    exc_info=True,
                )
                email_send = False

            SentMail.objects.create(
                deleted=None,
                deleted_on=None,
                version=0,
                recipient=list(recipients),
                email_subject=obj.email_subject,
                email_content=obj.email_content,
                email_sent=email_send,
            )


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(SentMail, SentMailAdmin)
admin.site.register(MassMail, MassMailAdmin)
