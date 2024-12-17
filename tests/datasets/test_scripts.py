import json
from unittest.mock import patch, Mock

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django_webtest import DjangoTestApp
from lxml import etree as ET
from reversion.models import Version

from scripts.geoportal_import import main as geoportal_import
from vitrina import settings
from vitrina.classifiers.factories import FrequencyFactory, LicenceFactory, CategoryFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.messages.factories import SubscriptionFactory
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.resources.factories import FileFormat, DatasetDistributionFactory
from vitrina.tasks.models import Task
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_geoportal_import__title_and_description_create(app: DjangoTestApp):
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.geoportal_id == "1"
    dataset.set_current_language("lt")
    assert dataset.title == "Naujas duomenų rinkinys"
    assert dataset.description == "Naujo duomenų rinkinio aprašymas"
    dataset.set_current_language("en")
    assert dataset.title == "New dataset"
    assert dataset.description == "New dataset description"


@pytest.mark.django_db
def test_geoportal_import__title_and_description_update(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    dataset.set_current_language("lt")
    assert dataset.title == "Naujas duomenų rinkinys"
    assert dataset.description == "Naujo duomenų rinkinio aprašymas"
    dataset.set_current_language("en")
    assert dataset.title == "New dataset"
    assert dataset.description == "New dataset description"


@pytest.mark.django_db
def test_geoportal_import__title_and_description_create_without_translation(app: DjangoTestApp):
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Pavadinimas</gco:CharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Aprašymas</gco:CharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.geoportal_id == "1"
    dataset.set_current_language("lt")
    assert dataset.title == "Pavadinimas"
    assert dataset.description == "Aprašymas"
    dataset.set_current_language("en")
    assert dataset.title == "Title"
    assert dataset.description == "Description"


@pytest.mark.django_db
def test_geoportal_import__tags_create(app: DjangoTestApp):
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:descriptiveKeywords>
                    <gmd:keyword>
                        <gco:CharacterString>žymė1</gco:CharacterString>
                    </gmd:keyword>  
                    <gmd:keyword>
                        <gco:CharacterString>žymė1</gco:CharacterString>
                    </gmd:keyword> 
                    <gmd:keyword>
                        <gco:CharacterString>Žymė2</gco:CharacterString>
                    </gmd:keyword>  
                    <gmd:keyword>
                        <gco:CharacterString>žymė3 </gco:CharacterString>
                    </gmd:keyword>  
                </gmd:descriptiveKeywords> 
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.geoportal_id == "1"
    assert sorted(list(dataset.tags.values_list('name', flat=True))) == ['žymė1', 'žymė2', 'žymė3']


@pytest.mark.django_db
def test_geoportal_import__tags_upcate(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1", tags=('žymė1', 'test'))

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:descriptiveKeywords>
                    <gmd:keyword>
                        <gco:CharacterString>žymė1</gco:CharacterString>
                    </gmd:keyword>  
                    <gmd:keyword>
                        <gco:CharacterString>žymė1</gco:CharacterString>
                    </gmd:keyword> 
                    <gmd:keyword>
                        <gco:CharacterString>Žymė2</gco:CharacterString>
                    </gmd:keyword>  
                    <gmd:keyword>
                        <gco:CharacterString>žymė3 </gco:CharacterString>
                    </gmd:keyword>  
                </gmd:descriptiveKeywords> 
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert sorted(list(dataset.tags.values_list('name', flat=True))) == ['žymė1', 'žymė2', 'žymė3']


@pytest.mark.django_db
def test_geoportal_import__frequency_create_with_existing_value(app: DjangoTestApp):
    frequency = FrequencyFactory(title="Neapibrėžtu periodiškumu")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceMaintenance>
                    <gmd:MD_MaintenanceFrequencyCode>asNeeded</gmd:MD_MaintenanceFrequencyCode>
                </gmd:resourceMaintenance>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.frequency == frequency


@pytest.mark.django_db
def test_geoportal_import__frequency_create_with_not_existing_value(app: DjangoTestApp):
    UserFactory(is_superuser=True)
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceMaintenance>
                    <gmd:MD_MaintenanceFrequencyCode>asNeeded</gmd:MD_MaintenanceFrequencyCode>
                </gmd:resourceMaintenance>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.frequency is None

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerastas atnaujinimo periodiškumas: "Neapibrėžtu periodiškumu"' in task.description


@pytest.mark.django_db
def test_geoportal_import__frequency_create_with_not_mapped_value(app: DjangoTestApp):
    UserFactory(is_superuser=True)
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceMaintenance>
                    <gmd:MD_MaintenanceFrequencyCode>test</gmd:MD_MaintenanceFrequencyCode>
                </gmd:resourceMaintenance>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.frequency is None

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerastas atnaujinimo periodiškumas: "test"' in task.description


@pytest.mark.django_db
def test_geoportal_import__frequency_update(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1")
    frequency = FrequencyFactory(title="Neapibrėžtu periodiškumu")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceMaintenance>
                    <gmd:MD_MaintenanceFrequencyCode>asNeeded</gmd:MD_MaintenanceFrequencyCode>
                </gmd:resourceMaintenance>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert dataset.frequency == frequency


@pytest.mark.django_db
def test_geoportal_import__access_rights_and_licence_create_with_existing_value(app: DjangoTestApp):
    licence = LicenceFactory(title="Creative Commons Attribution 4.0")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceConstraints>
                    <gmd:accessConstraints>
                        <gmd:MD_RestrictionCode>copyright</gmd:MD_RestrictionCode>
                    </gmd:accessConstraints>
                </gmd:resourceConstraints>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.access_rights == Dataset.PUBLIC
    assert dataset.licence == licence


@pytest.mark.django_db
def test_geoportal_import__access_rights_and_licence_create_with_not_existing_value(app: DjangoTestApp):
    UserFactory(is_superuser=True)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceConstraints>
                    <gmd:accessConstraints>
                        <gmd:MD_RestrictionCode>copyright</gmd:MD_RestrictionCode>
                    </gmd:accessConstraints>
                </gmd:resourceConstraints>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.access_rights == Dataset.PUBLIC
    assert dataset.licence is None

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta licencija: "Creative Commons Attribution 4.0"' in task.description


@pytest.mark.django_db
def test_geoportal_import__access_rights_and_licence_create_with_not_mapped_value(app: DjangoTestApp):
    UserFactory(is_superuser=True)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceConstraints>
                    <gmd:accessConstraints>
                        <gmd:MD_RestrictionCode>test</gmd:MD_RestrictionCode>
                    </gmd:accessConstraints>
                </gmd:resourceConstraints>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.access_rights is None
    assert dataset.licence is None

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerastos prieigos teisės: "test"' in task.description
    assert 'Nerasta licencija: "test"' in task.description


@pytest.mark.django_db
def test_geoportal_import__access_rights_and_licence_update(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1", access_rights=Dataset.RESTRICTED)
    licence = LicenceFactory(title="Creative Commons Attribution 4.0")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:resourceConstraints>
                    <gmd:accessConstraints>
                        <gmd:MD_RestrictionCode>copyright</gmd:MD_RestrictionCode>
                    </gmd:accessConstraints>
                </gmd:resourceConstraints>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert dataset.access_rights == Dataset.PUBLIC
    assert dataset.licence == licence


@pytest.mark.django_db
def test_geoportal_import__existing_publisher(app: DjangoTestApp):
    organization = OrganizationFactory(
        title="Viešoji įstaiga Statybos sektoriaus vystymo agentūra",
        company_code="305997589"
    )
    coordinator = RepresentativeFactory(
        role=Representative.COORDINATOR,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.publisher == organization
    assert dataset.representatives.count() == 1
    assert dataset.representatives.first().user == coordinator.user


@pytest.mark.django_db
def test_geoportal_import__not_existing_publisher(app: DjangoTestApp):
    UserFactory(is_superuser=True)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.publisher is None

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta tiekėjo organizacija: "Viešoji įstaiga Statybos sektoriaus vystymo agentūra"' in task.description


@pytest.mark.django_db
def test_geoportal_import__existing_creator(app: DjangoTestApp):
    organization = OrganizationFactory(title="VšĮ Statybos sektoriaus vystymo agentūra")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Statybos sektoriaus vystymo agentūra, VšĮ</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.organization == organization


@pytest.mark.django_db
def test_geoportal_import__existing_creator_municipality(app: DjangoTestApp):
    organization = OrganizationFactory(title="Jonavos rajono savivaldybės administracija")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Savivaldybė - Jonavos rajono</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.organization == organization


@pytest.mark.django_db
def test_geoportal_import__existing_creator_alternative_title(app: DjangoTestApp):
    organization = OrganizationFactory(
        title="Jonavos rajono savivaldybės administracija",
        alternative_titles="Jonavos rajonas"
    )

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Jonavos rajonas</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.organization == organization


@pytest.mark.django_db
def test_geoportal_import__not_existing_creator(app: DjangoTestApp):
    UserFactory(is_superuser=True)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Jonavos rajonas</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.organization is None
    assert dataset.creator_text == "Jonavos rajonas"

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta organizacija: "Jonavos rajonas"' in task.description


@pytest.mark.django_db
def test_geoportal_import__distribution_create_with_url(app: DjangoTestApp):
    frm = FileFormat(extension="URL")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
            <gmd:distributionInfo>
                <gmd:transferOptions>
                    <gmd:CI_OnlineResource>
                        <gmd:URL>https://example.com</gmd:URL>
                    </gmd:CI_OnlineResource>
                </gmd:transferOptions>
            </gmd:distributionInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.datasetdistribution_set.count() == 1
    assert dataset.datasetdistribution_set.first().download_url == "https://example.com"
    assert dataset.datasetdistribution_set.first().format == frm
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.OPENED


@pytest.mark.django_db
def test_geoportal_import__distribution_create_without_url(app: DjangoTestApp):
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
            <gmd:distributionInfo>
                <gmd:transferOptions>
                </gmd:transferOptions>
            </gmd:distributionInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


@pytest.mark.django_db
def test_geoportal_import__distribution_update_with_url(app: DjangoTestApp):
    frm = FileFormat(extension="URL")
    dataset = DatasetFactory(geoportal_id="1")
    distribution = DatasetDistributionFactory(
        dataset=dataset,
        format=frm,
        download_url="https://test.com"
    )

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
            <gmd:distributionInfo>
                <gmd:transferOptions>
                    <gmd:CI_OnlineResource>
                        <gmd:URL>https://example.com</gmd:URL>
                    </gmd:CI_OnlineResource>
                </gmd:transferOptions>
            </gmd:distributionInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    distribution.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert dataset.datasetdistribution_set.count() == 1
    assert distribution.download_url == "https://example.com"
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.OPENED


@pytest.mark.django_db
def test_geoportal_import__categories_create_existing_values(app: DjangoTestApp):
    CategoryFactory(title="Flora ir fauna")
    CategoryFactory(title="Energetika")
    CategoryFactory(title="Transportas ir ryšiai")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>utilitiesCommunication</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>biota</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.category.count() == 3
    assert sorted(list(dataset.category.values_list('title', flat=True))) == [
        'Energetika',
        'Flora ir fauna',
        'Transportas ir ryšiai'
    ]


@pytest.mark.django_db
def test_geoportal_import__categories_create_not_existing_values(app: DjangoTestApp):
    UserFactory(is_superuser=True)
    CategoryFactory(title="Energetika")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>utilitiesCommunication</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>biota</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.category.count() == 1
    assert sorted(list(dataset.category.values_list('title', flat=True))) == ['Energetika']

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta kategorija: "Flora ir fauna"' in task.description
    assert 'Nerasta kategorija: "Transportas ir ryšiai"' in task.description


@pytest.mark.django_db
def test_geoportal_import__categories_create_not_mapped_values(app: DjangoTestApp):
    UserFactory(is_superuser=True)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>test</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert dataset.category.count() == 0

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta kategorija: "test"' in task.description


@pytest.mark.django_db
def test_geoportal_import__categories_update(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1")
    category = CategoryFactory(title="Flora ir fauna")
    dataset.category.add(category)

    CategoryFactory(title="Energetika")
    CategoryFactory(title="Transportas ir ryšiai")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>utilitiesCommunication</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>biota</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert dataset.category.count() == 3
    assert sorted(list(dataset.category.values_list('title', flat=True))) == [
        'Energetika',
        'Flora ir fauna',
        'Transportas ir ryšiai'
    ]


@pytest.mark.django_db
def test_geoportal_import__recurring_error_message(app: DjangoTestApp):
    user = UserFactory(is_superuser=True)
    dataset = DatasetFactory(geoportal_id="1")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>test</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        # import two times, to repeat the error
        geoportal_import()
        geoportal_import()

    assert Dataset.objects.count() == 1
    assert dataset.category.count() == 0

    assert Task.objects.count() == 1
    task = Task.objects.first()
    assert 'Nerasta kategorija: "test"' in task.description

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.django_db
def test_geoportal_import__different_error_message(app: DjangoTestApp):
    user = UserFactory(is_superuser=True)
    dataset = DatasetFactory(geoportal_id="1")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>test</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:topicCategory>
                    <gmd:MD_TopicCategoryCode>test2</gmd:MD_TopicCategoryCode>
                </gmd:topicCategory>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    assert dataset.category.count() == 0

    assert Task.objects.count() == 2
    task1 = Task.objects.order_by('pk')[0]
    assert 'Nerasta kategorija: "test"' in task1.description
    task2 = Task.objects.order_by('pk')[1]
    assert 'Nerasta kategorija: "test2"' in task2.description

    assert len(mail.outbox) == 2
    assert mail.outbox[0].to == [user.email]
    assert mail.outbox[1].to == [user.email]


@pytest.mark.django_db
def test_geoportal_import__subscription_create(app: DjangoTestApp):
    organization = OrganizationFactory(title="Statybos sektoriaus vystymo agentūra, VšĮ")
    coordinator = RepresentativeFactory(
        role=Representative.COORDINATOR,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    SubscriptionFactory(
        user=coordinator.user,
        sub_type=Subscription.ORGANIZATION,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        dataset_update_sub=True,
    )

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Statybos sektoriaus vystymo agentūra, VšĮ</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    assert Task.objects.filter(user=coordinator.user).count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [coordinator.user.email]


@pytest.mark.django_db
def test_geoportal_import__subscription_update(app: DjangoTestApp):
    organization = OrganizationFactory(title="Statybos sektoriaus vystymo agentūra, VšĮ")
    coordinator = RepresentativeFactory(
        role=Representative.COORDINATOR,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    SubscriptionFactory(
        user=coordinator.user,
        sub_type=Subscription.ORGANIZATION,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        dataset_update_sub=True,
    )
    dataset = DatasetFactory(geoportal_id="1", organization=organization)

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Statybos sektoriaus vystymo agentūra, VšĮ</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    assert Task.objects.filter(user=coordinator.user).count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [coordinator.user.email]


@pytest.mark.django_db
def test_geoportal_import__subscription_update_no_changes(app: DjangoTestApp):
    organization = OrganizationFactory(title="Statybos sektoriaus vystymo agentūra, VšĮ")
    coordinator = RepresentativeFactory(
        role=Representative.COORDINATOR,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    SubscriptionFactory(
        user=coordinator.user,
        sub_type=Subscription.ORGANIZATION,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        dataset_update_sub=True,
    )
    dataset = DatasetFactory(geoportal_id="1", organization=organization)
    dataset.set_current_language("lt")
    dataset.title = "Naujas duomenų rinkinys"
    dataset.description = "Naujo duomenų rinkinio aprašymas"
    dataset.set_current_language("en")
    dataset.title = "New dataset"
    dataset.description = "New dataset description"
    dataset.save()

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
                <gmd:pointOfContact>
                    <gmd:organisationName>
                        <gco:CharacterString>Statybos sektoriaus vystymo agentūra, VšĮ</gco:CharacterString>
                    </gmd:organisationName>
                </gmd:pointOfContact>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    assert Dataset.objects.count() == 1
    assert Task.objects.filter(user=coordinator.user).count() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_geoportal_import__history_create(app: DjangoTestApp):
    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    sys_user = User.objects.get(email=settings.SYSTEM_USER_EMAIL)
    assert Dataset.objects.count() == 1
    dataset = Dataset.objects.first()
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.CREATED
    assert Version.objects.get_for_object(dataset).first().revision.user == sys_user


@pytest.mark.django_db
def test_geoportal_import__history_update(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1")

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    sys_user = User.objects.get(email=settings.SYSTEM_USER_EMAIL)
    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert Version.objects.get_for_object(dataset).count() == 1
    assert Version.objects.get_for_object(dataset).first().revision.comment == Dataset.EDITED
    assert Version.objects.get_for_object(dataset).first().revision.user == sys_user


@pytest.mark.django_db
def test_geoportal_import__history_update_no_changes(app: DjangoTestApp):
    dataset = DatasetFactory(geoportal_id="1")
    dataset.set_current_language("lt")
    dataset.title = "Naujas duomenų rinkinys"
    dataset.description = "Naujo duomenų rinkinio aprašymas"
    dataset.set_current_language("en")
    dataset.title = "New dataset"
    dataset.description = "New dataset description"
    dataset.save()

    with patch('scripts.geoportal_import.requests.get') as get_all_mock, \
            patch('scripts.geoportal_import.ET.parse') as get_one_mock:
        data = {
            'totalResults': 1,
            'startIndex': 1,
            'records': [{
                'id': "1"
            }],
        }
        get_all_mock.return_value = Mock(content=json.dumps(data))
        root = ET.fromstring('''
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:identificationInfo>
                <gmd:title>
                    <gco:CharacterString>Naujas duomenų rinkinys</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset</gmd:LocalisedCharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Naujo duomenų rinkinio aprašymas</gco:CharacterString>
                    <gmd:LocalisedCharacterString locale="#en">New dataset description</gmd:LocalisedCharacterString>
                </gmd:abstract>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>
        ''')
        tree = ET.ElementTree(root)
        get_one_mock.return_value = tree
        geoportal_import()

    dataset.refresh_from_db()
    assert Dataset.objects.count() == 1
    assert Version.objects.get_for_object(dataset).count() == 0
