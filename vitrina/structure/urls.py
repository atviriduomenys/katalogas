from django.urls import path

from vitrina.structure.views import DatasetStructureView
from vitrina.structure.views import ModelStructureView
from vitrina.structure.views import PropertyStructureView
from vitrina.structure.views import ModelDataView
from vitrina.structure.views import ObjectDataView
from vitrina.structure.views import EnumCreateView
from vitrina.structure.views import EnumUpdateView
from vitrina.structure.views import EnumDeleteView

urlpatterns = [
    path('datasets/<int:pk>/models/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/models/<str:model>/', ModelStructureView.as_view(), name='model-structure'),
    path('datasets/<int:pk>/models/<str:model>/<str:prop>/',
         PropertyStructureView.as_view(), name='property-structure'),
    path('datasets/<int:pk>/data/<str:model>/', ModelDataView.as_view(), name='model-data'),
    path('datasets/<int:pk>/data/<str:model>/<str:uuid>/', ObjectDataView.as_view(), name='object-data'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/add/', EnumCreateView.as_view(), name='enum-create'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/<int:enum_id>/change/',
         EnumUpdateView.as_view(), name='enum-update'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/<int:enum_id>/delete/',
         EnumDeleteView.as_view(), name='enum-delete'),
]
