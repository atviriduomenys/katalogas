from django.urls import path

from vitrina.datasets.models import Dataset
from vitrina.datasets.views import AddProjectView
from vitrina.datasets.views import CreateMemberView
from vitrina.datasets.views import DatasetCreateView
from vitrina.datasets.views import DatasetDetailView
from vitrina.datasets.views import DatasetDistributionPreviewView
from vitrina.datasets.views import DatasetHistoryView
from vitrina.datasets.views import DatasetListView
from vitrina.datasets.views import DatasetManagementsView
from vitrina.datasets.views import DatasetMembersView
from vitrina.datasets.views import DatasetProjectsView
from vitrina.datasets.views import DatasetStatsView
from vitrina.datasets.views import DatasetStructureImportView
from vitrina.datasets.views import DatasetAttributionCreateView
from vitrina.datasets.views import DatasetAttributionDeleteView
from vitrina.datasets.views import DatasetUpdateView
from vitrina.datasets.views import DeleteMemberView
from vitrina.datasets.views import RemoveProjectView
from vitrina.datasets.views import UpdateMemberView
from vitrina.datasets.views import autocomplete_tags
from vitrina.datasets.views import DatasetsStatsView

urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    path('datasets/stats/status/', DatasetStatsView.as_view(), name="dataset-status-stats"),
    # @GetMapping("/dataset/{slug}")
    path('datasets/stats/yearly', DatasetsStatsView.as_view(), name='dataset-stats-yearly'),
    path('datasets/<int:pk>/add/', DatasetCreateView.as_view(), name='dataset-add'),
    path('datasets/<int:pk>/update/', DatasetUpdateView.as_view(), name='dataset-change'),
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<int:dataset_id>/preview/<int:distribution_id>/', DatasetDistributionPreviewView.as_view(),
         name='dataset-distribution-preview'),
    path('datasets/<int:pk>/structure/import/', DatasetStructureImportView.as_view(),
         name='dataset-structure-import'),
    path('datasets/<int:pk>/history/', DatasetHistoryView.as_view(), name="dataset-history"),
    path('datasets/<int:pk>/members/', DatasetMembersView.as_view(), name='dataset-members'),
    path('datasets/<int:pk>/projects/', DatasetProjectsView.as_view(), name='dataset-projects'),
    path('datasets/<int:pk>/projects/<int:project_id>/remove',
         RemoveProjectView.as_view(),
         name='dataset-project-remove'),
    path('datasets/<int:pk>/projects/add',
         AddProjectView.as_view(),
         name='dataset-project-add'),
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
    path(
        'datasets/tags/autocomplete/',
        autocomplete_tags,
        {'tag_model': Dataset.tags.tag_model},
        name='autocomplete_tags',
    ),
    path(
        'dataset/stats/jurisdiction/',
        DatasetManagementsView.as_view(),
        name='dataset-stats-jurisdiction'
    ),
    path('datasets/<int:dataset_id>/attribution/add/', DatasetAttributionCreateView.as_view(), name="attribution-add"),
    path('datasets/<int:dataset_id>/attribution/delete/<int:pk>',
         DatasetAttributionDeleteView.as_view(), name="attribution-delete"),
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
