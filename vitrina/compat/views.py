from django.http import HttpResponseNotFound, HttpResponse
from vitrina.compat.models import Redirections


def redirection_handler(request, exception):
    try:
        existing_url = Redirections.objects.get(path=str(request.path))
        new_url = existing_url.content_object
        response = HttpResponse(status=308)
        response['location'] = new_url
        return response
    except:
        return HttpResponseNotFound()
