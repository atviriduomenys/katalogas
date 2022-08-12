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
        extra_context_data = {
            'members': organization.representative_set.all(),
            'datasets': organization.dataset_set.all(),
            'detail_active': True,
            'members_active': False,
            'datasets_active': False
        }
        context_data.update(extra_context_data)
        return context_data


class OrganizationMembersView(OrganizationDetailView):
    template_name = 'vitrina/orgs/members.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['detail_active'] = False
        context_data['members_active'] = True
        context_data['datasets_active'] = False
        return context_data


class OrganizationDatasetsView(OrganizationDetailView):
    template_name = 'vitrina/orgs/datasets.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['detail_active'] = False
        context_data['members_active'] = False
        context_data['datasets_active'] = True
        return context_data
