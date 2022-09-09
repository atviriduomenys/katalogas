from django.urls import path

from vitrina.datasets.views import DatasetListView, DatasetMembersView
from vitrina.datasets.views import DatasetDetailView
from vitrina.datasets.views import DatasetListView, DatasetStructureView, DatasetStructureDownloadView,\
    DatasetDetailView, DatasetSearchResultsView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<str:org_kind>/<slug:org_slug>/<slug:dataset_slug>/members/',
         DatasetMembersView.as_view(), name='dataset-members'),
    path('datasets/<int:pk>/structure/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/structure/download/', DatasetStructureDownloadView.as_view(),
         name='dataset-structure-download'),
    path('datasets/search/', DatasetSearchResultsView.as_view(), name='dataset-search-results')
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
