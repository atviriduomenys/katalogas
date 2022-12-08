from django.urls import path

from vitrina.projects.views import ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, \
    ProjectHistoryView, ProjectDatasetsView, RemoveDatasetView

urlpatterns = [
    # @GetMapping("/usecases/examples")
    path('projects/', ProjectListView.as_view(), name='project-list'),
    path('projects/<int:pk>', ProjectDetailView.as_view(), name='project-detail'),
    path('projects/add/', ProjectCreateView.as_view(), name='project-create'),
    path('projects/<int:pk>/change/', ProjectUpdateView.as_view(), name='project-update'),
    path('projects/<int:pk>/history/', ProjectHistoryView.as_view(), name='project-history'),
    path('projects/<int:pk>/datasets/', ProjectDatasetsView.as_view(), name='project-datasets'),
    path('projects/<int:pk>/datasets/<int:dataset_id>/remove/', RemoveDatasetView.as_view(),
         name='project-dataset-remove'),
    # @GetMapping("/usecase")
    # @PostMapping("/usecase")
    # @GetMapping("/usecases/applications")
    # @GetMapping("/application")
    # @PostMapping("/application")
    # @GetMapping("/usecases/application")
    # @GetMapping("/usecases/submitusecase")
]
