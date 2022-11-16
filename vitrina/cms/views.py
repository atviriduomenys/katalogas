from django.views.generic import TemplateView, DetailView

from vitrina.cms.models import LearningMaterial, FileResource
from vitrina.orgs.models import PublishedReport


class PolicyView(TemplateView):
    template_name = 'vitrina/cms/policy.html'


class LearningMaterialDetailView(DetailView):
    model = LearningMaterial
    template_name = 'vitrina/cms/learning_material_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'files': FileResource.objects.filter(
                obj_class__contains=self.model.__name__,
                obj_id=self.object.pk
            )
        })
        return context


class ReportDetailView(DetailView):
    model = PublishedReport
    template_name = 'vitrina/cms/report_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'lines': [{
                'cols': item.split("&&&")
            } for item in self.object.data.split("\n")]
        })
        return context


class SparqlView(TemplateView):
    template_name = 'vitrina/cms/sparql.html'
