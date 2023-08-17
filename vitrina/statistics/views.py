from django.views.generic import ListView

from vitrina.statistics.models import StatRoute


class StatRouteListView(ListView):
    template_name = 'vitrina/statistics/list.html'
    model = StatRoute
    paginate_by = 20
    ordering = ('order',)
