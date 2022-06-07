from django.views.generic import ListView
from django.views.generic.detail import DetailView

from vitrina.requests.models import Request


class RequestListView(ListView):
    model = Request
    queryset = Request.public.order_by('-created')
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20


class RequestDetailView(DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'
