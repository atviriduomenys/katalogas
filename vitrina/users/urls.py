from django.contrib.auth.views import LogoutView
from django.urls import path

from vitrina.users.views import LoginView, RegisterView, PasswordResetView, PasswordResetConfirmView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('reset/', PasswordResetView.as_view(), name='reset'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # @GetMapping("/login")
    # @GetMapping("/register")
    # @GetMapping("/reset")
    # @PostMapping("/reset")
    # @GetMapping("/user/changePassword")
    # @GetMapping("/reset/new")
    # @PostMapping("/user/savePassword")
    # @PostMapping("/reset/new")
    # @PostMapping("/profile/password/change")
    # @PostMapping("/login")
    # @PostMapping("/register")
    # @GetMapping("/logout")
    # @GetMapping("/initPasswordReset")
    # @GetMapping("/sso")
    # @GetMapping("/sso/admin")
    # @RequestMapping("/user")
    # @GetMapping("/profile")
]
