from django.urls import path

from vitrina.cms.views import PolicyView

urlpatterns = [
    # @RequestMapping("/page")
    # @GetMapping("/{slug}")
    # @GetMapping("/opening/addMaterial")
    # @PostMapping("/opening/addMaterial")
    # @GetMapping("/about")
    path('policy/', PolicyView.as_view(), name='policy'),
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
