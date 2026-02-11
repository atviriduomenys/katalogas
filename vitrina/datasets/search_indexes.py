from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Exists, OuterRef
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Model, Property
from haystack.fields import (
    CharField,
    IntegerField,
    MultiValueField,
    DateTimeField,
    EdgeNgramField,
    BooleanField,
)
from django.db import models

from haystack import signals
from haystack.exceptions import NotHandled
from haystack.indexes import SearchIndex, Indexable

from vitrina.datasets.models import Dataset
from vitrina.requests.models import RequestObject, Request


class DatasetIndex(SearchIndex, Indexable):
    django_pk = IntegerField(model_attr="pk")
    text = EdgeNgramField(document=True, use_template=True)
    # used for search
    lt_title = CharField(model_attr="lt_title", boost=1)
    lt_title_s = CharField(model_attr="lt_title", indexed=False, stored=True, boost=1)
    en_title = CharField(model_attr="en_title", boost=1)
    en_title_s = CharField(model_attr="en_title", indexed=False, stored=True, boost=1)
    tags = MultiValueField(model_attr="get_tag_list", faceted=True, boost=1)
    lt_description = CharField(model_attr="lt_description", boost=0.9)
    lt_description_s = CharField(model_attr="lt_description", indexed=False, stored=True, boost=0.9)
    en_description = CharField(model_attr="en_description", boost=0.9)
    en_description_s = CharField(model_attr="en_description", indexed=False, stored=True, boost=0.9)
    name = CharField(model_attr="name", boost=0.9)
    resource_title = MultiValueField(model_attr="get_resource_titles", boost=0.9)
    model_title = MultiValueField(model_attr="get_model_title_list", boost=0.9)
    model_names = MultiValueField(model_attr="get_model_name_list", boost=0.9)
    property_title = MultiValueField(model_attr="get_property_title_list", boost=0.9)
    request_title = MultiValueField(model_attr="get_request_title_list", boost=0.9)
    project_title = MultiValueField(model_attr="get_project_title_list", boost=0.9)
    category = MultiValueField(model_attr="category__pk", faceted=True, boost=0.8)
    organization = MultiValueField(model_attr="organization__pk", faceted=True, null=True, boost=0.8)
    resource_description = MultiValueField(model_attr="get_resource_description", boost=0.7)
    model_description = MultiValueField(model_attr="get_model_title_description", boost=0.7)
    property_description = MultiValueField(model_attr="get_property_title_description", boost=0.7)
    request_description = MultiValueField(model_attr="get_request_title_description", boost=0.7)
    project_description = MultiValueField(model_attr="get_project_title_description", boost=0.7)
    parent_category = MultiValueField(model_attr="parent_category", faceted=True, null=True, boost=0.6)
    parent_category_titles = MultiValueField(model_attr="parent_category_titles", boost=0.6)
    parent_organization_title = CharField(model_attr="get_parent_organization_title", boost=0.6)
    # only for filters
    published_created_s = DateTimeField(model_attr="published_created_sort", indexed=False, stored=True)
    jurisdiction = MultiValueField(model_attr="jurisdiction", faceted=True, null=True)
    groups = MultiValueField(model_attr="get_group_list", faceted=True)
    formats = MultiValueField(model_attr="filter_formats", faceted=True)
    frequency = IntegerField(model_attr="frequency__pk", faceted=True)
    published = DateTimeField(model_attr="published", null=True, faceted=True)
    status = CharField(model_attr="status", faceted=True, null=True)
    level = IntegerField(model_attr="get_level", faceted=True, null=True)
    lt_subclass_title = CharField(model_attr="lt_subclass_title", indexed=True)
    en_subclass_title = CharField(model_attr="en_subclass_title", indexed=True)
    subclass = CharField(model_attr="subclass__name", faceted=True)
    type = MultiValueField(model_attr="public_types", faceted=True)
    type_order = IntegerField(model_attr="type_order")
    is_public = BooleanField(model_attr="is_public", faceted=True, null=False)
    resource_managers = MultiValueField(model_attr="resource_managers", faceted=True)
    open_data_managers = MultiValueField(model_attr="open_data_managers", faceted=True)
    access_rights = CharField(model_attr="access_rights", faceted=True, null=True)
    publisher = MultiValueField(model_attr="publisher__pk", faceted=True, null=True)

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        DatasetTranslation = Dataset._parler_meta.root_model
        return (
            self.get_model()
            .objects.all()
            .filter(
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
            )
            .filter(Exists(DatasetTranslation.objects.filter(master_id=OuterRef("pk"), title__isnull=False)))
            .select_related(
                "organization",
                "organization__jurisdiction",
                "frequency",
                "subclass",
            )
            .prefetch_related(
                "tags",
                "translations",
                "subclass__translations",
                "category",
                "category__datasetgroupcategoryuri_set",
                "excluded_groups",
                "type",
                "part_of",
                "related_datasets",
                "metadata",
                "representatives",
                "organization__representatives",
                "project_set",
                Prefetch(
                    "datasetdistribution_set",
                    queryset=DatasetDistribution.objects.select_related("format").prefetch_related("translations"),
                ),
                Prefetch(
                    "model_set",
                    queryset=Model.objects.prefetch_related(
                        "metadata",
                        Prefetch(
                            "model_properties",
                            queryset=Property.objects.prefetch_related("metadata"),
                        ),
                    ),
                ),
                Prefetch("dataset_request", queryset=Request.objects.prefetch_related("translations")),
            )
        )

    def prepare_category(self, obj):
        categories = []
        for category in obj.category.all():
            categories.extend([cat.pk for cat in category.get_ancestors() if cat.dataset_set.exists()])
            categories.append(category.pk)
        return categories


class CustomSignalProcessor(signals.BaseSignalProcessor):
    def setup(self):
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)

    def teardown(self):
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)

    def handle_save(self, sender, instance, **kwargs):
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(sender)

                if index.index_queryset().filter(pk=instance.pk):
                    index.update_object(instance, using=using)
                    if isinstance(instance, Dataset):
                        req_index = self.connections[using].get_unified_index().get_index(Request)
                        reqs = RequestObject.objects.filter(
                            content_type=ContentType.objects.get_for_model(instance),
                            object_id=instance.pk,
                        )
                        for req in reqs:
                            req_index.update_object(req.request, using=using)
                else:
                    index.remove_object(instance, using=using)

            except NotHandled:
                pass
