from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import CreateView

from vitrina.helpers import send_email_with_logging
from vitrina.messages.forms import SubscriptionForm
from vitrina.messages.models import Subscription
from vitrina.users.models import User
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub
from django.utils.translation import gettext_lazy as _


class UnsubscribeView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, obj_id, user_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        user = get_object_or_404(User, pk=user_id)
        if Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
            Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).delete()
            messages.success(request, _("Sėkmingai atsisakėte prenumeratos."))
        email_data = prepare_email_by_identifier_for_sub('newsletter-unsubscribed',
                                                         'Sveiki, Jūs sėkmingai atšaukėte naujienlaiškį',
                                                         'Naujienlaiškio atšaukimas', [])
        if user is not None:
            if user.email is not None:
                send_email_with_logging(email_data, [user.email])
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


class SubscribeFormView(
    LoginRequiredMixin,
    CreateView
):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'vitrina/messages/form.html'

    ct: ContentType | None = None
    obj: None
    user: User

    def dispatch(self, request, *args, **kwargs):
        try:
            self.ct = get_object_or_404(ContentType, pk=self.kwargs['content_type_id'])
            self.obj = get_object_or_404(self.ct.model_class(), pk=self.kwargs['obj_id'])
            self.user = get_object_or_404(User, pk=self.kwargs['user_id'])
        except ObjectDoesNotExist:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Prenumeratos kūrimas')
        context_data['object_title'] = self.obj.title
        return context_data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ct'] = self.ct
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.content_type = self.ct
        self.object.object_id = self.obj.id
        self.object.user = self.user

        try:
            self.object.save()
            messages.success(self.request, _("Prenumerata sukurta sėkmingai"))
            email_data = prepare_email_by_identifier_for_sub('newsletter-subscribed',
                                                             'Sveiki, Jūs sėkmingai užsiprenumeravote naujienlaiškį',
                                                             'Naujienlaiškio prenumeratos registracija', [])
            if self.user is not None:
                if self.user.email is not None:
                    send_email_with_logging(email_data, [self.user.email])
        except IntegrityError:
            existing_subscription = Subscription.objects.filter(
                content_type=self.ct,
                object_id=self.obj.id,
                user=self.user,
            ).first()

            if existing_subscription:
                existing_subscription.delete()
                self.object.save()
                messages.success(self.request, _("Rasta esama šio objekto prenumerata, ji buvo sėkmingai atnaujinta."))
                email_data = prepare_email_by_identifier_for_sub('newsletter-subscribed-update',
                                                                 'Sveiki, Jūs sėkmingai atnaujinote'
                                                                 ' prenumeratos naujienlaiškį',
                                                                 'Naujienlaiškio prenumeratos atnaujinimas', [])
                if self.user is not None:
                    if self.user.email is not None:
                        send_email_with_logging(email_data, [self.user.email])
        return HttpResponseRedirect(self.obj.get_absolute_url())
