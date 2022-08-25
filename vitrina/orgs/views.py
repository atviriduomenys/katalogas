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

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization = context_data.get('organization')
        context_data['ancestors'] = organization.get_ancestors()
        return context_data


class OrganizationMembersView(OrganizationDetailView):
    template_name = 'vitrina/orgs/members.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization = context_data.get('organization')
        context_data['members'] = organization.representative_set.all()
        return context_data


class OrganizationDatasetsView(OrganizationDetailView):
    template_name = 'vitrina/orgs/datasets.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization = context_data.get('organization')
        context_data['datasets'] = organization.dataset_set.all()
        return context_data

