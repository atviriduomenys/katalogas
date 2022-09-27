from django.contrib.auth.decorators import login_required
from django.urls import path
from vitrina.datasets.views import DatasetListView, DatasetCreateView, DatasetUpdateView, DatasetStructureView, DatasetStructureDownloadView, DatasetCreateView, DatasetUpdateView, DatasetDetailView, DatasetDistributionDownloadView, DatasetDistributionPreviewView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/<int:pk>/add', DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<int:pk>/update', DatasetUpdateView.as_view(), name='dataset-change'),
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<int:dataset_id>/preview/<int:distribution_id>/', DatasetDistributionPreviewView.as_view(),
         name='dataset-distribution-preview'),
    path('datasets/<int:dataset_id>/download/<int:distribution_id>/<str:filename>/',
         DatasetDistributionDownloadView.as_view(), name='dataset-distribution-download'),
    path('datasets/<int:pk>/structure/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/structure/download/', DatasetStructureDownloadView.as_view(),
         name='dataset-structure-download'),
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
