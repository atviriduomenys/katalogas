from django.http import HttpRequest


def is_org_dataset_list(request: HttpRequest):
    return request.resolver_match.url_name == 'organization-datasets'


def is_manager_dataset_list(request: HttpRequest):
    return request.resolver_match.url_name == 'manager-dataset-list'