from django.urls import path

from vitrina.datasets.views import DatasetListView, DatasetStructureView, DatasetStructureDownloadView, \
    DatasetDistributionDownloadView, DatasetDistributionPreviewView
from vitrina.datasets.views import DatasetDetailView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<int:dataset_id>/preview/<int:distribution_id>/', DatasetDistributionPreviewView.as_view(),
         name='dataset-distribution-preview'),
    path('datasets/<int:dataset_id>/download/<int:distribution_id>/<str:filename>/',
         DatasetDistributionDownloadView.as_view(), name='dataset-distribution-download'),
    path('datasets/<str:organization_kind>/<slug:organization_slug>/<slug:dataset_slug>/structure/',
         DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<str:organization_kind>/<slug:organization_slug>/<slug:dataset_slug>/structure/download',
         DatasetStructureDownloadView.as_view(), name='dataset-structure-download'),
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
