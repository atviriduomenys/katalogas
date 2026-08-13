import logging
from copy import copy

from django.db import transaction

logger = logging.getLogger(__name__)


def on_commit(func):
    transaction.on_commit(func)


_STALE_CACHES = ("_cached_tags",)


def _with_fresh_relations(instance):
    fresh = copy(instance)
    for name in _STALE_CACHES:
        fresh.__dict__.pop(name, None)
    fresh._prefetched_objects_cache = {}
    return fresh


def _reindex_dataset(instance):
    from vitrina.requests.models import RequestObject
    from vitrina.search.indexing import index_dataset, index_request

    index_dataset(_with_fresh_relations(instance))

    for request_object in RequestObject.objects.filter(
        content_type__app_label="vitrina_datasets",
        content_type__model="dataset",
        object_id=instance.pk,
    ).select_related("request"):
        index_request(request_object.request)


def _reindex_request(instance):
    from vitrina.search.indexing import index_request

    index_request(_with_fresh_relations(instance))


def _guarded(work, label, instance):
    try:
        work(instance)
    except Exception:
        logger.warning("Failed to index %s pk=%s", label, instance.pk, exc_info=True)


def index_dataset_on_save(sender, instance, **kwargs):
    on_commit(lambda: _guarded(_reindex_dataset, "dataset", instance))


def index_request_on_save(sender, instance, **kwargs):
    on_commit(lambda: _guarded(_reindex_request, "request", instance))
