from django import forms
from django.utils.translation import gettext_lazy as _

from vitrina.search.queries import apply_selected_facets


class SearchForm(forms.Form):
    q = forms.CharField(required=False, label=_("Paieška"))

    facet_model = None
    facet_fk = None

    def __init__(self, *args, queryset=None, selected_facets=None, **kwargs):
        self.queryset = queryset
        self.selected_facets = list(selected_facets or [])
        super().__init__(*args, **kwargs)

    def no_query_found(self):
        return self.queryset

    def filter_by_text(self, queryset, keyword):
        raise NotImplementedError

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        queryset = self.queryset
        keyword = self.cleaned_data.get("q")
        if keyword:
            queryset = self.filter_by_text(queryset, keyword)
        if self.facet_model:
            queryset = apply_selected_facets(queryset, self.facet_model, self.facet_fk, self.selected_facets)
        return queryset
