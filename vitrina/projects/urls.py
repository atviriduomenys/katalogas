from django.urls import path

from vitrina.projects.views import ProjectListView, ProjectDetailView

urlpatterns = [
    # @GetMapping("/usecases/examples")
    path('projects/', ProjectListView.as_view(), name='project-list'),
    path('projects/<int:pk>', ProjectDetailView.as_view(), name='project-detail'),
    # @GetMapping("/usecase")
    # @PostMapping("/usecase")
    # @GetMapping("/usecases/applications")
    # @GetMapping("/application")
    # @PostMapping("/application")
    # @GetMapping("/usecases/application")
    # @GetMapping("/usecases/submitusecase")
]
