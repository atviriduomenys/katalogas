from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from vitrina.messages.models import Subscription
from vitrina.users.models import User
from django.core.mail import send_mail
from vitrina import settings
from django.utils.translation import gettext_lazy as _
from vitrina.messages.models import EmailTemplate
import datetime


class SubscribeView(LoginRequiredMixin, View):

    def post(self, request, content_type_id, obj_id, user_id):
        def prepare_email_by_identifier(email_identifier, base_template_content,
                                        email_title_subject, email_template_keys):
            email_template = EmailTemplate.objects.filter(identifier=email_identifier)
            if not email_template:
                email_subject = email_title = email_title_subject
                email_content = base_template_content.format(*email_template_keys)
                created_template = EmailTemplate.objects.create(
                    created=datetime.datetime.now(),
                    version=0,
                    identifier=email_identifier,
                    template=email_content,
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

        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        Subscription.objects.create(
            content_type=content_type,
            object_id=obj.pk,
            user=user
        )
        email_data = prepare_email_by_identifier('newsletter-subscribed',
                                                      'Sveiki, Jūs sėkmingai užsiprenumeravote naujienlaiškį',
                                                      'Naujienlaiškio prenumeratos registracija', [])
        if user is not None:
            if user.email is not None:
                send_mail(
                    subject=_(email_data['email_subject']),
                    message=_(email_data['email_content']),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                )
        return redirect(obj.get_absolute_url())


class UnsubscribeView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, obj_id, user_id):
        def prepare_email_by_identifier(email_identifier, base_template_content,
                                         email_title_subject, email_template_keys):

            email_template = EmailTemplate.objects.filter(identifier=email_identifier)
            if not email_template:
                email_subject = email_title = email_title_subject
                email_content = base_template_content.format(*email_template_keys)
                created_template = EmailTemplate.objects.create(
                    created=datetime.datetime.now(),
                    version=0,
                    identifier=email_identifier,
                    template=email_content,
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

        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        if Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
            Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).delete()
            email_data = prepare_email_by_identifier('newsletter-unsubscribed',
                                                          'Sveiki, Jūs sėkmingai atšaukėte naujienlaiškį',
                                                          'Naujienlaiškio atšaukimas', [])
            if user is not None:
                if user.email is not None:
                    send_mail(
                        subject=_(email_data['email_subject']),
                        message=_(email_data['email_content']),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                    )
        return redirect(obj.get_absolute_url())
