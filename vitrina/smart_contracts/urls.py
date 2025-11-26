from django.urls import path

from vitrina.smart_contracts.views import (
    AgreementCreateView,
    AgreementListView,
    AgreementDetailView,
    AgreementUploadSignedFile,
    AgreementSubmitView,
    AgreementApproveView,
    AgreementFormView,
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
        "projects/<int:pk>/agreement/<uuid:agreement_id>/submit/",
        AgreementSubmitView.as_view(),
        name="agreement-submit",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/approve/",
        AgreementApproveView.as_view(),
        name="agreement-approve",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/form",
        AgreementFormView.as_view(),
        name="agreement-form",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/upload-signed/",
        AgreementUploadSignedFile.as_view(),
        name="agreement-upload-signed-adoc",
    ),
]
