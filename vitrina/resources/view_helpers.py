from vitrina.datasets.models import Dataset
from vitrina.resources.models import DatasetDistribution


def get_default_distribution_name(dataset: Dataset) -> str:
    latest_name = (
        DatasetDistribution.objects.filter(dataset=dataset, name__iregex=r"resource[0-9]+")
        .order_by("name")
        .values_list("name", flat=True)
        .last()
    )
    if not latest_name:
        name = "resource1"
    else:
        duplicate_name_suffix = latest_name.replace("resource", "")
        try:
            duplicate_name_suffix = int(duplicate_name_suffix)
        except ValueError:
            duplicate_name_suffix = 0
        duplicate_name_suffix += 1
        name = f"resource{duplicate_name_suffix}"

    return name
