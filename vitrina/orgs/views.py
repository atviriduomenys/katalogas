from django.views.generic import ListView

from vitrina.orgs.models import Organization, Representative


class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        jurisdiction = self.request.GET.get('jurisdiction')
        orgs = Organization.public.all()

        if query:
            orgs = orgs.filter(title__icontains=query)
        if jurisdiction:
            orgs = orgs.filter(jurisdiction=jurisdiction)
        return orgs.order_by("-created")

    def get_context_data(self, **kwargs):
        context = super(OrganizationListView, self).get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        query = self.request.GET.get("q", "")
        context['jurisdictions'] = [{
            'title': jurisdiction,
            'query': "?%s%sjurisdiction=%s" % ("q=%s" % query if query else "", "&" if query else "", jurisdiction),
            'count': filtered_queryset.filter(jurisdiction=jurisdiction).count(),
        } for jurisdiction in Organization.public.values_list('jurisdiction', flat="True")
            .distinct().order_by('jurisdiction').exclude(jurisdiction__isnull=True)]
        context['selected_jurisdiction'] = self.request.GET.get('jurisdiction')
        context['jurisdiction_query'] = self.request.GET.get("jurisdiction", "")
        return context


class OrganizationMembersView(ListView):
    model = Representative
    template_name = 'vitrina/orgs/members_list.html'
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        org_slug = self.kwargs['org_slug']
        org = Organization.objects.filter(slug=org_slug)[:1]
        #TODO: change organization_id to organization when models are relevant
        Representative.objects.filter(organization_id=org[0].id).order_by("first_name", 'last_name')
        return super(OrganizationMembersView, self).get(request, *args, **kwargs)
