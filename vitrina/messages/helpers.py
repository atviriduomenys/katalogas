import datetime
from django.utils.translation import gettext_lazy as _
from vitrina.messages.models import EmailTemplate


# Same method as prepare_email_by_identifier to avoid circular import
def prepare_email_by_identifier_for_sub(email_identifier, base_template_content,
                                        email_title_subject, email_template_keys):
    email_template = EmailTemplate.objects.filter(identifier=email_identifier)
    list_keys = base_template_content[base_template_content.find("{") + 1:base_template_content.rfind("}")].replace(
        '{', '').replace('}', '').split()
    email_template_to_save = base_template_content
    for key in list_keys:
        if key in email_template_keys.keys():
            if email_template_keys[key] is not None:
                base_template_content = base_template_content.replace("{" + key + "}", email_template_keys[key])
        else:
            base_template_content = base_template_content.replace("{" + key + "}", '')
    if not email_template:
        email_subject = email_title = email_title_subject
        email_content = base_template_content
        created_template = EmailTemplate.objects.create(
            created=datetime.datetime.now(),
            version=0,
            identifier=email_identifier,
            template=email_template_to_save,
            subject=_(email_title_subject),
            title=_(email_title)
        )
        created_template.save()
    else:
        email_template = email_template.first()
        email_content = str(email_template.template)
        for key in list_keys:
            if key in email_template_keys.keys():
                if email_template_keys[key] is not None:
                    email_content = email_content.replace("{" + key + "}", email_template_keys[key])
            else:
                email_content = email_content.replace("{" + key + "}", '')
        email_subject = str(email_template.subject)

    return {'email_content': email_content, 'email_subject': email_subject}
