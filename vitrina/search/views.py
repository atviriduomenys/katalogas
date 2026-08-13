from django.views.generic import ListView

from vitrina.search.queries import TAGS_FACET_LIMIT, date_facet_counts, facet_counts


class FacetedListView(ListView):
    form_class = None
    facet_fields: list[str] = []
    integer_facet_fields: set[str] = frozenset()
    facet_limits: dict[str, int] = {"tags": TAGS_FACET_LIMIT}
    facet_model = None
    facet_fk = None
    date_facet_field = None
    row_select_related: tuple[str, ...] = ()
    row_prefetch_related: tuple[str, ...] = ()

    def get(self, request, *args, **kwargs):
        self.form = self.get_form()
        self.object_list = self.form.search()
        return self.render_to_response(self.get_context_data())

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.get_paginate_by(queryset):
            return queryset
        if self.row_select_related:
            queryset = queryset.select_related(*self.row_select_related)
        if self.row_prefetch_related:
            queryset = queryset.prefetch_related(*self.row_prefetch_related)
        return queryset

    def get_form(self):
        return self.form_class(
            data=self.request.GET,
            queryset=self.get_queryset(),
            selected_facets=self.request.GET.getlist("selected_facets"),
        )

    def get_facets(self):
        facets = {"fields": {}, "dates": {}}
        if self.facet_model and self.facet_fields:
            facets["fields"] = facet_counts(
                self.object_list,
                self.facet_model,
                self.facet_fk,
                self.facet_fields,
                self.integer_facet_fields,
                self.facet_limits,
            )
        if self.date_facet_field:
            facets["dates"][self.date_facet_field] = date_facet_counts(self.object_list, self.date_facet_field)
        return facets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form
        context["facets"] = self.get_facets()
        context["query"] = self.form.cleaned_data.get("q", "") if self.form.is_valid() else ""
        return context
