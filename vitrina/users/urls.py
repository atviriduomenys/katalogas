from django.contrib.auth.views import LogoutView
from django.urls import path

from vitrina.users.views import (
    LoginView, RegisterView,
    ProfileView, ProfileEditView,
    PasswordSetView, PasswordResetView, PasswordResetConfirmView, CustomPasswordChangeView,
    UserStatsView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password-set/', PasswordSetView.as_view(), name='password-set'),
    path('reset/', PasswordResetView.as_view(), name='reset'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('user/profile/<int:pk>/', ProfileView.as_view(), name='user-profile'),
    path('user/profile/<int:pk>/edit', ProfileEditView.as_view(), name='user-profile-change'),
    path('user/profile/<int:pk>/password/change', CustomPasswordChangeView.as_view(), name='users-password-change'),
    path('user/stats-graph', UserStatsView.as_view(), name='users-stats-graph'),
]
