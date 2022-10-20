from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as BaseLoginView, PasswordResetView as BasePasswordResetView, \
    PasswordResetConfirmView as BasePasswordResetConfirmView
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, DetailView, UpdateView
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.orgs.services import has_perm, Action
from vitrina.tasks.services import get_active_tasks
from vitrina.users.forms import LoginForm, RegisterForm, PasswordResetForm, PasswordResetConfirmForm
from vitrina.users.forms import UserProfileEditForm
from vitrina.users.models import User


class LoginView(BaseLoginView):
    template_name = 'vitrina/users/login.html'
    form_class = LoginForm

    def get_success_url(self):
        tasks = get_active_tasks(self.request.user)
        redirect_url = self.request.GET.get('next')
        if tasks.exists() and redirect_url == reverse('home'):
            return reverse('user-task-list', args=[self.request.user.pk])
        return super().get_success_url()


class RegisterView(CreateView):
    template_name = 'vitrina/users/register.html'
    form_class = RegisterForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        return render(request=request, template_name=self.template_name, context={"form": form})


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
        extra_context_data = {
            'can_edit_profile': has_perm(self.request.user, Action.UPDATE, user),
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
