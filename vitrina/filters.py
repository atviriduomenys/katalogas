from django.contrib import admin


class FormatFilter(admin.SimpleListFilter):
    title = ''
    parameter_name = 'format'
    template = 'component/hidden_filter.html'

    def lookups(self, request, model_admin):
        return (request.GET.get(self.parameter_name), ''),

    def queryset(self, request, queryset):
        return queryset
