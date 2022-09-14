from django.urls import path

from vitrina.datasets.views import DatasetListView, DatasetStructureView, DatasetStructureDownloadView, DatasetDetailView, DatasetMembersView


urlpatterns = [
    # @GetMapping("/datasets")
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    # @GetMapping("/dataset/{slug}")
    path('dataset/<slug:slug>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('datasets/<str:org_kind>/<slug:org_slug>/<slug:slug>/members/',
         DatasetMembersView.as_view(), name='dataset-members'),
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
