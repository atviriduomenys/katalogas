import uuid
from django.utils import timezone

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView
from django.utils.translation import gettext_lazy as _

from datetime import timedelta
from vitrina.datasets.models import Dataset
from vitrina.messages.forms import SubscriptionForm
from vitrina.messages.models import Subscription, NewsletterSubscriber
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.users.models import User
from vitrina.helpers import email, get_current_domain


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
        self.ct = get_object_or_404(ContentType, pk=self.kwargs["content_type_id"])
        self.obj = get_object_or_404(self.ct.model_class(), pk=self.kwargs["obj_id"])
        # FIXME: take user from request.user
        self.user = get_object_or_404(User, pk=self.kwargs["user_id"])

        # FIXME: take userFrom request user
        if request.user.is_authenticated and request.user.pk != self.user.pk:
            messages.error(request, _("Jūs neturit teisės sukurti prenumeratos kitam naudotojui."))
            return redirect(self.obj)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, content_type_id, obj_id, user_id):
        qs = Subscription.objects.filter(
            content_type=self.ct,
            object_id=self.obj.pk,
            user=self.user,
        )
        if qs.exists():
            qs.delete()
            messages.success(request, _("Sėkmingai atsisakėte prenumeratos."))

        unsubscribe_url = "%s%s" % (
            get_current_domain(self.request),
            self.obj.get_absolute_url(),
        )

        subscribe_url = "%s%s" % (
            get_current_domain(self.request),
            reverse(
                "subscribe-form",
                kwargs={
                    "content_type_id": content_type_id,
                    "obj_id": obj_id,
                    "user_id": user_id,
                },
            ),
        )

        email(
            [self.user.email],
            "newsletter-unsubscribed",
            "vitrina/messages/emails/sub/deleted.md",
            {
                "obj": self.obj,
                "subscribe_url": subscribe_url,
                "unsubscribe_url": unsubscribe_url,
            },
        )

        return HttpResponseRedirect(reverse("user-profile", args=[self.user.pk]) + "#sub")


class SubscribeFormView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = "vitrina/messages/form.html"

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
        self.ct = get_object_or_404(ContentType, pk=self.kwargs["content_type_id"])
        self.obj = get_object_or_404(self.ct.model_class(), pk=self.kwargs["obj_id"])
        # FIXME: take user from request.user
        self.user = get_object_or_404(User, pk=self.kwargs["user_id"])

        # FIXME: take userFrom request user
        if request.user.is_authenticated and request.user.pk != self.user.pk:
            messages.error(request, _("Jūs neturit teisės sukurti prenumeratos kitam naudotojui."))
            return redirect(self.obj)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["current_title"] = _("Prenumeratos kūrimas")
        context_data["object_title"] = self.obj.title
        return context_data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ct"] = self.ct
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
            self.obj.get_absolute_url(),
        )
        unsubscribe_url = "%s%s#sub" % (
            get_current_domain(self.request),
            reverse("user-profile", args=[self.user.pk]),
        )
        try:
            self.object.save()
            messages.success(self.request, _("Prenumerata sukurta sėkmingai"))

            email(
                [self.object.user.email],
                "newsletter-subscribed",
                "vitrina/messages/emails/sub/created.md",
                {
                    "obj": self.obj,
                    "subscribe_url": subscribe_url,
                    "unsubscribe_url": unsubscribe_url,
                },
            )
        except IntegrityError:
            existing_subscription = Subscription.objects.filter(
                content_type=self.ct,
                object_id=self.obj.id,
                user=self.user,
            ).first()

            if existing_subscription:
                existing_subscription.delete()
                self.object.save()
                messages.success(
                    self.request,
                    _("Rasta esama šio objekto prenumerata, ji buvo sėkmingai atnaujinta."),
                )
        return HttpResponseRedirect(self.obj.get_absolute_url())


class NewsletterSubscribeView(View):
    def post(self, request, *args, **kwargs):
        email_input = request.POST.get("email", "").strip()

        if not email_input:
            message = _("Prašome įvesti el. pašto adresą.")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": str(message)})

            messages.error(request, message)
            return self.redirect_back()

        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email_input, defaults={"is_confirmed": False, "is_active": True}
        )

        if not created and subscriber.is_confirmed and subscriber.is_active:
            message = _("Šis el. pašto adresas jau prenumeruoja naujienlaiškį.")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"status": "info", "message": str(message)})

            messages.info(request, message)
            return self.redirect_back()

        if not created:
            subscriber.is_active = True
            subscriber.is_confirmed = False

        subscriber.confirmation_token = uuid.uuid4()
        subscriber.confirmation_expires_at = timezone.now() + timedelta(hours=24)
        subscriber.save()

        confirmation_url = request.build_absolute_uri(
            reverse(
                "newsletter-confirm", kwargs={"token": subscriber.confirmation_token}
            )
        )

        email(
            [subscriber.email],
            "newsletter-confirmation",
            "vitrina/messages/emails/newsletter/confirmation.md",
            {
                "confirmation_url": confirmation_url,
                "expiry_hours": 24,
            },
        )

        message = _(
            "Patvirtinimo nuoroda išsiųsta į jūsų el. paštą. Nuoroda galioja 24 valandas."
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "success", "message": str(message)})
        messages.success(request, message)

        return self.redirect_back()

    def redirect_back(self):
        referer = self.request.META.get("HTTP_REFERER")
        if referer and url_has_allowed_host_and_scheme:
            return redirect(referer)
        return redirect("/")


class NewsletterConfirmView(View):
    def get(self, request, token):
        try:
            subscriber = get_object_or_404(
                NewsletterSubscriber, confirmation_token=token, is_confirmed=False
            )

            if subscriber.is_confirmation_expired:
                messages.error(
                    request,
                    _(
                        "Patvirtinimo nuoroda nebegalioja. Prašome užsisakyti prenumeratą iš naujo."
                    ),
                )
                return redirect("newsletter-subscribe")

            subscriber.confirm_subscription()

            unsubscribe_url = request.build_absolute_uri(
                reverse(
                    "newsletter-unsubscribe",
                    kwargs={"token": subscriber.unsubscribe_token},
                )
            )

            email(
                [subscriber.email],
                "newsletter-welcome",
                "vitrina/messages/emails/newsletter/welcome.md",
                {
                    "unsubscribe_url": unsubscribe_url,
                },
            )

            messages.success(
                request, _("Naujienlaiškio prenumerata sėkmingai patvirtinta!")
            )
            return render(request, "newsletter/confirmed.html")

        except Exception:
            messages.error(request, _("Įvyko klaida patvirtinant prenumeratą."))
            return redirect("/")


class NewsletterUnsubscribeView(View):
    def get(self, request, token):
        subscriber = get_object_or_404(
            NewsletterSubscriber,
            unsubscribe_token=token,
            is_active=True,
            is_confirmed=True,
        )

        return render(
            request, "newsletter/unsubscribe_confirm.html", {"subscriber": subscriber}
        )

    def post(self, request, token):
        subscriber = get_object_or_404(
            NewsletterSubscriber,
            unsubscribe_token=token,
            is_active=True,
            is_confirmed=True,
        )

        subscriber.is_active = False
        subscriber.save()

        messages.success(request, _("Naujienlaiškio prenumerata sėkmingai atšaukta."))

        return render(request, "newsletter/unsubscribed.html")
