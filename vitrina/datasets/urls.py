from django.contrib.auth.decorators import login_required
from django.urls import path
from vitrina.datasets.views import DatasetListView, DatasetCreateView, DatasetUpdateView, DatasetStructureView, DatasetStructureDownloadView
from vitrina.datasets.views import DatasetDetailView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<str:org_kind>/<slug:slug>/add/',
         DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<str:org_kind>/<slug:org_slug>/<slug:slug>/change/',
         DatasetUpdateView.as_view(), name='dataset-change'),
    path('datasets/<int:pk>/structure/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/structure/download/', DatasetStructureDownloadView.as_view(),
         name='dataset-structure-download'),
    path('datasets/<int:Organization_kind>/<int:Organization_slug>/add', DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<int:Organization_kind>/<int:Organization_slug>/<int:Dataset_slug>/update', DatasetUpdateView.as_view(), name='dataset-change')
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
