from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from reversion.models import Version

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project


def home(request):
    return render(request, 'landing.html', {
        'counts': {
            'dataset': Dataset.public.count(),
            'organization': Organization.public.count(),
            'project': Project.public.count(),
        },
        'categories': (
            Category.objects.
            filter(featured=True).
            order_by('title')
        )
    })


class HistoryView(PermissionRequiredMixin, TemplateView):
    template_name = 'history.html'
    model = None
    detail_url_name = None
    history_url_name = None
    tabs_template_name: str

    def has_permission(self):
        obj_id = self.kwargs.get('pk')
        obj = get_object_or_404(self.model, pk=obj_id)
        return has_perm(self.request.user, Action.HISTORY_VIEW, obj)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.kwargs.get('pk')
        obj = get_object_or_404(self.model, pk=obj_id)
        extra_context = {
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
                    get_for_object(obj).
                    order_by('-revision__date_created')
                )
            ],
            'can_manage_history': has_perm(
                self.request.user,
                Action.HISTORY_VIEW,
                obj,
            ),
            'tabs_template_name': self.tabs_template_name,
        }
        context.update(extra_context)
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
        extra_context = {
            'detail_url_name': self.get_detail_url_name(),
            'history_url_name': self.get_history_url_name(),
            'can_manage_history': has_perm(self.request.user, Action.HISTORY_VIEW, self.object)
        }
        context.update(extra_context)
        return context

    def get_detail_url_name(self):
        return self.detail_url_name

    def get_history_url_name(self):
        return self.history_url_name
