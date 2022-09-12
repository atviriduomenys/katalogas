from django.urls import path

from vitrina.tasks.views import TaskListView

urlpatterns = [
    path('users/<int:pk>/tasks/', TaskListView.as_view(), name='user-task-list'),
]
