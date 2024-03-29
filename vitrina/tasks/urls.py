from django.urls import path

from vitrina.tasks.views import TaskListView, TaskView, CloseTaskView, AssignTaskView

urlpatterns = [
    path('users/<int:pk>/tasks/', TaskListView.as_view(), name='user-task-list'),
    path('users/<int:pk>/tasks/<int:task_id>/', TaskView.as_view(), name='user-task-detail'),
    path('users/<int:pk>/tasks/<int:task_id>/close/', CloseTaskView.as_view(), name='user-task-close'),
    path('users/<int:pk>/tasks/<int:task_id>/assign/', AssignTaskView.as_view(), name='user-task-assign')
]
