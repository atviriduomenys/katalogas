from allauth.account.views import email_verification_sent
from django.contrib.auth.views import LogoutView
from django.urls import path, re_path

from vitrina.users.views import (
    LoginView, RegisterView,
    ProfileView, ProfileEditView,
    PasswordSetView, PasswordResetView, PasswordResetConfirmView, CustomPasswordChangeView,
    UserStatsView, ConfirmEmailView, AdminLoginView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('admin/login/', AdminLoginView.as_view(), name='admin:login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password-set/', PasswordSetView.as_view(), name='password-set'),
    path('reset/', PasswordResetView.as_view(), name='reset'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('user/profile/<int:pk>/', ProfileView.as_view(), name='user-profile'),
    path('user/profile/<int:pk>/edit', ProfileEditView.as_view(), name='user-profile-change'),
    path('user/profile/<int:pk>/password/change', CustomPasswordChangeView.as_view(), name='users-password-change'),
    path('user/stats-graph', UserStatsView.as_view(), name='users-stats-graph'),
    re_path(r'register/account-confirm-email/(?P<key>[-:\w]+)/$', ConfirmEmailView.as_view(),
            name='account_confirm_email'),
    path('register/email-verification-sent/', email_verification_sent, name='account_email_verification_sent'),
]
