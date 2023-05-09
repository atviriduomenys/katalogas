from typing import Type

from django.db.models import Model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from reversion.models import Version

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization, Representative
from vitrina.users.models import User
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project


def home(request):
    coordinator_count = User.objects.select_related('representative').filter(
        representative__role='coordinator'
    ).distinct('representative__user').count()
    manager_count = User.objects.select_related('representative').filter(
        representative__role='manager'
    ).exclude(representative__role='coordinator').distinct('representative__user').count()
    user_count = User.objects.exclude(representative__role='manager').exclude(representative__role='coordinator').count()
    return render(request, 'landing.html', {
        'counts': {
            'dataset': Dataset.public.count(),
            'organization': Organization.public.count(),
            'project': Project.public.count(),
            'coordinators': coordinator_count,
            'managers': manager_count,
            'users': user_count
        },
        'categories': (
            Category.objects.
            filter(featured=True).
            order_by('title')
        )
    })

class HistoryView(PermissionRequiredMixin, TemplateView):
    template_name = 'history.html'
    model: Type[Model] = None
    detail_url_name = None
    history_url_name = None
    tabs_template_name: str

    object: Model

    def dispatch(self, request, *args, **kwargs):
        object_id = self.kwargs.get('pk')
        self.object = get_object_or_404(self.model, pk=object_id)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.HISTORY_VIEW, self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "detail_url_name": self.get_detail_url_name(),
            "history_url_name": self.get_history_url_name(),
            "history": [
                {
                    'date': version.revision.date_created,
                    'user': version.revision.user,
                    'action': self.model.HISTORY_MESSAGES.get(
                        version.revision.comment,
                    ),
                }
                for version in (
                    Version.objects.
                    get_for_object(self.object).
                    order_by('-revision__date_created')
                )
            ],
            'can_manage_history': has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                self.object,
            ),
            'tabs_template_name': self.tabs_template_name,
        })
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name


class HistoryMixin:
    detail_url_name = None
    history_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'detail_url_name': self.get_detail_url_name(),
            'history_url_name': self.get_history_url_name(),
            'can_manage_history': has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                self.object,
            )
        })
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name


