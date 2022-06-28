from django.contrib import admin

from vitrina.requests.models import Request


class RequestAdmin(admin.ModelAdmin):
    list_filter = ('organization',)


admin.site.register(Request, RequestAdmin)
