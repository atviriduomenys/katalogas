from django.urls import path

from vitrina.smart_contracts.views import AgreementCreateView

urlpatterns = [
    path(
        "projects/<int:pk>/agreement/add/",
        AgreementCreateView.as_view(),
        name="agreement-create",
    ),
]
