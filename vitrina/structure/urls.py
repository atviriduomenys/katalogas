from django.urls import path

from vitrina.structure.views import DatasetStructureView
from vitrina.structure.views import DatasetStructureExportView
from vitrina.structure.views import ModelStructureView
from vitrina.structure.views import PropertyStructureView
from vitrina.structure.views import ModelDataView
from vitrina.structure.views import ObjectDataView
from vitrina.structure.views import EnumCreateView
from vitrina.structure.views import EnumUpdateView
from vitrina.structure.views import EnumDeleteView
from vitrina.structure.views import GetAllApiView
from vitrina.structure.views import GetOneApiView
from vitrina.structure.views import ChangesApiView
from vitrina.structure.views import ModelCreateView
from vitrina.structure.views import ModelUpdateView
from vitrina.structure.views import PropertyCreateView
from vitrina.structure.views import PropertyUpdateView
from vitrina.structure.views import CreateBasePropertyView
from vitrina.structure.views import DeleteBasePropertyView

urlpatterns = [
    path('datasets/<int:pk>/models/', DatasetStructureView.as_view(), name='dataset-structure'),
    path('datasets/<int:pk>/models/add/', ModelCreateView.as_view(), name='model-create'),
    path('datasets/<int:pk>/models/<str:model>/change/', ModelUpdateView.as_view(), name='model-update'),
    path('datasets/<int:pk>/models/<str:model>/add/',
         PropertyCreateView.as_view(), name='property-create'),
    path('datasets/<int:pk>/models/<str:model>/', ModelStructureView.as_view(), name='model-structure'),
    path('datasets/<int:pk>/models/<str:model>/<str:prop>/',
         PropertyStructureView.as_view(), name='property-structure'),
    path('datasets/<int:pk>/models/<str:model>/<str:prop>/change/',
         PropertyUpdateView.as_view(), name='property-update'),
    path('datasets/<int:pk>/data/<str:model>/', ModelDataView.as_view(), name='model-data'),
    path('datasets/<int:pk>/data/<str:model>/<str:uuid>/', ObjectDataView.as_view(), name='object-data'),
    path('datasets/<int:pk>/<int:model_id>/add_prop/<int:prop_id>/',
         CreateBasePropertyView.as_view(), name='base-property-create'),
    path('datasets/<int:pk>/<int:model_id>/delete_prop/<int:prop_id>/',
         DeleteBasePropertyView.as_view(), name='base-property-delete'),
    path('datasets/<int:pk>/api/getall/<str:model>/', GetAllApiView.as_view(), name='getall-api'),
    path('datasets/<int:pk>/api/getone/<str:model>/<str:uuid>/', GetOneApiView.as_view(), name='getone-api'),
    path('datasets/<int:pk>/api/changes/<str:model>/', ChangesApiView.as_view(), name='changes-api'),
    path('datasets/<int:pk>/structure/export/', DatasetStructureExportView.as_view(), name='dataset-structure-export'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/add/', EnumCreateView.as_view(), name='enum-create'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/<int:enum_id>/change/',
         EnumUpdateView.as_view(), name='enum-update'),
    path('datasets/<int:pk>/<str:model>/<str:prop>/enum/<int:enum_id>/delete/',
         EnumDeleteView.as_view(), name='enum-delete'),
]
