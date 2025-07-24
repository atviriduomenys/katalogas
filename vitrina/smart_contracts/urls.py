from django.urls import path

from vitrina.smart_contracts.views import (
    AgreementCreateView,
    AgreementListView,
    AgreementDetailView,
    AgreementGeneratePdf,
    AgreementUploadSignedFile,
)

urlpatterns = [
    path(
        "projects/<int:pk>/agreement/add/",
        AgreementCreateView.as_view(),
        name="agreement-create",
    ),
    path(
        "projects/<int:pk>/agreement/",
        AgreementListView.as_view(),
        name="agreement-list",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/",
        AgreementDetailView.as_view(),
        name="agreement-detail",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/generate-pdf/",
        AgreementGeneratePdf.as_view(),
        name="agreement-generate-pdf",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/upload-signed/",
        AgreementUploadSignedFile.as_view(),
        name="agreement-upload-signed-adoc",
    ),
]
