from datetime import date, datetime

import factory
from factory.django import DjangoModelFactory

from vitrina.statistics.models import DatasetStats, ModelDownloadStats


class DatasetStatsFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStats

    created = factory.LazyFunction(date.today)
    dataset_id = factory.Sequence(lambda n: n + 1)
    object_count = 0
    field_count = 0
    model_count = 0
    distribution_count = 0
    request_count = 0
    project_count = 0
    maturity_level = 0


class ModelDownloadStatsFactory(DjangoModelFactory):
    class Meta:
        model = ModelDownloadStats

    created = factory.LazyFunction(datetime.now)
    source = "get.data.gov.lt"
    model = factory.Sequence(lambda n: f"datasets/model{n}")
    model_format = "json"
    model_requests = 0
    model_objects = 0
