from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from vitrina.datasets.models import Dataset
from vitrina.likes.models import UserLike
from vitrina.requests.models import Request


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
        request = context_data.get('request')

        structure_data = request.structure_data.split(";") if request.structure_data else []
        structure = []
        for struct in structure_data:
            data = struct.split(",")
            if data:
                structure.append({
                    "data_title": data[0],
                    "dictionary_title": data[1],
                    "data_type": data[2],
                    "data_notes": data[3],
                })

        dataset = None
        if request.dataset_id:
            try:
                dataset = Dataset.public.get(pk=request.dataset_id)
            except ObjectDoesNotExist:
                pass

        liked = False
        if self.request.user and self.request.user.pk:
            user_like = UserLike.objects.filter(request_id=request.pk, user_id=self.request.user.pk)
            if user_like.exists():
                liked = True

        extra_context_data = {
            "formats": request.format.replace(" ", "").split(",") if request.format else [],
            "changes": request.changes.replace(" ", "").split(",") if request.changes else [],
            "purposes": request.purpose.replace(" ", "").split(",") if request.purpose else [],
            "structure": structure,
            "dataset": dataset,
            "status": request.get_status_label(),
            "like_count": UserLike.objects.filter(request_id=request.pk).count(),
            "liked": liked,
            "user_count": 0,
            "history": None,
        }
        context_data.update(extra_context_data)
        return context_data
