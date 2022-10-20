from django.shortcuts import render

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project


def home(request):
    return render(request, 'landing.html', {
        'counts': {
            'dataset': Dataset.public.count(),
            'organization': Organization.public.count(),
            'project': Project.public.count(),
        },
        'categories': (
            Category.objects.
            filter(featured=True).
            order_by('title')
        )
    })
