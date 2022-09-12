from django.contrib.sites.models import Site


def current_domain(request):
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    return {
       "current_domain_full": request.build_absolute_uri("%s://%s" % (protocol, domain)),
       "current_domain": domain,
    }
