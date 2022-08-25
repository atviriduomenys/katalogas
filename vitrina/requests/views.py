from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from vitrina.datasets.models import Dataset
from vitrina.likes.models import UserLike
from vitrina.requests.models import Request
from vitrina.requests.services import get_structure, get_is_liked


class RequestListView(ListView):
    model = Request
    queryset = Request.public.order_by('-created')
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20


class RequestDetailView(DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'

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
            "structure": get_structure(request),
            "dataset": dataset,
            "status": request.get_status_display(),
            "like_count": UserLike.objects.filter(request_id=request.pk).count(),
            "liked": get_is_liked(self.request.user, request),
            "user_count": 0,
            "history": None,
        }
        context_data.update(extra_context_data)
        return context_data
