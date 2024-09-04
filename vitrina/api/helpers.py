from typing import Optional

from vitrina.datasets.models import Dataset
from vitrina.resources.models import DatasetDistribution as Distribution
from vitrina.resources.models import Format
from vitrina.resources.models import FormatName
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency
from vitrina.classifiers.models import Licence


def get_datasets_for_rdf(qs):
    datasets = (
        qs.
        select_related('organization').
        select_related('licence').
        prefetch_related('category').
        prefetch_related('translations').
        prefetch_related('datasetdistribution_set').
        prefetch_related('datasetdistribution_set__format').
        order_by('published')
    )
    for dataset in datasets:
        distributions = [
            _get_distribution(dataset, dist)
            for dist in dataset.datasetdistribution_set.all()
        ]

        yield {
            'uri': dataset.get_absolute_url(),
            'translations': (
                {
                    'lang': t.language_code,
                    'title': t.title,
                    'description': t.description,
                }
                for t in dataset.translations.order_by('language_code')
            ),
            'categories': [
                _get_category(c)
                for c in dataset.category.all()
            ],
            'hvd_categories': [
                _get_category(c)
                for c in dataset.category.filter(
                    groups__translations__title="Didelės vertės rinkiniai"
                )
            ],
            'keywords': [
                k.name
                for k in dataset.tags.all()
            ],
            'published': dataset.published,
            'modified': dataset.modified,
            'organization': dataset.organization,
            'frequency': _get_frequency(dataset.frequency),
            'licence': _get_licence(dataset.licence),
            'distributions': distributions,
        }


def _get_distribution(dataset: Dataset, dist: Distribution):
    dist_type = None
    if dist.format:
        if dist.format.extension in (FormatName.API, FormatName.UAPI):
            dist_type = 'WEB_SERVICE'
        else:
            dist_type = 'DOWNLOADABLE_FILE'
        dist_type = (
            'http://publications.europa.eu/' +
            'resource/authority/distribution-type/' +
            dist_type
        )

    return {
        'uri': dist.get_absolute_url(),
        'type': dist_type,
        'translations': [
            {
                'lang': 'lt',
                'title': dist.title,
                'description': dist.description,
            },
        ],
        'access_url': dataset.get_absolute_url(),
        'download_url': dist.get_download_url(),
        'licence': _get_licence(dataset.licence),
        'format': _get_format(dist.format),
        'media_type': _get_media_type(dist.format),
        'created': dist.created,
        'modified': dist.modified,
    }


def _get_category(category: Category):
    return {
        'uri': category.uri,
        'translations': [
            {
                'lang': 'lt',
                'title': category.title,
            },
        ],
    }


def _get_frequency(frequency: Optional[Frequency]):
    if not frequency:
        return

    return {
        'uri': frequency.uri,
        'translations': [
            {
                'lang': 'lt',
                'title': frequency.title,
            },
            {
                'lang': 'en',
                'title': frequency.title_en,
            },
        ],
    }


def _get_licence(licence: Optional[Licence]):
    if licence and licence.url:
        return {
            'uri': licence.url
        }


def _get_format(format: Optional[Format]):
    if format and format.uri:
        return {
            'uri': format.uri,
        }


def _get_media_type(format: Optional[Format]):
    if format and format.media_type_uri:
        return {
            'uri': format.media_type_uri,
        }
