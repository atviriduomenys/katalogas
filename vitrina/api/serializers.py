from django.utils import timezone
from filer.models import Folder, File
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import gettext_lazy as _
from reversion import set_comment, set_user

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Licence, Category, Frequency
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.helpers import get_current_domain
from vitrina.resources.models import DatasetDistribution


class LicenceSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        source='identifier',
    )
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Licence
        fields = ['description', 'id', 'title']


class CatalogSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        source='identifier',
    )
    licence = LicenceSerializer(read_only=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Catalog
        fields = ['description', 'id', 'licence', 'title']


class CategorySerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(required=False, allow_blank=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Category
        fields = ['description', 'id', 'title']


class DatasetSerializer(serializers.ModelSerializer):
    created = serializers.DateTimeField(required=False, label="")
    id = serializers.CharField(required=False, allow_blank=True, label="")
    origin = serializers.CharField(required=False, allow_blank=True, label="")
    internalId = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        source='internal_id',
        validators=[
            UniqueValidator(Dataset.objects.all()),
        ],
    )
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:title - Title (required)"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:description - Description (required)"
    )
    modified = serializers.DateTimeField(
        required=False,
        label="",
        help_text="dct:modified - Update / modification date"
    )
    temporalCoverage = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:temporal - Temporal coverage of dataset data",
        source='temporal_coverage'
    )
    language = serializers.ListField(
        required=False,
        child=serializers.CharField(),
        source="language_array",
        help_text="dct:language - Language"
    )
    publisher = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:publisher - Publisher"
    )
    spatial = serializers.CharField(
        required=False,
        source='spatial_coverage',
        allow_blank=True,
        label="",
        help_text="dct:spatial - Spatial information"
    )
    licence = serializers.CharField(
        source='licence.identifier',
        required=False,
        allow_blank=True,
        label="",
        help_text="Licence"
    )
    periodicity = serializers.CharField(
        source='frequency.title',
        required=False,
        allow_blank=True,
        label="",
        help_text="Periodicity"
    )
    contactPoint = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dcat:contactPoint - Contact information",
    )
    keyword = serializers.ListField(
        required=False,
        child=serializers.CharField(),
        source='tag_name_array',
        help_text="dcat:keyword - Keywords"
    )
    landingPage = serializers.SerializerMethodField(
        required=False,
        label="",
        help_text="dcat:landingPage - Landing page of dataset",
    )
    theme = serializers.ListField(
        child=serializers.CharField(),
        source='category_titles',
        required=False,
        label="",
        help_text="dcat:theme - Category of the dataset",
    )

    class Meta:
        model = Dataset
        fields = [
            'created',
            'id',
            'internalId',
            'origin',
            'title',
            'description',
            'modified',
            'temporalCoverage',
            'language',
            'publisher',
            'spatial',
            'licence',
            'periodicity',
            'contactPoint',
            'keyword',
            'landingPage',
            'theme',
        ]

    def get_landingPage(self, obj):
        landing_page = ""
        request = self.context.get('request')
        if request:
            domain = get_current_domain(request)
            landing_page = f"{domain}{obj.get_absolute_url()}"
        return landing_page


class PostDatasetSerializer(DatasetSerializer):
    title = serializers.CharField(
        allow_blank=True,
        label="",
        help_text="dct:title - Title (required)"
    )
    description = serializers.CharField(
        allow_blank=True,
        label="",
        help_text="dct:description - Description (required)"
    )
    published = serializers.BooleanField(
        required=False,
        label="",
        source='is_public'
    )
    landingPage = serializers.CharField(
        required=False,
        label="",
        allow_blank=True,
        help_text="dcat:landingPage - Landing page of dataset",
    )

    class Meta(DatasetSerializer.Meta):
        fields = [
            'internalId',
            'published',
            'title',
            'description',
            'temporalCoverage',
            'language',
            'publisher',
            'spatial',
            'licence',
            'periodicity',
            'contactPoint',
            'keyword',
            'landingPage',
            'theme',
        ]

    def create(self, validated_data):
        languages = validated_data.pop('language_array', [])
        licence = validated_data.pop('licence', None)
        periodicity = validated_data.pop('frequency', None)
        keywords = validated_data.pop('tag_name_array', [])
        theme = validated_data.pop('category_titles', [])

        # these fields are not saved in the old code
        validated_data.pop('publisher', None)
        validated_data.pop('contactPoint', None)
        validated_data.pop('landingPage', None)

        instance = super().create(validated_data)
        instance.origin = Dataset.API_ORIGIN
        instance.organization = self.context.get('organization')
        if languages:
            instance.language = " ".join(languages)
        if licence and Licence.objects.filter(identifier=licence['identifier']).exists():
            instance.licence = Licence.objects.filter(identifier=licence['identifier']).first()
        if periodicity and Frequency.objects.filter(title=periodicity['title']).exists():
            instance.frequency = Frequency.objects.filter(title=periodicity['title']).first()
        if theme and Category.objects.filter(title__in=theme).exists():
            for category in Category.objects.filter(title__in=theme):
                instance.category.add(category)
        for tag in keywords:
            instance.tags.add(tag)
        instance.save()
        set_comment(Dataset.CREATED)
        set_user(self.context.get('user'))
        return instance


class PatchDatasetSerializer(PostDatasetSerializer):
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:title - Title"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        help_text="dct:description - Description"
    )

    def update(self, instance, validated_data):
        languages = validated_data.pop('language_array', [])
        licence = validated_data.pop('licence', None)
        periodicity = validated_data.pop('frequency', None)
        keywords = validated_data.pop('tag_name_array', [])
        theme = validated_data.pop('category_titles', [])

        # these fields are not saved in the old code
        validated_data.pop('publisher', None)
        validated_data.pop('contactPoint', None)
        validated_data.pop('landingPage', None)

        instance = super().update(instance, validated_data)
        if languages:
            instance.language = " ".join(languages)
        if licence and Licence.objects.filter(identifier=licence['identifier']).exists():
            instance.licence = Licence.objects.filter(identifier=licence['identifier']).first()
        if periodicity and Frequency.objects.filter(title=periodicity['title']).exists():
            instance.frequency = Frequency.objects.filter(title=periodicity['title']).first()
        if theme and Category.objects.filter(title__in=theme).exists():
            instance.category.clear()
            for category in Category.objects.filter(title__in=theme):
                instance.category.add(category)
        if keywords:
            instance.tags.all().delete()
            for tag in keywords:
                instance.tags.add(tag)
        instance.save()
        set_comment(Dataset.EDITED)
        set_user(self.context.get('user'))
        return instance


class DatasetDistributionSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    file = serializers.CharField(required=False, label="", allow_blank=True, source="filename_without_path")
    id = serializers.IntegerField(required=False, label="")
    issued = serializers.CharField(required=False, allow_blank=True, label="")
    municipality = serializers.CharField(required=False, allow_blank=True, label="")
    periodEnd = serializers.DateField(required=False, label="", source='period_end')
    periodStart = serializers.DateField(required=False, label="", source='period_start')
    region = serializers.CharField(required=False, allow_blank=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")
    type = serializers.CharField(required=False, allow_blank=True, label="")
    url = serializers.SerializerMethodField(required=False, label="")
    version = serializers.IntegerField(required=False, label="", source="distribution_version")
    geo_location = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = DatasetDistribution
        fields = [
            'description',
            'file',
            'id',
            'issued',
            'municipality',
            'periodEnd',
            'periodStart',
            'region',
            'geo_location',
            'title',
            'type',
            'url',
            'version',
        ]

    def get_url(self, obj):
        if obj.type == "URL":
            return obj.download_url
        else:
            dataset_url = ""
            request = self.context.get('request')
            if request:
                domain = get_current_domain(request)
                dataset_url = f"{domain}{obj.dataset.get_absolute_url()}"
            return dataset_url


class PostDatasetDistributionSerializer(DatasetDistributionSerializer):
    title = serializers.CharField(required=True, allow_blank=True, label="")
    url = serializers.CharField(required=False, allow_blank=True, label="")
    file = serializers.FileField(required=False, label="", allow_empty_file=False)
    overwrite = serializers.BooleanField(required=False, label="")

    class Meta(DatasetDistributionSerializer.Meta):
        fields = [
            'description',
            'file',
            'issued',
            'municipality',
            'overwrite',
            'periodEnd',
            'periodStart',
            'region',
            'title',
            'url',
            'version',
        ]

    def validate(self, data):
        file = data.get('file')
        url = data.get('url')
        if not file and not url:
            raise serializers.ValidationError({
                'file': _("file' arba 'url' laukui turi būti priskirta reikšmė"),
                'url': _("file' arba 'url' laukui turi būti priskirta reikšmė")
            })
        if file and url:
            raise serializers.ValidationError({
                'file': _("Reikšmė turi būti priskirta 'file' arba 'url' laukui, bet ne abiems"),
                'url': _("Reikšmė turi būti priskirta 'file' arba 'url' laukui, bet ne abiems"),
            })
        return data

    def overwrite_file(self, validated_data):
        return validated_data.pop('overwrite', False)

    def create(self, validated_data):
        issued = validated_data.get('issued', None)
        file = validated_data.pop('file', None)
        region = validated_data.pop('region', None)
        municipality = validated_data.pop('municipality', None)
        url = validated_data.pop('url', None)
        overwrite = self.overwrite_file(validated_data)

        dataset = self.context.get('dataset')
        validated_data.update({
            'dataset': dataset
        })

        # if overwrite True, try to look for existing distribution
        upload_to = DatasetDistribution.UPLOAD_TO
        upload_folder = None
        folders = upload_to.split('/')
        for level, folder_name in enumerate(folders):
            upload_folder, created = Folder.objects.get_or_create(
                level=level,
                name=folder_name,
                parent=upload_folder
            )

        if overwrite and file and dataset.datasetdistribution_set.filter(
            file__folder=upload_folder,
            file__original_filename=file.name,
        ):
            instance = dataset.datasetdistribution_set.filter(
                file__folder=upload_folder,
                file__original_filename=file.name,
            ).first()
            instance = super().update(instance, validated_data)
        else:
            # did not find, initialize a new one
            instance = super().create(validated_data)

        if region and not municipality:
            instance.geo_location = region
        elif not region and municipality:
            instance.geo_location = municipality
        elif region and municipality:
            instance.geo_location = f"{region} {municipality}"
        if file:
            instance.file = File.objects.create(
                file=file,
                original_filename=file.name,
                folder=upload_folder
            )
            instance.type = "FILE"
        elif url:
            instance.type = "URL"
            instance.download_url = url
        if not issued:
            instance.issued = timezone.now()
        instance.save()
        return instance


class PutDatasetDistributionSerializer(PostDatasetDistributionSerializer):

    class Meta(PostDatasetDistributionSerializer.Meta):
        fields = [
            'description',
            'file',
            'issued',
            'municipality',
            'periodEnd',
            'periodStart',
            'region',
            'title',
            'url',
            'version',
        ]

    def overwrite_file(self, validated_data):
        return True


class PatchDatasetDistributionSerializer(DatasetDistributionSerializer):
    title = serializers.CharField(required=False, allow_blank=True, label="")
    url = serializers.CharField(required=False, allow_blank=True, label="")
    file = serializers.FileField(required=False, label="", allow_empty_file=False)

    class Meta(DatasetSerializer.Meta):
        fields = [
            'description',
            'file',
            'issued',
            'municipality',
            'periodEnd',
            'periodStart',
            'region',
            'title',
            'url'
        ]

    def validate(self, data):
        file = data.get('file')
        url = data.get('url')
        if file and url:
            raise serializers.ValidationError({
                'file': _("Reikšmė turi būti priskirta 'file' arba 'url' laukui, bet ne abiems"),
                'url': _("Reikšmė turi būti priskirta 'file' arba 'url' laukui, bet ne abiems"),
            })
        return data

    def update(self, instance, validated_data):
        file = validated_data.pop('file', None)
        region = validated_data.pop('region', None)
        municipality = validated_data.pop('municipality', None)
        url = validated_data.pop('url', None)

        instance = super().update(instance, validated_data)
        if region and not municipality:
            instance.geo_location = region
        elif not region and municipality:
            instance.geo_location = municipality
        elif region and municipality:
            instance.geo_location = f"{region} {municipality}"
        if file:
            upload_to = DatasetDistribution.UPLOAD_TO
            upload_folder = None
            folders = upload_to.split('/')
            for level, folder_name in enumerate(folders):
                upload_folder, created = Folder.objects.get_or_create(
                    level=level,
                    name=folder_name,
                    parent=upload_folder
                )
            instance.file = File.objects.create(
                file=file,
                original_filename=file.name,
                folder=upload_folder
            )
            instance.type = "FILE"
            instance.download_url = None
        elif url:
            instance.type = "URL"
            instance.download_url = url
            instance.file = None
        instance.save()
        return instance


class DatasetStructureSerializer(serializers.ModelSerializer):
    created = serializers.DateTimeField(required=False, label="")
    id = serializers.IntegerField(required=False, label="")
    size = serializers.IntegerField(required=False, label="file_size")
    title = serializers.CharField(required=False, allow_blank=True, label="")
    filename = serializers.CharField(
        required=False,
        allow_blank=True,
        label="",
        source="filename_without_path"
    )

    class Meta:
        model = DatasetStructure
        fields = [
            'created',
            'filename',
            'id',
            'size',
            'title',
        ]


class PostDatasetStructureSerializer(serializers.ModelSerializer):
    title = serializers.CharField(allow_blank=True, label="")
    file = serializers.FileField(label="", allow_empty_file=False)

    class Meta:
        model = DatasetStructure
        fields = [
            'file',
            'title'
        ]

    def create(self, validated_data):
        file = validated_data.pop('file', None)
        dataset = self.context.get('dataset')
        validated_data.update({
            'dataset': dataset
        })
        instance = super().create(validated_data)
        if file:
            upload_to = DatasetStructure.UPLOAD_TO
            upload_folder = None
            folders = upload_to.split('/')
            for level, folder_name in enumerate(folders):
                upload_folder, created = Folder.objects.get_or_create(
                    level=level,
                    name=folder_name,
                    parent=upload_folder
                )
            instance.file = File.objects.create(
                file=file,
                original_filename=file.name,
                folder=upload_folder
            )
            instance.save()
            dataset.current_structure = instance
            dataset.save()
        return instance
