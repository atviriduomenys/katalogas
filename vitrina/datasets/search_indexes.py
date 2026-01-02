import logging
from django.contrib.contenttypes.models import ContentType
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
from vitrina.orgs.models import Representative
from vitrina.requests.models import RequestObject, Request
from vitrina.resources.models import DatasetDistribution


logger = logging.getLogger(__name__)


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
    resource_description = MultiValueField(model_attr="get_resource_titles", boost=0.7)
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
    access_rights = CharField(model_attr="access_rights", faceted=True, null=True)
    publisher = MultiValueField(model_attr="publisher__pk", faceted=True, null=True)

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return (
            self.get_model()
            .objects.all()
            .filter(
                deleted__isnull=True,
                deleted_on__isnull=True,
                organization_id__isnull=False,
                translations__title__isnull=False,
            )
            .distinct()
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

        models.signals.post_save.connect(self.handle_representative, sender=Representative)
        models.signals.post_delete.connect(self.handle_representative, sender=Representative)

        models.signals.post_save.connect(self.handle_distribution, sender=DatasetDistribution)
        models.signals.post_delete.connect(self.handle_distribution, sender=DatasetDistribution)

    def teardown(self):
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)

        models.signals.post_save.disconnect(self.handle_representative, sender=Representative)
        models.signals.post_delete.disconnect(self.handle_representative, sender=Representative)

        models.signals.post_save.disconnect(self.handle_distribution, sender=DatasetDistribution)
        models.signals.post_delete.disconnect(self.handle_distribution, sender=DatasetDistribution)

    def handle_distribution(self, sender, instance, **kwargs):
        if instance.dataset_id:
            self._update_single_dataset(instance.dataset_id)

    def handle_representative(self, sender, instance, **kwargs):
        affected_datasets = self._get_affected_datasets(instance)
        self._update_dataset_indexes(affected_datasets)

    def _get_affected_datasets(self, representative):
        dataset_ids = set()
        dataset_ids.update(self._get_direct_datasets(representative))
        dataset_ids.update(self._get_org_generic_fk_datasets(representative))
        dataset_ids.update(self._get_org_direct_fk_datasets(representative))
        return Dataset.objects.filter(pk__in=dataset_ids)

    def _get_direct_datasets(self, representative):
        dataset_ids = set()
        dataset_ct = ContentType.objects.get_for_model(Dataset)

        if representative.content_type_id == dataset_ct.id:
            dataset_ids.add(representative.object_id)
            try:
                dataset = Dataset.objects.get(pk=representative.object_id)
                dataset_ids.update(dataset.get_descendants().values_list("pk", flat=True))
            except Dataset.DoesNotExist:
                logger.warning(f"Dataset {representative.object_id} not found for representative {representative.pk}")

        return dataset_ids

    def _get_org_generic_fk_datasets(self, representative):
        dataset_ids = set()

        if representative.content_object and hasattr(representative.content_object, "get_descendants"):
            try:
                org_ids = {representative.object_id}
                org_ids.update(representative.content_object.get_descendants().values_list("pk", flat=True))
                dataset_ids.update(Dataset.objects.filter(organization_id__in=org_ids).values_list("pk", flat=True))
            except Exception as e:
                logger.exception("Failed getting Representative attached to an Organization via GenericFK: %s", e)

        return dataset_ids

    def _get_org_direct_fk_datasets(self, representative):
        dataset_ids = set()

        if representative.organization_id:
            try:
                org_ids = {representative.organization_id}
                org_ids.update(representative.organization.get_descendants().values_list("pk", flat=True))
                dataset_ids.update(Dataset.objects.filter(organization_id__in=org_ids).values_list("pk", flat=True))
            except Exception as e:
                logger.exception("Failed getting Representative organization field set (direct FK): %s", e)

        return dataset_ids

    def _update_dataset_indexes(self, datasets):
        for dataset in datasets:
            self._update_single_dataset_object(dataset)

    def _update_single_dataset(self, dataset_id):
        try:
            dataset = Dataset.objects.get(pk=dataset_id)
            self._update_single_dataset_object(dataset)
        except Dataset.DoesNotExist:
            logger.warning(f"Dataset {dataset_id} not found for index update")

    def _update_single_dataset_object(self, dataset):
        using_backends = self.connection_router.for_write(instance=dataset)
        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(Dataset)
                index.update_object(dataset, using=using)
            except NotHandled:
                pass

    def _update_related_request_indexes(self, dataset, using):
        try:
            req_index = self.connections[using].get_unified_index().get_index(Request)
            reqs = RequestObject.objects.filter(
                content_type=ContentType.objects.get_for_model(dataset),
                object_id=dataset.pk,
            )
            for req in reqs:
                req_index.update_object(req.request, using=using)
        except NotHandled:
            pass

    def handle_save(self, sender, instance, **kwargs):
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(sender)

                if index.index_queryset().filter(pk=instance.pk):
                    index.update_object(instance, using=using)
                    if isinstance(instance, Dataset):
                        self._update_related_request_indexes(instance, using)
                else:
                    index.remove_object(instance, using=using)

            except NotHandled:
                pass
