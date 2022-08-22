from django.urls import path

from vitrina.tasks.views import TaskListView

urlpatterns = [
    path('users/<pk>/tasks/', TaskListView.as_view(), name='user-task-list'),
]
