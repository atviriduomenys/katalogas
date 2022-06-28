from django.views.generic import ListView

from vitrina.orgs.models import Organization


class OrganizationListView(ListView):
    model = Organization
    queryset = Organization.public.order_by('-created')
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20
