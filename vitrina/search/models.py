from django.db import models

from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request


class SearchDoc(models.Model):
    text = models.TextField(blank=True, default="")

    class Meta:
        abstract = True


class SearchFacet(models.Model):
    field = models.CharField(max_length=32)
    value = models.CharField(max_length=255)

    class Meta:
        abstract = True


class DatasetSearchDoc(SearchDoc):
    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="search_doc",
    )
    title_lt = models.TextField(blank=True, default="")
    title_en = models.TextField(blank=True, default="")
    published_or_created = models.DateTimeField(null=True, blank=True)
    type_order = models.IntegerField(default=0)

    class Meta:
        db_table = "search_dataset_doc"


class DatasetSearchFacet(SearchFacet):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="search_facets",
    )

    class Meta:
        db_table = "search_dataset_facet"
        unique_together = ("dataset", "field", "value")
        indexes = [models.Index(fields=["field", "value"])]


class RequestSearchDoc(SearchDoc):
    request = models.OneToOneField(
        Request,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="search_doc",
    )
    title_lt = models.TextField(blank=True, default="")
    title_en = models.TextField(blank=True, default="")

    class Meta:
        db_table = "search_request_doc"


class RequestSearchFacet(SearchFacet):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="search_facets",
    )

    class Meta:
        db_table = "search_request_facet"
        unique_together = ("request", "field", "value")
        indexes = [models.Index(fields=["field", "value"])]
