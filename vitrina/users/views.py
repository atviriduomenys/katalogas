from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as BaseLoginView, PasswordResetView as BasePasswordResetView, \
    PasswordResetConfirmView as BasePasswordResetConfirmView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView

from vitrina.orgs.models import Representative
from vitrina.users.forms import LoginForm, RegisterForm, PasswordResetForm, PasswordResetConfirmForm

from django.utils.translation import gettext_lazy as _


class LoginView(BaseLoginView):
    template_name = 'vitrina/users/login.html'
    form_class = LoginForm

    def get_success_url(self):
        if self.request.user.organization:
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
        messages.info(self.request, _("Slaptažodžio pakeitimo nuoroda išsiųsta į Jūsų el. paštą"))
        return super().form_valid(form)


class PasswordResetConfirmView(BasePasswordResetConfirmView):
    form_class = PasswordResetConfirmForm
    template_name = 'base_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.info(self.request, _("Slaptažodis sėkmingai atnaujintas"))
        return super().form_valid(form)
