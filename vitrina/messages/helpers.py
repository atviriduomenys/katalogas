import datetime
from django.utils.translation import gettext_lazy as _
from vitrina.messages.models import EmailTemplate


# Same method as prepare_email_by_identifier to avoid circular import
def prepare_email_by_identifier_for_sub(email_identifier, base_template_content,
                                        email_title_subject, email_template_keys):
    email_template = EmailTemplate.objects.filter(identifier=email_identifier)
    if not email_template:
        email_subject = email_title = email_title_subject
        email_content = base_template_content.format(*email_template_keys)
        created_template = EmailTemplate.objects.create(
            created=datetime.datetime.now(),
            version=0,
            identifier=email_identifier,
            template=base_template_content,
            subject=_(email_title_subject),
            title=_(email_title)
        )
        created_template.save()
    else:
        email_template = email_template.first()
        email_content = str(email_template.template)
        email_content = email_content.format(*email_template_keys)
        email_subject = str(email_template.subject)

    return {'email_content': email_content, 'email_subject': email_subject}
