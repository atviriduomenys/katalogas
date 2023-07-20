from typing import Type

from django.db.models import Model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django.db.models import Count

from reversion.models import Version

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request
from vitrina.projects.models import Project
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
        ),
        'datasets': (
            Dataset.public.
            select_related('organization').
            order_by('-published')[:3]
        ),
        'requests': (
            Request.public.
            select_related('organization').
            order_by('-created')[:3]
        ),
        'projects': (
            Project.public.
            filter(
                image__isnull=False,
            ).
            order_by('-created')[:3]
        ),
        'orgs': (
            Organization.public.
            filter(
                numchild=0,
                image__isnull=False,
            ).
            annotate(datasets=Count('dataset')).
            order_by('-datasets')[:3]
        ),
    })


class PlanMixin:
    object: Model
    plan_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'plan_url_name': self.get_plan_url_name(),
            'plan_url': self.get_plan_url(),
        })
        return context

    def get_plan_url_name(self):
        return self.plan_url_name

    def get_plan_url(self):
        obj = self.get_plan_object()
        url_name = self.get_plan_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_plan_object(self):
        return self.object


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
            'detail_url_name': self.get_detail_url_name(),
            'history_url_name': self.get_history_url_name(),
            'detail_url': self.get_detail_url(),
            'history_url': self.get_history_url(),
            "history": [
                {
                    'date': version.revision.date_created,
                    'user': version.revision.user,
                    'action': self.model.HISTORY_MESSAGES.get(
                        version.revision.comment,
                    ) if (
                        hasattr(self.model, 'HISTORY_MESSAGES') and
                        self.model.HISTORY_MESSAGES.get(version.revision.comment)
                    ) else version.revision.comment,
                }
                for version in self.get_history_objects()
            ],
            'can_manage_history': has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                self.get_history_object(),
            ),
            'tabs_template_name': self.tabs_template_name,
        })
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name

    def get_detail_url(self):
        obj = self.get_detail_object()
        url_name = self.get_detail_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_url(self):
        obj = self.get_history_object()
        url_name = self.get_history_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_object(self):
        return self.object

    def get_detail_object(self):
        return self.object

    def get_history_objects(self):
        return (
            Version.objects.
            get_for_object(self.get_history_object()).
            order_by('-revision__date_created')
        )


class HistoryMixin:
    detail_url_name = None
    history_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'detail_url_name': self.get_detail_url_name(),
            'history_url_name': self.get_history_url_name(),
            'detail_url': self.get_detail_url(),
            'history_url': self.get_history_url(),
            'can_manage_history': has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                self.get_history_object(),
            )
        })
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name

    def get_detail_url(self):
        obj = self.get_detail_object()
        url_name = self.get_detail_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_url(self):
        obj = self.get_history_object()
        url_name = self.get_history_url_name()
        return reverse(url_name, args=[obj.pk])

    def get_history_object(self):
        return self.object

    def get_detail_object(self):
        return self.object

