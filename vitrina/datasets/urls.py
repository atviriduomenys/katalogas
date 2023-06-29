from django.urls import path

from vitrina.datasets.models import Dataset
from vitrina.datasets.views import AddProjectView
from vitrina.datasets.views import OrganizationStatsView
from vitrina.datasets.views import QuarterStatsView
from vitrina.datasets.views import DatasetsTagsView
from vitrina.datasets.views import YearStatsView
from vitrina.datasets.views import DatasetsFormatView
from vitrina.datasets.views import DatasetsFrequencyView
from vitrina.datasets.views import DatasetsOrganizationsView
from vitrina.datasets.views import DatasetsCategoriesView
from vitrina.datasets.views import DatasetsLevelView
from vitrina.datasets.views import PublicationStatsView
from vitrina.datasets.views import CategoryStatsView
from vitrina.datasets.views import JurisdictionStatsView
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
from vitrina.datasets.views import DatasetUpdateView
from vitrina.datasets.views import DeleteMemberView
from vitrina.datasets.views import RemoveProjectView
from vitrina.datasets.views import UpdateMemberView
from vitrina.datasets.views import autocomplete_tags
from vitrina.datasets.views import DatasetsStatsView
from vitrina.datasets.views import DatasetCategoryView
from vitrina.datasets.views import FilterCategoryView

urlpatterns = [
    # @GetMapping("/datasets")`
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('datasets/stats/status/', DatasetStatsView.as_view(), name="dataset-status-stats"),
    path('datasets/stats/level/', DatasetsLevelView.as_view(), name='dataset-stats-level'),
    path('datasets/stats/jurisdiction/', DatasetManagementsView.as_view(), name='dataset-stats-jurisdiction'),
    path('datasets/stats/jurisdiction/<int:pk>/', JurisdictionStatsView.as_view(),
         name='dataset-stats-jurisdiction-children'),
    # path('datasets/stats/yearly/', DatasetsStatsView.as_view(), name='dataset-stats-yearly'),
    path('datasets/stats/organization/', DatasetsOrganizationsView.as_view(), name='dataset-stats-organization'),
    # path('datasets/stats/organization/<int:pk>', OrganizationStatsView.as_view(), name='dataset-stats-organization-children'),
    path('datasets/stats/category/', DatasetsCategoriesView.as_view(), name='dataset-stats-category'),
    path('datasets/stats/category/<int:pk>/', CategoryStatsView.as_view(), name='dataset-stats-category-children'),
    path('datasets/stats/tag/', DatasetsTagsView.as_view(), name='dataset-stats-tag'),
    path('datasets/stats/format/', DatasetsFormatView.as_view(), name='dataset-stats-format'),
    path('datasets/stats/frequency/', DatasetsFrequencyView.as_view(), name='dataset-stats-frequency'),
    path('datasets/stats/publication/', PublicationStatsView.as_view(), name='dataset-stats-publication'),
    path('datasets/stats/publication/year/<int:year>/', YearStatsView.as_view(), name='dataset-stats-publication-year'),
    path('datasets/stats/publication/quarter/<str:quarter>/', QuarterStatsView.as_view(), name='dataset-stats-publication-quarter'),
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
    path('datasets/<int:dataset_id>/category/', DatasetCategoryView.as_view(), name='assign-category'),
    path('datasets/<int:dataset_id>/filter_categories/', FilterCategoryView.as_view(), name='filter-categories'),
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
