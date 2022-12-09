from django.contrib.contenttypes.models import ContentType
from django.views.generic import TemplateView
from djangocms_blog.views import PostDetailView as BasePostDetailView

from vitrina.cms.models import FileResource


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
