from django.contrib.auth.decorators import login_required
from django.urls import path

from vitrina.datasets.views import DatasetListView, DatasetCreateView, DatasetUpdateView
from vitrina.datasets.views import DatasetDetailView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('dataset/<slug:slug>/', DatasetDetailView.as_view(), name='dataset-detail'),
    #TODO: change url according to task
    path('datasets/<slug:org_slug>/add', DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<slug:org_slug>/<slug:dataset_slug>/update', DatasetUpdateView.as_view(), name='dataset-change')
    # @GetMapping("/harvest/object/{id}")
    # @GetMapping("/harvested/{id}")
    # @GetMapping("/dataset/{slug}/follow")
    # @GetMapping("/dataset/{slug}/unfollow")
    # @PostMapping("/dataset/{id}/comment")
    # @PostMapping("/dataset/{id}/reply")
    # @PostMapping("/dataset/{id}/rate")
    # @GetMapping("/dataset/{id}/download/{rid}/{filename}")
    # @GetMapping("/dataset/{id}/structure/{filename}")
    # @GetMapping("/dataset/{id}/structure/{strid}/{filename}")
    # @GetMapping("/dataset/{id}/previewStructure")
    # @GetMapping("/dataset/{id}/preview/{rid}")
    # @RequestMapping("/search")
    # @PostMapping("/quick")
    # @PostMapping("/dataset")
    # @GetMapping("/harvested")
]
