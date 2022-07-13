from django.views.generic import ListView
from django.views.generic import DetailView

from vitrina.orgs.models import Organization


class OrganizationListView(ListView):
    model = Organization
    queryset = Organization.public.order_by('title')
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

class OrganizationDetailView(DetailView):
    model = Organization
    template_name = 'vitrina/orgs/detail.html'