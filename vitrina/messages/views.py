from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.urls import reverse

from vitrina.datasets.models import Dataset
from vitrina.messages.forms import SubscriptionForm
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.users.models import User
from vitrina.helpers import email, get_current_domain
from django.utils.translation import gettext_lazy as _


class UnsubscribeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    ct: ContentType | None = None
    obj: None
    user: User

    def has_permission(self):
        if isinstance(self.obj, Dataset):
            if self.obj.is_public:
                return True
            else:
                return has_perm(self.request.user, Action.VIEW, self.obj)
        elif isinstance(self.obj, Project):
            if self.obj.status == Project.APPROVED or self.obj.user == self.request.user:
                return True
            else:
                return has_perm(
                    self.request.user,
                    Action.UPDATE,
                    self.obj,
                )
        return True

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

    def post(self, request, content_type_id, obj_id, user_id):
        qs = (
            Subscription.objects.
            filter(
                content_type=self.ct,
                object_id=self.obj.pk,
                user=self.user,
            )
        )
        if qs.exists():
            qs.delete()
            messages.success(request, _("Sėkmingai atsisakėte prenumeratos."))

        unsubscribe_url = "%s%s" % (
            get_current_domain(self.request),
            self.obj.get_absolute_url()
        )

        subscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse('subscribe-form', kwargs={'content_type_id': content_type_id,
                                           'obj_id': obj_id,
                                           'user_id': user_id})
        )

        email([self.user.email], 'newsletter-unsubscribed', 'vitrina/messages/emails/sub/deleted.md', {
            'obj': self.obj,
            'subscribe_url': subscribe_url,
            'unsubscribe_url': unsubscribe_url
        })

        return HttpResponseRedirect(reverse('user-profile', args=[self.user.pk]) + "#sub")


class SubscribeFormView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView
):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'vitrina/messages/form.html'

    ct: ContentType | None = None
    obj: None
    user: User

    def has_permission(self):
        if isinstance(self.obj, (Dataset, Organization)):
            if self.obj.is_public:
                return True
            else:
                return has_perm(self.request.user, Action.VIEW, self.obj)
        elif isinstance(self.obj, Project):
            if self.obj.status == Project.APPROVED or self.obj.user == self.request.user:
                return True
            else:
                return has_perm(
                    self.request.user,
                    Action.UPDATE,
                    self.obj,
                )
        return True

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

        subscribe_url = "%s%s" % (
            get_current_domain(self.request),
            self.obj.get_absolute_url()
        )
        unsubscribe_url = "%s%s#sub" % (
            get_current_domain(self.request),
            reverse('user-profile', args=[self.user.pk])
        )
        try:
            self.object.save()
            messages.success(self.request, _("Prenumerata sukurta sėkmingai"))

            email([self.object.user.email], 'newsletter-subscribed', 'vitrina/messages/emails/sub/created.md', {
                'obj': self.obj,
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
