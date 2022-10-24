import factory
import faker
from factory.django import DjangoModelFactory

from vitrina import settings
from vitrina.classifiers.factories import CategoryFactory, LicenceFactory, FrequencyFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetStructure


MANIFEST = '''\
id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description
,datasets/gov/ivpk/adk,,,,,,,,,,,,Opend Data Portal,
,,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,
,,,,,,,dct,,,,,http://purl.org/dc/terms/,,
,,,,,,,spinta,,,,,https://github.com/atviriduomenys/spinta/issues/,,
,,,,,,,,,,,,,,
,,,,Dataset,,,id,,,5,,dcat:Dataset,Dataset,
,,,,,id,integer,,,,5,open,dct:identifier,,
,,,,,title,string,,,,2,open,dct:title,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
,,,,,description,string,,,,2,open,dct:description,,
,,,,,,comment,type,,"update(property: ""description@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
,,,,,licence,ref,Licence,,,2,open,dct:license,,
,,,,,,,,,,,,,,
,,,,Licence,,,id,,,,,,Licence,
,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,
,,,,,title,string,,,,2,open,dct:title,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
'''


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('organization', 'is_public')

    organization = factory.SubFactory(OrganizationFactory)
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA
    category = factory.SubFactory(CategoryFactory)
    licence = factory.SubFactory(LicenceFactory)
    frequency = factory.SubFactory(FrequencyFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        dataset = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            dataset.set_current_language(lang[0])
            dataset.title = fake.word
            dataset.description = fake.catch_phrase
        dataset.save()
        return dataset

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    version = 1
    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='manifest.csv', data=MANIFEST)
