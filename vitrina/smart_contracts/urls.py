from django.urls import path

from vitrina.smart_contracts.views import (
    AgreementCreateView,
    ProjectAgreementListView,
    ProjectAgreementDetailView,
    ProjectBasedAgreementSubmitView,
    ProjectBasedAgreementApproveView,
    ProjectBasedAgreementFormView,
    ProjectBasedAgreementInitiateView,
    ProjectBasedAgreementSignView,
)

urlpatterns = [
    path(
        "projects/<int:pk>/agreement/add/",
        AgreementCreateView.as_view(),
        name="project-agreement-create",
    ),
    path(
        "projects/<int:pk>/agreement/",
        ProjectAgreementListView.as_view(),
        name="project-agreement-list",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/",
        ProjectAgreementDetailView.as_view(),
        name="project-agreement-detail",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/submit/",
        ProjectBasedAgreementSubmitView.as_view(),
        name="project-agreement-submit",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/approve/",
        ProjectBasedAgreementApproveView.as_view(),
        name="project-agreement-approve",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/form/",
        ProjectBasedAgreementFormView.as_view(),
        name="project-agreement-form",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/initiate/",
        ProjectBasedAgreementInitiateView.as_view(),
        name="project-agreement-initiate",
    ),
    path(
        "projects/<int:pk>/agreement/<uuid:agreement_id>/sign/",
        ProjectBasedAgreementSignView.as_view(),
        name="project-agreement-sign",
    ),
]
