from django.urls import path

from vitrina.tasks.views import TaskListView, TaskView

urlpatterns = [
    path('users/<int:pk>/tasks/', TaskListView.as_view(), name='user-task-list'),
    path('users/<int:pk>/tasks/<int:task_id>/', TaskView.as_view(), name='user-task-view'),
]
