from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.orgs.models import Organization

WIZARD_NODE_ORGANIZATION = "organization"
WIZARD_NODE_IS = "is"
WIZARD_NODE_SERVICE = "service"
WIZARD_NODE_DATASET = "dataset"
WIZARD_NODE_DISTRIBUTION = "distribution"

WIZARD_ALLOWED_CHILDREN: dict[str, list[str]] = {
    WIZARD_NODE_ORGANIZATION: [WIZARD_NODE_IS],
    WIZARD_NODE_IS: [WIZARD_NODE_IS, WIZARD_NODE_SERVICE, WIZARD_NODE_DATASET],
    WIZARD_NODE_SERVICE: [WIZARD_NODE_DATASET],
    WIZARD_NODE_DATASET: [WIZARD_NODE_DISTRIBUTION],
    WIZARD_NODE_DISTRIBUTION: [],
}

WIZARD_NODE_ICONS: dict[str, str] = {
    WIZARD_NODE_ORGANIZATION: "fa-building",
    WIZARD_NODE_IS: "fa-server",
    WIZARD_NODE_SERVICE: "fa-cogs",
    WIZARD_NODE_DATASET: "fa-database",
    WIZARD_NODE_DISTRIBUTION: "fa-file-lines",
}

WIZARD_NODE_LABELS: dict[str, str] = {
    WIZARD_NODE_ORGANIZATION: _("Organizacija"),
    WIZARD_NODE_IS: _("Informacinė sistema"),
    WIZARD_NODE_SERVICE: _("Paslauga"),
    WIZARD_NODE_DATASET: _("Duomenų rinkinys"),
    WIZARD_NODE_DISTRIBUTION: _("Distribucija"),
}

WIZARD_NODE_LABELS_PLURAL: dict[str, str] = {
    WIZARD_NODE_ORGANIZATION: _("Organizacija"),
    WIZARD_NODE_IS: _("Informacinės sistemos"),
    WIZARD_NODE_SERVICE: _("Paslaugos"),
    WIZARD_NODE_DATASET: _("Duomenų rinkiniai"),
    WIZARD_NODE_DISTRIBUTION: _("Distribucijos"),
}

WIZARD_TYPE_ORDER: dict[str, int] = {
    WIZARD_NODE_ORGANIZATION: 0,
    WIZARD_NODE_IS: 1,
    WIZARD_NODE_SERVICE: 2,
    WIZARD_NODE_DATASET: 3,
    WIZARD_NODE_DISTRIBUTION: 4,
}

WIZARD_NODE_HELPERS: dict[str, str] = {
    WIZARD_NODE_IS: _("Sukurti naują informacinę sistemą po šiuo mazgu."),
    WIZARD_NODE_SERVICE: _("Sukurti naują paslaugą po šiuo mazgu."),
    WIZARD_NODE_DATASET: _("Sukurti naują duomenų rinkinį po šiuo mazgu."),
    WIZARD_NODE_DISTRIBUTION: _("Pridėti naują duomenų rinkinio distribuciją."),
}

WIZARD_TYPE_TO_SUBCLASS_NAME: dict[str, str] = {
    WIZARD_NODE_IS: DCATResourceSubclass.INFORMATION_SYSTEM,
    WIZARD_NODE_SERVICE: DCATResourceSubclass.SERVICE,
    WIZARD_NODE_DATASET: DCATResourceSubclass.DATASET,
}

WIZARD_SUBCLASS_TO_NODE_TYPE: dict[str, str] = {
    DCATResourceSubclass.INFORMATION_SYSTEM: WIZARD_NODE_IS,
    DCATResourceSubclass.SERVICE: WIZARD_NODE_SERVICE,
    DCATResourceSubclass.DATASET: WIZARD_NODE_DATASET,
}

_WIZARD_TREE_MAX_DEPTH = 8


def _wizard_node_type(dataset: Dataset) -> str:
    name = dataset.subclass.name if dataset.subclass_id else None
    if name == DCATResourceSubclass.INFORMATION_SYSTEM:
        return WIZARD_NODE_IS
    if name == DCATResourceSubclass.SERVICE:
        return WIZARD_NODE_SERVICE
    return WIZARD_NODE_DATASET


def _wizard_dataset_title(dataset: Dataset) -> str:
    title = dataset.safe_translation_getter("title", any_language=True)
    return title or f"#{dataset.pk}"


def _wizard_ancestor_summary(node_type: str, node_id: int, title: str) -> dict:
    key = f"org:{node_id}" if node_type == WIZARD_NODE_ORGANIZATION else f"{node_type}:{node_id}"
    return {
        "key": key,
        "type": node_type,
        "type_label": str(WIZARD_NODE_LABELS[node_type]),
        "id": node_id,
        "title": title,
    }


def _build_wizard_tree(organization: Organization) -> tuple[list[dict], dict[str, dict]]:
    """Build the org's content tree and a flat key→selection map for the wizard Alpine state."""
    _subclass_uuids: dict[str, str] = {
        s.name: str(s.pk)
        for s in DCATResourceSubclass.objects.filter(
            name__in=[
                DCATResourceSubclass.INFORMATION_SYSTEM,
                DCATResourceSubclass.SERVICE,
                DCATResourceSubclass.DATASET,
            ]
        )
    }

    def _node_create_urls(node_type: str, node_id: int) -> dict[str, str]:
        urls: dict[str, str] = {}
        for child_type in WIZARD_ALLOWED_CHILDREN.get(node_type, []):
            if child_type == WIZARD_NODE_DISTRIBUTION:
                urls[child_type] = reverse(
                    "dcat-distribution-create",
                    kwargs={
                        "organization_id": organization.pk,
                        "dataset_id": node_id,
                    },
                )
            else:
                subclass_name = WIZARD_TYPE_TO_SUBCLASS_NAME.get(child_type)
                if subclass_name and subclass_name in _subclass_uuids:
                    urls[child_type] = reverse(
                        "dcat-dataset-create-with-parent",
                        kwargs={
                            "organization_id": organization.pk,
                            "parent_id": node_id,
                            "subclass_uuid": _subclass_uuids[subclass_name],
                        },
                    )
        return urls

    org_datasets = list(
        Dataset.objects.filter(organization=organization, is_public=False).select_related("subclass").order_by("path")
    )
    datasets_by_id = {d.pk: d for d in org_datasets}
    datasets_by_path = {d.path: d for d in org_datasets}

    parent_to_children: dict[int, list[int]] = {}
    for dataset in org_datasets:
        parent_path = dataset.path[: -Dataset.steplen]
        if parent_path and parent_path in datasets_by_path:
            parent = datasets_by_path[parent_path]
            parent_to_children.setdefault(parent.pk, []).append(dataset.pk)

    top_level = [d for d in org_datasets if d.path[: -Dataset.steplen] not in datasets_by_path]

    nodes_by_key: dict[str, dict] = {}
    org_key = f"org:{organization.pk}"
    org_ancestor = _wizard_ancestor_summary(WIZARD_NODE_ORGANIZATION, organization.pk, organization.title)

    def register_selection(
        key: str,
        node_type: str,
        node_id: int,
        title: str,
        ancestors: list[dict],
        fragment_url: str = "",
        create_urls: dict | None = None,
    ) -> None:
        nodes_by_key[key] = {
            "key": key,
            "type": node_type,
            "type_label": str(WIZARD_NODE_LABELS[node_type]),
            "id": node_id,
            "title": title,
            "icon": WIZARD_NODE_ICONS[node_type],
            "allowed_children": list(WIZARD_ALLOWED_CHILDREN.get(node_type, [])),
            "ancestors": list(ancestors),
            "fragment_url": fragment_url,
            "create_urls": create_urls or {},
        }

    def build(dataset: Dataset, depth: int, visited: frozenset, ancestors: list[dict]) -> dict | None:
        if depth >= _WIZARD_TREE_MAX_DEPTH or dataset.pk in visited:
            return None
        visited = visited | {dataset.pk}
        node_type = _wizard_node_type(dataset)
        node_key = f"{node_type}:{dataset.pk}"
        node_title = _wizard_dataset_title(dataset)
        my_ancestor = _wizard_ancestor_summary(node_type, dataset.pk, node_title)
        next_ancestors = ancestors + [my_ancestor]
        dataset_fragment_url = reverse(
            "dcat-dataset-update",
            kwargs={"organization_id": organization.pk, "dataset_id": dataset.pk},
        )

        children: list[dict] = []
        for child_id in parent_to_children.get(dataset.pk, []):
            child = datasets_by_id.get(child_id)
            if child is None:
                continue
            child_node = build(child, depth + 1, visited, next_ancestors)
            if child_node is not None:
                children.append(child_node)

        for dist in dataset.datasetdistribution_set.all():
            dist_title = dist.safe_translation_getter("title", any_language=True) or f"#{dist.pk}"
            dist_key = f"{WIZARD_NODE_DISTRIBUTION}:{dist.pk}"
            dist_fragment_url = reverse(
                "dcat-distribution-update",
                kwargs={
                    "organization_id": organization.pk,
                    "dataset_id": dataset.pk,
                    "distribution_id": dist.pk,
                },
            )
            register_selection(
                dist_key,
                WIZARD_NODE_DISTRIBUTION,
                dist.pk,
                dist_title,
                next_ancestors,
                fragment_url=dist_fragment_url,
            )
            children.append(
                {
                    "type": WIZARD_NODE_DISTRIBUTION,
                    "type_label": WIZARD_NODE_LABELS[WIZARD_NODE_DISTRIBUTION],
                    "type_label_plural": WIZARD_NODE_LABELS_PLURAL[WIZARD_NODE_DISTRIBUTION],
                    "icon": WIZARD_NODE_ICONS[WIZARD_NODE_DISTRIBUTION],
                    "id": dist.pk,
                    "key": dist_key,
                    "title": dist_title,
                    "children": [],
                    "allowed_children": [],
                    "fragment_url": dist_fragment_url,
                }
            )

        children.sort(key=lambda c: WIZARD_TYPE_ORDER.get(c["type"], 99))
        dataset_create_urls = _node_create_urls(node_type, dataset.pk)
        register_selection(
            node_key,
            node_type,
            dataset.pk,
            node_title,
            ancestors,
            fragment_url=dataset_fragment_url,
            create_urls=dataset_create_urls,
        )
        return {
            "type": node_type,
            "type_label": WIZARD_NODE_LABELS[node_type],
            "type_label_plural": WIZARD_NODE_LABELS_PLURAL[node_type],
            "icon": WIZARD_NODE_ICONS[node_type],
            "id": dataset.pk,
            "key": node_key,
            "title": node_title,
            "children": children,
            "allowed_children": WIZARD_ALLOWED_CHILDREN.get(node_type, []),
            "fragment_url": dataset_fragment_url,
            "create_urls": dataset_create_urls,
        }

    tree: list[dict] = []
    for dataset in top_level:
        node = build(dataset, 0, frozenset(), [org_ancestor])
        if node is not None:
            tree.append(node)
    tree.sort(key=lambda n: WIZARD_TYPE_ORDER.get(n["type"], 99))

    org_fragment_url = reverse("organization-change", kwargs={"pk": organization.pk})
    org_create_urls: dict[str, str] = {}
    for child_type in WIZARD_ALLOWED_CHILDREN.get(WIZARD_NODE_ORGANIZATION, []):
        subclass_name = WIZARD_TYPE_TO_SUBCLASS_NAME.get(child_type)
        if subclass_name and subclass_name in _subclass_uuids:
            org_create_urls[child_type] = reverse(
                "dcat-dataset-create",
                kwargs={
                    "organization_id": organization.pk,
                    "subclass_uuid": _subclass_uuids[subclass_name],
                },
            )
    register_selection(
        org_key,
        WIZARD_NODE_ORGANIZATION,
        organization.pk,
        organization.title,
        [],
        fragment_url=org_fragment_url,
        create_urls=org_create_urls,
    )
    return tree, nodes_by_key
