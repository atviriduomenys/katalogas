from cms.utils.i18n import get_current_language
from django.contrib.sites.models import Site
from django.utils import translation


def current_domain(request):
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    return {
       "current_domain_full": request.build_absolute_uri("%s://%s" % (protocol, domain)),
       "current_domain": domain,
    }


def current_language(request):
    if request.GET.get('language'):
        user_language = request.GET.get('language')
        translation.activate(user_language)
        request.session[translation.LANGUAGE_SESSION_KEY] = user_language
    return {
        "LANGUAGE_CODE": get_current_language()
    }
