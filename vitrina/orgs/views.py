from django.views.generic import ListView
from django.db.models import Q

from vitrina.orgs.models import Organization

class OrganizationSearchResultsView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            orgs = Organization.objects.filter(
                Q(title__icontains=query)
            )
        else:
            orgs = Organization.objects.all()
        return orgs