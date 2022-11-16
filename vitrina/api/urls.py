from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    # @RequestMapping("/api")
    # @GetMapping("/partner/api/1")
    # @GetMapping("partner/api/1/licences")
    # @GetMapping("/public/api/1")
    path('public/api/1/', TemplateView.as_view(template_name="vitrina/api/public_api.html"), name="public-api"),
    # @GetMapping("/edp/api/1")

    # @RequestMapping("/edp")
    # @RequestMapping("/edp/refresh")
    # @RequestMapping("/edp/dcat-ap.rdf")

    # @GetMapping("/sparql")

    # @RequestMapping("/rdf")
    # @PostMapping("/rdf/search")
]
