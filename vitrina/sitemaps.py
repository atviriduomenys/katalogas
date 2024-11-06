from django.contrib.sitemaps import Sitemap
from django.contrib import sitemaps

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.structure.models import Model


class RootSitemap(Sitemap):
    changefreq = "monthly"
    priority = 1.0

    def items(self):
        return ['/']

    def location(self, item):
        return item


# Only public datasets
class DatasetSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.8

    def items(self):
        return Dataset.public.all()

    def lastmod(self, obj):
        return obj.modified


class ModelSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    # Only public models
    def items(self):
        return [model for model in Model.objects.all().order_by('id') if model.is_opened()]


class OrganizationSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.6

    # Only public organizations
    def items(self):
        return Organization.public.all()

    def lastmod(self, obj):
        return obj.modified


class MoreViewSitemap(sitemaps.Sitemap):
    priority = 0.3
    changefreq = "yearly"

    def items(self):
        return ["/more/about/", "/more/regulation/regulation_legal/", "/more/regulation/regulation_strat/",]

    def location(self, item):
        return item