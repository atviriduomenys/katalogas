from django.views.generic import TemplateView


class PolicyView(TemplateView):
    template_name = 'vitrina/cms/policy.html'
