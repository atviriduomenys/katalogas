from django.urls import path
from vitrina.datasets.views import DatasetCreateView
from vitrina.datasets.views import DatasetDetailView
from vitrina.datasets.views import DatasetDistributionDownloadView
from vitrina.datasets.views import DatasetDistributionPreviewView
from vitrina.datasets.views import DatasetHistoryView
from vitrina.datasets.views import DatasetListView
from vitrina.datasets.views import DatasetMembersView
from vitrina.datasets.views import CreateMemberView
from vitrina.datasets.views import UpdateMemberView
from vitrina.datasets.views import DeleteMemberView
from vitrina.datasets.views import DatasetStructureDownloadView
from vitrina.datasets.views import DatasetStructureImportView
from vitrina.datasets.views import DatasetStructureView
from vitrina.datasets.views import DatasetUpdateView

urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/<int:pk>/add/', DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<int:pk>/update/', DatasetUpdateView.as_view(), name='dataset-change'),
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<int:dataset_id>/preview/<int:distribution_id>/', DatasetDistributionPreviewView.as_view(),
         name='dataset-distribution-preview'),
    path('datasets/<int:dataset_id>/download/<int:distribution_id>/<str:file>/',
         DatasetDistributionDownloadView.as_view(), name='dataset-distribution-download'),
    path('datasets/<int:pk>/structure/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/structure/download/', DatasetStructureDownloadView.as_view(),
         name='dataset-structure-download'),
    path('datasets/<int:pk>/structure/import/', DatasetStructureImportView.as_view(),
         name='dataset-structure-import'),
    path('datasets/<int:pk>/history/', DatasetHistoryView.as_view(), name="dataset-history"),
    path('datasets/<int:pk>/members/', DatasetMembersView.as_view(), name='dataset-members'),
    path(
        'datasets/<int:dataset_id>/members/add/',
        CreateMemberView.as_view(),
        name='dataset-representative-create',
    ),
    path(
        'datasets/<int:dataset_id>/members/<int:pk>/change/',
        UpdateMemberView.as_view(),
        name='dataset-representative-update',
    ),
    path(
        'datasets/<int:dataset_id>/members/<int:pk>/delete/',
        DeleteMemberView.as_view(),
        name='dataset-representative-delete',
    ),
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
