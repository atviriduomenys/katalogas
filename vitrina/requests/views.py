from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from reversion import set_comment

from vitrina.requests.forms import RequestForm
from django.core.exceptions import ObjectDoesNotExist
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request, RequestStructure
from vitrina.requests.services import can_update_request

from django.utils.translation import gettext_lazy as _

from vitrina.views import HistoryView, HistoryMixin


class RequestListView(ListView):
    model = Request
    queryset = Request.public.order_by('-created')
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20


class RequestDetailView(HistoryMixin, DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'
    context_object_name = 'request_object'
    detail_url_name = 'request-detail'
    history_url_name = 'request-history'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        request: Request = self.object

        dataset = None
        if request.dataset_id:
            try:
                dataset = Dataset.public.get(pk=request.dataset_id)
            except ObjectDoesNotExist:
                pass

        extra_context_data = {
            "formats": request.format.replace(" ", "").split(",") if request.format else [],
            "changes": request.changes.replace(" ", "").split(",") if request.changes else [],
            "purposes": request.purpose.replace(" ", "").split(",") if request.purpose else [],
            "structure": RequestStructure.objects.filter(request_id=request.pk),
            "dataset": dataset,
            "status": request.get_status_display(),
            "user_count": 0,
            'can_update_request': can_update_request(
                self.request.user,
                request,
            )
        }
        context_data.update(extra_context_data)
        return context_data


class RequestCreateView(LoginRequiredMixin, RevisionMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.status = Request.CREATED
        self.object.save()
        set_comment(Request.CREATED)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio registravimas')
        return context_data


class RequestUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def form_valid(self, form):
        super().form_valid(form)
        set_comment(Request.EDITED)
        return HttpResponseRedirect(self.get_success_url())

    def has_permission(self):
        request = self.get_object()
        return can_update_request(self.request.user, request)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio redagavimas')
        return context_data


class RequestHistoryView(HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-history"
