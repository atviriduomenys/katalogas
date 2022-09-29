from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    search_fields = ['first_name', 'last_name', 'email']


admin.site.register(User, UserAdmin)
