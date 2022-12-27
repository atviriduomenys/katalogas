from django.urls import path, include
from djangocms_blog.settings import get_setting

from vitrina.cms.views import PolicyView, PostDetailView, LearningMaterialDetailView, SparqlView, ReportDetailView


def get_urls():
    urls = get_setting("PERMALINK_URLS")
    details = []
    for urlconf in urls.values():
        details.append(
            path(urlconf, PostDetailView.as_view(), name="post-detail"),
        )
    return details


post_detail_urls = get_urls()

urlpatterns = [
    # @RequestMapping("/page")
    # @GetMapping("/{slug}")
    # @GetMapping("/opening/addMaterial")
    # @PostMapping("/opening/addMaterial")
    # @GetMapping("/about")
    path('policy/', PolicyView.as_view(), name='policy'),
    path('blog/', include(post_detail_urls)),
    path('opening/learningmaterial/<int:pk>/', LearningMaterialDetailView.as_view(), name='learning-material-detail'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report-detail'),
    path('sparql/', SparqlView.as_view(), name='sparql'),
    # @GetMapping("/other")
    # @GetMapping("/opening")
    # @GetMapping("/opening/tips")
    # @GetMapping("/opening/tools")
    # @GetMapping("/opening/technical")
    # @GetMapping("/opening/learningmaterial")
    # @GetMapping("/regulation")
    # @GetMapping("/regulation/legal")
    # @GetMapping("/regulation/recommendations")
    # @GetMapping("/regulation/strategic")
    # @GetMapping("/regulation/rules")
    # @GetMapping("/news")
    # @GetMapping("/opening/faq")
    # @GetMapping("/terms")
    # @GetMapping("/regulation/rules/{id}")
    # @GetMapping("/news/{id}")
    # @GetMapping("/opening/learningmaterial/{id}")
    # @GetMapping("/contacts")
    # @GetMapping("/learningmaterial")
    # @GetMapping("/learningmaterial/{id}")
]
