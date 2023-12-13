from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView
from django.urls import reverse
from vitrina.messages.forms import SubscriptionForm
from vitrina.messages.models import Subscription
from vitrina.users.models import User
from vitrina.helpers import email, get_current_domain
from django.utils.translation import gettext_lazy as _


class UnsubscribeView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, obj_id, user_id):
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(content_type.model_class(), pk=obj_id)
        # FIXME: Should get user from request.user.
        user = get_object_or_404(User, pk=user_id)

        # FIXME: Just use request.user
        if request.user.is_authenticated and request.user.pk != user.pk:
            messages.error(request, _(
                "Jūs neturite teisės panaikinti prenumeratos kitam vartotojui."
            ))
            return redirect(obj)

        qs = (
            Subscription.objects.
            filter(
                content_type=content_type,
                object_id=obj.pk,
                user=user,
            )
        )
        if qs.exists():
            qs.delete()
            messages.success(request, _("Sėkmingai atsisakėte prenumeratos."))

        unsubscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse('unsubscribe', kwargs={'content_type_id': content_type_id,
                                           'obj_id': obj_id,
                                           'user_id': user_id})
        )

        subscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse('subscribe-form', kwargs={'content_type_id': content_type_id,
                                           'obj_id': obj_id,
                                           'user_id': user_id})
        )

        email([user.email], 'newsletter-unsubscribed', 'vitrina/messages/emails/sub/deleted.md', {
            'obj': obj,
            'subscribe_url': subscribe_url,
            'unsubscribe_url': unsubscribe_url
        })

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
        self.ct = get_object_or_404(ContentType, pk=self.kwargs['content_type_id'])
        self.obj = get_object_or_404(self.ct.model_class(), pk=self.kwargs['obj_id'])
        # FIXME: take user from request.user
        self.user = get_object_or_404(User, pk=self.kwargs['user_id'])

        # FIXME: take userFrom request user
        if request.user.is_authenticated and request.user.pk != self.user.pk:
            messages.error(request, _(
                "Jūs neturit teisės sukurti prenumeratos kitam naudotojui."
            ))
            return redirect(self.obj)
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

        sub_type = self.ct.model.upper()
        if sub_type in dict(Subscription.SUB_TYPE_CHOICES):
            self.object.sub_type = sub_type

        unsubscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse('unsubscribe', kwargs={'content_type_id': self.object.content_type_id,
                                           'obj_id': self.object.object_id,
                                           'user_id': self.object.user_id
                                           })
        )

        subscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse('subscribe-form', kwargs={'content_type_id': self.object.content_type_id,
                                           'obj_id': self.object.object_id,
                                           'user_id': self.object.user_id})
        )
        try:
            self.object.save()
            messages.success(self.request, _("Prenumerata sukurta sėkmingai"))

            email([self.object.user.email], 'newsletter-subscribed', 'vitrina/messages/emails/sub/created.md', {
                'obj': self.object,
                'subscribe_url': subscribe_url,
                'unsubscribe_url': unsubscribe_url
            })
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
        return HttpResponseRedirect(self.obj.get_absolute_url())
