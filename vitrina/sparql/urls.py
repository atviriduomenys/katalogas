from django.urls import path

from vitrina.sparql.views import SparqlView

urlpatterns = [
    path("sparql/", SparqlView.as_view(), name="sparql"),
]
