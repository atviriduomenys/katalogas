from django.views.generic import ListView

from vitrina.orgs.models import Organization


class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            orgs = Organization.public.filter(title__icontains=query)
        else:
            orgs = Organization.public.all()
        return orgs.order_by("-created")
