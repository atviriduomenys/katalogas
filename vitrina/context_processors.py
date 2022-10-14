from django.contrib.sites.models import Site

from vitrina import settings


def current_domain(request):
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    return {
       "current_domain_full": request.build_absolute_uri("%s://%s" % (protocol, domain)),
       "current_domain": domain,
    }


def current_language(request):
    if request.GET.get('language'):
        language = request.GET.get('language')
        settings.LANGUAGE_CODE = language
    else:
        language = settings.LANGUAGE_CODE
    return {
        "LANGUAGE_CODE": language
    }
