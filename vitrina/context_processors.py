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
    elif request.session.get('LANGUAGE_CODE'):
        language = request.session.get('LANGUAGE_CODE')
    else:
        language = settings.LANGUAGE_CODE
    request.session['LANGUAGE_CODE'] = language
    request.session.modified = True
    return {
        "LANGUAGE_CODE": language
    }
