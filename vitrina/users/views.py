import secrets
from datetime import datetime

from allauth.account.utils import perform_login
from allauth.account.views import ConfirmEmailView as BaseConfirmEmailView
from pandas import period_range
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import (
    LoginView as BaseLoginView,
    PasswordResetView as BasePasswordResetView,
    PasswordResetConfirmView as BasePasswordResetConfirmView, PasswordChangeView
)
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, DetailView, UpdateView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now, make_aware
from allauth.socialaccount.models import SocialAccount
from allauth.account.forms import SignupForm
from allauth.account.models import EmailAddress, EmailConfirmation
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpResponseRedirect

from vitrina import settings
from vitrina.messages.models import Subscription
from vitrina.orgs.services import has_perm, Action
from vitrina.tasks.services import get_active_tasks
from vitrina.users.forms import (
    LoginForm, RegisterForm, PasswordSetForm,
    PasswordResetForm, PasswordResetConfirmForm,
    UserProfileEditForm, CustomPasswordChangeForm
)
from vitrina.users.models import User


class LoginView(BaseLoginView):
    template_name = 'vitrina/users/login.html'
    account_inactive_template = 'vitrina/users/account_inactive.html'
    form_class = LoginForm

    def form_valid(self, form):
        if settings.ACCOUNT_EMAIL_VERIFICATION == 'mandatory':
            user = EmailAddress.objects.filter(email=self.request.POST['email'])
            if user:
                if user[0].verified is True:
                    login(self.request, form.get_user(),
                          backend='django.contrib.auth.backends.ModelBackend')
                    return HttpResponseRedirect(self.get_success_url())
                else:
                    return HttpResponseRedirect(reverse('please_confirm_email'))
            else:
                login(self.request, form.get_user(),
                      backend='django.contrib.auth.backends.ModelBackend')
                return HttpResponseRedirect(self.get_success_url())
        else:
            login(self.request, form.get_user(),
                  backend='django.contrib.auth.backends.ModelBackend')
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        tasks = get_active_tasks(self.request.user)
        redirect_url = self.request.GET.get('next')
        if tasks.exists() and redirect_url == reverse('home'):
            return reverse('user-task-list', args=[self.request.user.pk])
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Prisijungimas')
        return context


class RegisterView(CreateView, SignupForm, PasswordResetTokenGenerator):
    template_name = 'vitrina/users/register.html'
    form_class = RegisterForm
    cleaned_data = None

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            self.cleaned_data = form.cleaned_data
            user = super(RegisterView, self).save(request)
            email_address = EmailAddress.objects.get(user_id=user.pk)
            EmailConfirmation.objects.create(
                created=datetime.now(),
                sent=datetime.now(),
                key=secrets.token_urlsafe(),
                email_address_id=email_address.id
            )
            perform_login(request=request, user=user,
                          email_verification=settings.ACCOUNT_EMAIL_VERIFICATION,
                          signup=False)
            return redirect('home')
        return render(request=request, template_name=self.template_name, context={"form": form})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Registracija')
        return context


class PasswordSetView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    template_name = 'base_form.html'
    model = User
    context_object_name = 'user'
    form_class = PasswordSetForm

    def has_permission(self):
        user = get_object_or_404(User, id=self.request.user.id)
        soc_acc = SocialAccount.objects.filter(user_id=user.id).first()
        if soc_acc:
            return soc_acc.extra_data.get('password_not_set') == True

    def handle_no_permission(self):
        return redirect('home')

    def get_object(self):
        object_id = self.request.user.id
        return User.objects.get(pk=object_id)
    
    def form_valid(self, form):
        user = self.get_object()
        password = form.cleaned_data.get('password')
        user.set_password(password)
        user.save()
        soc_acc = SocialAccount.objects.filter(user_id=user.id).first()
        soc_acc.extra_data['password_not_set'] = False
        soc_acc.save()
        
        update_session_auth_hash(self.request, user)
        soc_acc = SocialAccount.objects.filter(user_id=user.id).first()
        company_code = soc_acc.extra_data.get('company_code')
        return redirect('partner-register')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Slaptažodžio nustatymas')
        context_data['form_info'] = _(
            "Tam, kad pabaigti autentifikaciją per viisp ir sukurti naują vartotoją portale, sugalvokite slaptažodį.")
        return context_data


class PasswordResetView(BasePasswordResetView):
    form_class = PasswordResetForm
    template_name = 'base_form.html'
    email_template_name = 'vitrina/users/password_reset_email.html'
    subject_template_name = 'vitrina/users/password_reset_subject.txt'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.info(self.request, _(
            "Slaptažodžio pakeitimo nuoroda išsiųsta į Jūsų el. paštą"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Slaptažodžio atkūrimas')
        return context


class PasswordResetConfirmView(BasePasswordResetConfirmView):
    form_class = PasswordResetConfirmForm
    template_name = 'base_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.info(self.request, _("Slaptažodis sėkmingai atnaujintas"))
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = User
    template_name = 'vitrina/users/profile.html'
    context_object_name = 'user'

    def has_permission(self):
        users_profile = get_object_or_404(User, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.VIEW, users_profile)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            return redirect('user-profile', pk=self.request.user.id)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        user = context_data.get('user')
        context_data['logged_in_user'] = self.request.user

        subscriptions = Subscription.objects.filter(user=user)\
            .exclude(sub_type=Subscription.COMMENT)\
            .prefetch_related('content_object')
        for sub in subscriptions:
            sub.fields = [(_("Laiškai"), sub.email_subscribed)]
            if sub.sub_type == Subscription.ORGANIZATION:
                sub.fields.extend([
                    (_("Duomenų rinkiniai"), sub.dataset_update_sub),
                    (_("Duomenų rinkinių komentarai"), sub.dataset_comments_sub),
                    (_("Prašymai"), sub.request_update_sub),
                    (_("Prašymų komentarai"), sub.request_comments_sub)])
            if sub.sub_type == Subscription.DATASET:
                sub.fields.extend([
                    (_("Duomenų rinkiniai"), sub.dataset_update_sub),
                    (_("Duomenų rinkinių komentarai"), sub.dataset_comments_sub)])
            if sub.sub_type == Subscription.REQUEST:
                sub.fields.extend([
                    (_("Prašymai"), sub.request_update_sub),
                    (_("Prašymų komentarai"), sub.request_comments_sub),
                    (_("Duomenų rinkiniai"), sub.dataset_update_sub),
                    (_("Duomenų rinkinių komentarai"), sub.dataset_comments_sub)])
            if sub.sub_type == Subscription.PROJECT:
                sub.fields.extend([
                    (_("Projektai"), sub.project_update_sub),
                    (_("Projektų komentarai"), sub.project_comments_sub)])

        extra_context_data = {
            'can_edit_profile': has_perm(self.request.user, Action.UPDATE, user),
            'subscriptions': subscriptions
        }
        context_data.update(extra_context_data)
        return context_data


class ProfileEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    template_name = 'base_form.html'
    context_object_name = 'user'
    form_class = UserProfileEditForm

    def has_permission(self):
        users_profile = get_object_or_404(User, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.UPDATE, users_profile)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            return redirect('user-profile', pk=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Naudotojo profilio redagavimas')
        return context

    def get(self, request, *args, **kwargs):
        return super(ProfileEditView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return redirect('user-profile', pk=self.request.user.id)


class CustomPasswordChangeView(LoginRequiredMixin, PermissionRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'base_form.html'

    def has_permission(self):
        user = get_object_or_404(User, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.UPDATE, user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            return redirect('user-profile', pk=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Naudotojo slaptažodžio keitimas')
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Slaptažodžio keitimas sėkmingas"))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('user-profile', kwargs={'pk': self.kwargs['pk']})


class UserStatsView(TemplateView):
    template_name = 'users_count_stats_chart.html'

    def get_labels(self):
        """Return labels"""
        oldest_user_date = User.objects.order_by('created').first().created
        labels = period_range(start=oldest_user_date, end=now(), freq='M').tolist()    
        return labels

    def get_color(self, year):
        color_map = {
            'Koordinatoriai': '#03256C',
            'Tvarkytojai': '#1768AC',
            "Registruoti naudotojai": '#06BEE1',
            # FIXME: Use constants instead of strings.
        }
        return color_map.get(year)

    def get_user_types(self):
        """Return names of datasets."""
        return [
            "Koordinatoriai",
            "Tvarkytojai",
            "Registruoti naudotojai",
            # FIXME: these strings should be translatable
        ]

    def get_data(self):
        """Return datasets to plot."""
        user_types = self.get_user_types()
        labels = self.get_labels()
        data = {
            'labels': [str(label) for label in labels]
        }
        datasets = []
        for user_type in user_types:
            dataset = {
                'label': user_type,
                'data': []
            }
            dataset['backgroundColor'] = self.get_color(user_type)
            for label in labels:
                label = label + 1  # Increment by one month
                created_date = datetime(label.year, label.month, 1)
                created_date = make_aware(created_date)
                if user_type == "Koordinatoriai":
                    dataset['data'].append(
                        User.objects.select_related('representative').
                        filter(
                            representative__role='coordinator',
                            created__lt=created_date
                        ).
                        distinct('representative__user').
                        count()
                    )
                elif user_type == "Tvarkytojai":
                    dataset['data'].append(
                        User.objects.select_related('representative').
                        filter(
                            representative__role='manager',
                            created__lt=created_date,
                        ).
                        exclude(representative__role='coordinator').
                        distinct('representative__user').
                        count()
                    )
                elif user_type == "Registruoti naudotojai":
                    dataset['data'].append(
                        User.objects.select_related('representative').
                        filter(
                            created__lt=created_date
                        ).
                        exclude(representative__role='manager').
                        exclude(representative__role='coordinator').
                        count()
                    )
                    # TODO: If it is possible, it would be nice, to get
                    #       these stats with a single query.
                else:
                    raise ValueError(user_type)
            datasets.append(dataset)
        data['datasets'] = datasets
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_data()
        context['data'] = data
        return context


class ConfirmEmailView(BaseConfirmEmailView):
    template_name = 'vitrina/users/confirm_email.html'


class PleaseConfirmEmailView(TemplateView):
    template_name = 'vitrina/users/please_confirm_email.html'