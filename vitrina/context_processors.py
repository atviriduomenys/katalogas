from django.contrib.sites.models import Site
from django.conf import settings


def current_domain(request):
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    url = request.build_absolute_uri(f"{protocol}://{domain}")
    return {
        "current_domain_full": url,
        "current_domain": domain,
    }


def feature_flags(request):
    return {
        "IS_PUBLISH_BUTTON_ACTIVE": settings.IS_PUBLISH_BUTTON_ACTIVE,
    }
