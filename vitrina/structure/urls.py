from django.urls import path

from vitrina.structure.views import DatasetStructureView
from vitrina.structure.views import ModelStructureView
from vitrina.structure.views import PropertyStructureView
from vitrina.structure.views import ModelDataView
from vitrina.structure.views import ObjectDataView

urlpatterns = [
    path('datasets/<int:pk>/models/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:dataset_id>/models/<str:model>/', ModelStructureView.as_view(), name='model-structure'),
    path('datasets/<int:dataset_id>/models/<str:model>/<str:prop>/',
         PropertyStructureView.as_view(), name='property-structure'),
    path('datasets/<int:dataset_id>/data/<str:model>/', ModelDataView.as_view(), name='model-data'),
    path('datasets/<int:dataset_id>/data/<str:model>/<str:uuid>/', ObjectDataView.as_view(), name='object-data'),
]
