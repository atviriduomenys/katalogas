from django.views.generic import ListView

from vitrina.orgs.models import Organization


class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        jurisdiction = self.request.GET.get('jurisdiction')
        orgs = Organization.public.order_by('title')

        if query:
            orgs = orgs.filter(title__icontains=query)
        elif jurisdiction:
            orgs = orgs.filter(jurisdiction=jurisdiction)
        return orgs

    def get_context_data(self, **kwargs):
        context = super(OrganizationListView, self).get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        context['jurisdictions'] = [{
            'title': jurisdiction,
            'query': "?jurisdiction=%s" % jurisdiction,
            'count': filtered_queryset.filter(jurisdiction=jurisdiction).count(),
        } for jurisdiction in Organization.public.values_list('jurisdiction', flat="True")
            .distinct().order_by('jurisdiction').exclude(jurisdiction__isnull=True)]
        context['selected_jurisdiction'] = self.request.GET.get('jurisdiction')
        return context
