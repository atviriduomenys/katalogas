from vitrina.redirections.models import Redirections
from django.shortcuts import redirect


def redirection_handler(request, exception):
    try:
        existing_url = Redirections.objects.filter(path=request.path)
        new_url = existing_url.content_object.get_absolute_url
        return redirect(new_url)
    except:
        return redirect('home')
