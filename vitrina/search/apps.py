from django.apps import AppConfig
from django.db.models.signals import post_save


class SearchConfig(AppConfig):
    name = "vitrina.search"
    label = "vitrina_search"
    verbose_name = "Search"

    def ready(self):
        from vitrina.datasets.models import Dataset
        from vitrina.requests.models import Request
        from vitrina.search.signals import index_dataset_on_save, index_request_on_save

        post_save.connect(index_dataset_on_save, sender=Dataset, dispatch_uid="vitrina_search_dataset")
        post_save.connect(index_request_on_save, sender=Request, dispatch_uid="vitrina_search_request")
