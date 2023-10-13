from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from vitrina.messages.models import Subscription
from vitrina.users.models import User
from django.core.mail import send_mail
from vitrina import settings
from django.utils.translation import gettext_lazy as _
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub


class SubscribeView(LoginRequiredMixin, View):

    def post(self, request, content_type_id, obj_id, user_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        Subscription.objects.create(
            content_type=content_type,
            object_id=obj.pk,
            user=user
        )
        email_data = prepare_email_by_identifier_for_sub('newsletter-subscribed',
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
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        if Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
            Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).delete()
            email_data = prepare_email_by_identifier_for_sub('newsletter-unsubscribed',
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
