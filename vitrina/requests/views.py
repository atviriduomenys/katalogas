from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.detail import DetailView

from vitrina.requests.forms import RequestForm
from vitrina.requests.models import Request

from django.utils.translation import gettext_lazy as _


class RequestListView(ListView):
    model = Request
    queryset = Request.public.order_by('-created')
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20


class RequestDetailView(DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'


class RequestCreateView(CreateView):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio registravimas')
        return context_data


class RequestUpdateView(UpdateView):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio redagavimas')
        return context_data
