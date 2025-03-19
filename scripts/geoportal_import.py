import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import requests
import reversion
import lxml.etree as ET
from typer import run
from tqdm import tqdm
from django.db.models import Q
from django.utils import timezone
from django.contrib.sites.models import Site
from django.urls import reverse
from vitrina import settings
from vitrina.datasets.models import Dataset, ResourceSubclass, Relation, DatasetRelation
from vitrina.orgs.models import Organization, Representative
from vitrina.users.models import User
from vitrina.tasks.models import Task
from vitrina.helpers import email
from django.contrib.contenttypes.models import ContentType
from vitrina.classifiers.models import GeoportalCategory, GeoportalFrequency, GeoportalLicence, \
    GeoportalAccessRights
from vitrina.resources.models import DatasetDistribution, GeoportalFormatValue
from vitrina.comments.models import Comment
from vitrina.messages.models import Subscription


def _get_elem(tag, element, find_all=False):
    if element is not None:
        if find_all:
            return element.findall(tag)
        else:
            return element.find(tag)
    return [] if find_all else None


def _create_or_get_service_resource_subclass():
    resource_subclass_obj, created = ResourceSubclass.objects.get_or_create(name='service')
    if created:
        resource_subclass_obj.title = 'Duomenų publikavimo paslauga'
        resource_subclass_obj.save()
    return resource_subclass_obj


def _get_categories(title):
    categories = []
    if mapping := GeoportalCategory.objects.filter(title=title).first():
        categories = mapping.categories.all()
    else:
        GeoportalCategory.objects.create(title=title)
    return categories


def _get_frequency(title):
    frequency = None
    if mapping := GeoportalFrequency.objects.filter(title=title).first():
        frequency = mapping.frequency
    else:
        GeoportalFrequency.objects.create(title=title)
    return frequency


def _get_licence(title):
    licence = None
    if mapping := GeoportalLicence.objects.filter(title=title).first():
        licence = mapping.licence
    else:
        GeoportalLicence.objects.create(title=title)
    return licence


def _get_access_rights(title):
    access_rights = None
    if mapping := GeoportalAccessRights.objects.filter(title=title).first():
        access_rights = mapping.access_rights
    else:
        GeoportalAccessRights.objects.create(title=title)
    return access_rights


def main():
    """
    Import datasets from Geoportal
    """

    start_index = 1
    body = '''
    <csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" 
        service="CSW" version="2.0.2" resultType="results" startPosition="{}" maxRecords="15" 
        outputFormat="application/xml" outputSchema="http://www.opengis.net/cat/csw/2.0.2" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 
        http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">
        <csw:Query typeNames="csw:Record">
            <csw:ElementSetName>full</csw:ElementSetName>
        </csw:Query>
    </csw:GetRecords>
    '''

    url = "https://www.geoportal.lt/metadata-catalog/csw?Request=GetRecords&Service=CSW&Version=2.0.2"
    try:
        response = requests.get(url, data=body.format(start_index))
    except requests.RequestException as e:
        print(f"Got error while receiving data: {str(e)}")
        return

    xml = ET.XML(response.content)

    namespaces = xml.nsmap
    csw = namespaces.get('csw')
    dct = namespaces.get('dct')
    dc = namespaces.get('dc')

    total_results = 0
    results = _get_elem("{%s}SearchResults" % csw, xml)
    if results is not None and results.get('numberOfRecordsMatched'):
        total_results = int(results.get('numberOfRecordsMatched'))

    records = _get_elem(".//{%s}Record" % csw, results, find_all=True)

    pbar = tqdm("Importing Geoportal datasets", total=total_results)
    sys_user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)

    while records:
        for record in records:
            dataset_id = ""
            metadata_url = ""
            data_url = ""

            dataset_ids = _get_elem("{%s}identifier" % dc, record, find_all=True)
            for dat_id in dataset_ids:
                scheme = dat_id.get('scheme')
                if scheme.endswith("DocID"):
                    dataset_id = dat_id.text

            references = _get_elem("{%s}references" % dct, record, find_all=True)
            for ref in references:
                scheme = ref.get('scheme')
                if scheme.endswith("Document"):
                    metadata_url = ref.text
                elif scheme.endswith("Server"):
                    data_url = ref.text

            if metadata_url and dataset_id:
                try:
                    res = requests.get(metadata_url)
                except requests.RequestException as e:
                    print(f"Got error while receiving data: {str(e)}")
                    start_index += 1
                    pbar.update(1)
                    continue

                xml = ET.XML(res.content)

                errors = []

                namespaces = xml.nsmap
                gmd = namespaces.get('gmd')
                gco = namespaces.get('gco')

                created = False
                changed = False

                dataset = Dataset.objects.filter(geoportal_id=dataset_id).first()
                if not dataset:
                    created = True
                    dataset = Dataset.objects.create(
                        geoportal_id=dataset_id,
                        published=timezone.now()
                    )

                # resource_subclass
                dataset_resource_subclass = _get_elem("{%s}hierarchyLevel" % gmd, xml)
                dataset_resource_subclass = _get_elem("{%s}MD_ScopeCode" % gmd, dataset_resource_subclass)
                if dataset_resource_subclass is not None and dataset_resource_subclass.text == "service":
                    dataset.service = True
                    service_resource_subclass = _create_or_get_service_resource_subclass()
                    if not dataset.type.filter(pk=service_resource_subclass.pk):
                        changed = True
                        dataset.resource_subclass.add(service_resource_subclass)

                # dataset info
                dataset_info = _get_elem("{%s}identificationInfo" % gmd, xml)

                # title and description
                dataset_title = _get_elem(".//{%s}title" % gmd, dataset_info)
                dataset_title_lt = _get_elem(".{%s}CharacterString" % gco, dataset_title)
                dataset_title_en = _get_elem(".//{%s}LocalisedCharacterString" % gmd, dataset_title)

                dataset_description = _get_elem(".//{%s}abstract" % gmd, dataset_info)
                dataset_description_lt = _get_elem(".{%s}CharacterString" % gco, dataset_description)
                dataset_description_en = _get_elem(".//{%s}LocalisedCharacterString" % gmd, dataset_description)

                dataset.set_current_language("en")
                if dataset_title_en is not None:
                    if dataset.title != dataset_title_en.text:
                        changed = True
                        dataset.title = dataset_title_en.text
                if dataset_description_en is not None:
                    if dataset.description != dataset_description_en.text:
                        changed = True
                        dataset.description = dataset_description_en.text

                dataset.set_current_language("lt")
                if dataset_title_lt is not None:
                    if dataset.title != dataset_title_lt.text:
                        changed = True
                        dataset.title = dataset_title_lt.text
                if dataset_description_lt is not None:
                    if dataset.description != dataset_description_lt.text:
                        changed = True
                        dataset.description = dataset_description_lt.text
                dataset.save()

                # keywords
                keywords = _get_elem(".//{%s}keyword" % gmd, dataset_info, find_all=True)
                keyword_list = []
                for keyword in keywords:
                    keyword = _get_elem("{%s}CharacterString" % gco, keyword)
                    if keyword is not None and keyword.text and keyword.text not in keyword_list:
                        keyword_list.append(keyword.text)

                dataset_keywords = sorted(set([k.strip().lower() for k in dataset.tags.values_list("name", flat=True)]))
                keyword_list = sorted(set([k.strip().lower() for k in keyword_list]))
                if dataset_keywords != keyword_list:
                    changed = True
                    dataset.tags = keyword_list

                # frequency
                frequency_value = _get_elem(".//{%s}MD_MaintenanceFrequencyCode" % gmd, dataset_info)
                if frequency_value is not None:
                    frequency = _get_frequency(frequency_value.text)
                    if created or dataset.frequency != frequency:
                        changed = True
                        if frequency:
                            dataset.frequency = frequency
                        else:
                            dataset.frequency = None
                            errors.append(f'Nerastas atnaujinimo periodiškumas: "{frequency_value.text}"')

                # access rights and licence
                access_rights_value = _get_elem(".//{%s}accessConstraints" % gmd, dataset_info)
                access_rights_value = _get_elem(".//{%s}MD_RestrictionCode" % gmd, access_rights_value)
                if access_rights_value is not None:
                    access_rights = _get_access_rights(access_rights_value.text)

                    if created or dataset.access_rights != access_rights:
                        changed = True
                        if access_rights:
                            dataset.access_rights = access_rights
                        else:
                            dataset.access_rights = None
                            errors.append(f'Nerastos prieigos teisės: "{access_rights_value.text}"')

                    licence = _get_licence(access_rights_value.text)
                    if created or dataset.licence != licence:
                        changed = True
                        if licence:
                            dataset.licence = licence
                        else:
                            dataset.licence = None
                            errors.append(f'Nerasta licencija: "{access_rights_value.text}"')

                # organization
                if created:
                    # publisher will always be "Viešoji įstaiga Statybos sektoriaus vystymo agentūra" organization
                    publisher = Organization.objects.filter(company_code="305997589").first()
                    if publisher:
                        dataset.publisher = publisher

                        coordinator = publisher.representatives.filter(
                            role=Representative.COORDINATOR,
                        ).first()
                        if coordinator:
                            Representative.objects.create(
                                email=coordinator.email,
                                user=coordinator.user,
                                role=coordinator.role,
                                phone=coordinator.phone,
                                content_type=ContentType.objects.get_for_model(dataset),
                                object_id=dataset.pk
                            )
                    else:
                        errors.append(f'Nerasta tiekėjo organizacija: '
                                      f'"Viešoji įstaiga Statybos sektoriaus vystymo agentūra"')

                    organization_name = _get_elem(".//{%s}organisationName" % gmd, dataset_info)
                    organization_name = _get_elem("{%s}CharacterString" % gco, organization_name)

                    if organization_name is not None:
                        exclude = ["VĮ", ",", "Fizinis asmuo", "-", "VšĮ", "Savivaldybė", "-", "AB", "UAB", "\""]
                        stripped_organization_name = organization_name.text
                        for e in exclude:
                            stripped_organization_name = stripped_organization_name.replace(e, "")
                        stripped_organization_name = stripped_organization_name.strip()

                        organization = Organization.objects.filter(
                            Q(title__icontains=stripped_organization_name) |
                            Q(alternative_titles__icontains=organization_name.text)
                        ).first()

                        if organization:
                            dataset.organization = organization
                        else:
                            dataset.creator_text = organization_name.text
                            errors.append(f'Nerasta organizacija: "{organization_name.text}"')

                # distribution
                distribution_info = _get_elem(".//{%s}distributionInfo" % gmd, xml)

                distribution_format = _get_elem(".//{%s}distributionFormat" % gmd, distribution_info)
                distribution_format = _get_elem(".//{%s}MD_Format_GC" % gmd, distribution_format)

                if dataset.service:
                    if data_url and data_url != "-" and dataset.endpoint_url != data_url:
                        changed = True
                        dataset.endpoint_url = data_url
                    if distribution_format is not None and distribution_format.text != "-":
                        if endpoint_type := GeoportalFormatValue.objects.filter(
                            value__iexact=distribution_format.text
                        ).first():
                            endpoint_type = endpoint_type.geoportal_format.format
                            if endpoint_type and endpoint_type != dataset.endpoint_type:
                                changed = True
                                dataset.endpoint_type = endpoint_type
                        else:
                            errors.append(f'Nerastas API formatas: "{distribution_format.text}"')

                    if dataset.endpoint_url:
                        dataset.status = Dataset.HAS_DATA
                        comment_status = Comment.OPENED
                    else:
                        dataset.status = Dataset.INVENTORED
                        comment_status = Comment.INVENTORED
                else:
                    if data_url and data_url != "-":
                        dataset.status = Dataset.HAS_DATA
                        comment_status = Comment.OPENED

                        if (
                            distribution_format is not None and
                            distribution_format.text and
                            distribution_format.text != "-"
                        ):
                            formats = [frm.strip() for frm in distribution_format.text.split(',')]
                            for frm in formats:
                                if frm:
                                    if dist_format := GeoportalFormatValue.objects.filter(
                                        value__iexact=frm
                                    ).first():
                                        dist_format = dist_format.geoportal_format.format
                                        if not dataset.datasetdistribution_set.filter(
                                            download_url=data_url,
                                            format=dist_format
                                        ):
                                            changed = True
                                            DatasetDistribution.objects.create(
                                                dataset=dataset,
                                                download_url=data_url,
                                                format=dist_format
                                            )
                                    else:
                                        if not dataset.datasetdistribution_set.filter(
                                            download_url=data_url,
                                        ):
                                            changed = True
                                            DatasetDistribution.objects.create(
                                                dataset=dataset,
                                                download_url=data_url
                                            )
                                        errors.append(f'Nerastas formatas: "{frm}"')
                        elif not dataset.datasetdistribution_set.filter(download_url=data_url):
                            changed = True
                            DatasetDistribution.objects.create(
                                dataset=dataset,
                                download_url=data_url
                            )
                    else:
                        dataset.status = Dataset.INVENTORED
                        comment_status = Comment.INVENTORED

                # status comment
                latest_status_comment = Comment.objects.filter(
                    content_type=ContentType.objects.get_for_model(dataset),
                    object_id=dataset.pk,
                    type=Comment.STATUS,
                    status__isnull=False
                ).order_by('-created').first()

                if not latest_status_comment or latest_status_comment.status != comment_status:
                    Comment.objects.create(
                        content_type=ContentType.objects.get_for_model(dataset),
                        object_id=dataset.pk,
                        user=sys_user,
                        type=Comment.STATUS,
                        status=comment_status,
                    )

                # category
                categories = _get_elem(".//{%s}MD_TopicCategoryCode" % gmd, dataset_info, find_all=True)
                dataset_categories = dataset.category.all()
                category_list = []
                for category in categories:
                    category_value = category
                    if category := _get_categories(category_value.text):
                        for cat in category:
                            category_list.append(cat)
                            if not dataset.category.filter(pk=cat.pk):
                                changed = True
                                dataset.category.add(cat)
                    else:
                        errors.append(f'Nerasta kategorija: "{category_value.text}"')
                removed_categories = list(set(dataset_categories) - set(category_list))
                for cat in removed_categories:
                    changed = True
                    dataset.category.remove(cat)

                # add dataset to Geoportal catalog
                geoportal_catalog = Dataset.objects.filter(
                    translations__title="Lietuvos erdvinės informacijos portalas",
                ).first()
                relation = Relation.objects.filter(name=Relation.CATALOG).first()
                if geoportal_catalog and relation and not DatasetRelation.objects.filter(
                    relation=relation,
                    dataset=dataset,
                    part_of=geoportal_catalog
                ):
                    dataset_relation = DatasetRelation.objects.create(
                        relation=relation,
                        dataset=dataset,
                        part_of=geoportal_catalog
                    )
                    dataset.part_of.add(dataset_relation)

                # inform superusers about import errors
                dataset_url = "https://%s%s" % (
                    Site.objects.get_current().domain,
                    reverse('dataset-detail', args=[dataset.pk])
                )
                if errors:
                    emails = []
                    users = User.objects.filter(is_superuser=True)

                    errors = "<br/>".join(errors)
                    title = f'Klaida importuojant Geoportal duomenų rinkinį id: {dataset.pk}'
                    description = f"Importuojant duomenų rinkinį iš Geoportal (<a href='{metadata_url}'>" \
                                  f"metaduomenys</a>) įvyko klaida: <br/>{errors}"

                    for user in users:
                        if not Task.objects.filter(
                            title=title,
                            description=description,
                            user=user,
                            status=Task.CREATED,
                            type=Task.ERROR_GEOPORTAL,
                            content_type=ContentType.objects.get_for_model(dataset),
                            object_id=dataset.pk
                        ):
                            emails.append(user.email)
                            Task.objects.create(
                                title=title,
                                description=description,
                                user=user,
                                status=Task.CREATED,
                                type=Task.ERROR_GEOPORTAL,
                                content_type=ContentType.objects.get_for_model(dataset),
                                object_id=dataset.pk
                            )
                    if emails:
                        email(
                            emails,
                            'geoportal-error',
                            "vitrina/datasets/emails/sub/geoportal_error.md",
                            {
                                'title': dataset.title,
                                'url': dataset_url
                            }
                        )
                        print(title)
                        print(description)

                # inform subscribers
                organization_subs = Subscription.objects.none()
                if dataset.organization:
                    organization_subs = Subscription.objects.filter(
                        sub_type=Subscription.ORGANIZATION,
                        content_type=ContentType.objects.get_for_model(Organization),
                        object_id=dataset.organization.pk,
                        dataset_update_sub=True
                    )
                dataset_subs = Subscription.objects.filter(
                    sub_type=Subscription.DATASET,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    object_id=dataset.pk,
                    dataset_update_sub=True
                )
                subs = organization_subs | dataset_subs

                if created:
                    if dataset.organization:
                        sub_email_list = []
                        for sub in subs:
                            Task.objects.create(
                                title=f"Duomenų rinkinys organizacijai: {dataset.organization}",
                                description=f"Sukurtas naujas duomenų rinkinys organizacijai: {dataset.organization}.",
                                content_type=ContentType.objects.get_for_model(dataset),
                                object_id=dataset.pk,
                                organization=dataset.organization,
                                status=Task.CREATED,
                                type=Task.DATASET,
                                user=sub.user
                            )
                            if sub.user.email and sub.email_subscribed and sub.user.email not in sub_email_list:
                                sub_email_list.append(sub.user.email)
                            email(
                                sub_email_list,
                                'dataset-created-sub',
                                "vitrina/datasets/emails/sub/created.md",
                                {
                                    'dataset': dataset,
                                    'link': dataset_url
                                }
                            )
                # send email about update, only if something has changed
                elif changed:
                    sub_email_list = []
                    for sub in subs:
                        Task.objects.create(
                            title=f"Duomenų rinkinys: {dataset}",
                            description=f"Atnaujintas duomenų rinkinys: {dataset}",
                            content_type=ContentType.objects.get_for_model(Dataset),
                            object_id=dataset.pk,
                            organization=dataset.organization,
                            status=Task.CREATED,
                            type=Task.DATASET,
                            user=sub.user
                        )
                        if sub.user.email and sub.email_subscribed and sub.user.email not in sub_email_list:
                            sub_email_list.append(sub.user.email)
                    if sub_email_list:
                        email(
                            sub_email_list,
                            'dataset-updated',
                            "vitrina/datasets/emails/sub/updated.md",
                            {
                                'title': dataset,
                                'link': dataset_url
                            }
                        )

                dataset.save()

                # history
                if created or changed:
                    with reversion.create_revision():
                        dataset.save()
                        reversion.set_user(sys_user)
                        if created:
                            reversion.set_comment(Dataset.CREATED)
                        elif changed:
                            reversion.set_comment(Dataset.EDITED)

            start_index += 1
            pbar.update(1)

        if start_index <= total_results:
            try:
                response = requests.get(url, data=body.format(start_index))
            except requests.RequestException as e:
                print(f"Got error while receiving data: {str(e)}")
                return
            xml = ET.XML(response.content)

            records = _get_elem(".//{%s}Record" % csw, xml, find_all=True)
        else:
            records = []


if __name__ == '__main__':
    run(main)
