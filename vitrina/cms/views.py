from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.views.generic import TemplateView, DetailView
from djangocms_blog.views import PostDetailView as BasePostDetailView
from django.utils.translation import gettext_lazy as _


from vitrina.cms.models import LearningMaterial, FileResource
from vitrina.orgs.models import PublishedReport


class PolicyView(TemplateView):
    template_name = 'vitrina/cms/policy.html'


class PostDetailView(BasePostDetailView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['files'] = FileResource.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk
        )
        return context

    def get_template_names(self):
        return "vitrina/cms/post_detail.html"


class LearningMaterialDetailView(DetailView):
    model = LearningMaterial
    template_name = 'vitrina/cms/learning_material_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
        }
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
