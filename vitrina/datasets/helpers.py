from django.http import HttpRequest

def is_manager_dataset_list(request: HttpRequest):
    return request.resolver_match.url_name == 'manager-dataset-list'