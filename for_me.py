
from vitrina.datasets.models import Dataset
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Metadata, Version, Model, Property, EnumItem, ParamItem, Prefix


def collect_full_version(dataset_id):
    # dataset_ids = Metadata.objects.values_list('dataset_id', flat=True).distinct()
    dataset_ids = [dataset_id]
    for dataset_id in dataset_ids:
        version_ids = Version.objects.filter(dataset_id=dataset_id).values_list('id', flat=True).distinct().order_by('version')
        previous_version = None
        for version_id in version_ids:
            if not previous_version:
                full_metadata_rows = Metadata.objects.filter(dataset_id=dataset_id, metadata_version_id=version_id)
                previous_version = version_id
                first_version = True
            else:
                current_version_metadata_rows = list(Metadata.objects.filter(
                    dataset_id=dataset_id, metadata_version_id=version_id
                ))
                previous_version_metadata_rows = list(Metadata.objects.filter(
                    dataset_id=dataset_id, metadata_version_id=previous_version
                ))

                full_metadata_rows = current_version_metadata_rows + previous_version_metadata_rows

                Metadata.objects.filter(
                    dataset_id=dataset_id, metadata_version_id=version_id
                ).delete()

                previous_version = version_id
                first_version = False
            print(f"Dataset {dataset_id}, Version {version_id}, Rows: {len(full_metadata_rows)}, First: {first_version}")
            yield full_metadata_rows, version_id, first_version, dataset_id


def handle_first_version(metadata_row, version_id):
    connected_table = metadata_row.content_type.model_class()
    connected_table_instance = connected_table.objects.filter(id=metadata_row.object_id).first()
    if isinstance(connected_table_instance, Dataset):
        return
    connected_table_instance.version_id = version_id
    if isinstance(connected_table_instance, Model):
        if connected_table_instance.base:
            connected_table_instance.base.version_id = version_id
    if isinstance(connected_table_instance, EnumItem):
        connected_table_instance.enum.version_id = version_id

    connected_table_instance.save()


def create_needed_objects(dataset_id):
    for metadata_rows, version_id, first_version, dataset_id in collect_full_version(dataset_id):
        old_new_models = {}
        all_new_props = []
        old_new_props = {}
        all_enum_items = []
        all_param_items = []
        if first_version:
            for metadata_row in metadata_rows:
                metadata_row.version_id = version_id
                handle_first_version(metadata_row, version_id)
            _copy_prefix_db_distribution(dataset_id, version_id)
            continue

        for metadata_row in metadata_rows:
            new_model = metadata_row.content_type.model_class()
            new_model_instance = new_model.objects.filter(id=metadata_row.object_id).first()

            if isinstance(new_model_instance, Dataset):
                continue

            new_model_instance.pk = None
            new_model_instance.version_id = version_id
            new_model_instance.save()

            if isinstance(new_model_instance, Model):
                old_new_models[metadata_row.object_id] = new_model_instance.id
            if isinstance(new_model_instance, Property):
                all_new_props.append(new_model_instance)
                old_new_props[metadata_row.object_id] = new_model_instance.id
            if isinstance(new_model_instance, EnumItem):
                all_enum_items.append(new_model_instance)
            if isinstance(new_model_instance, ParamItem):
                all_param_items.append(metadata_row)

            metadata_row.pk = None
            metadata_row.metadata_version_id = version_id
            metadata_row.object_id = new_model_instance.pk
            metadata_row.save()

        _fix_model_bases(old_new_models, version_id)
        _fix_property_relationship(old_new_models, all_new_props, version_id)
        _fix_enum_values(all_enum_items, old_new_props, version_id)
        _fix_param_values(all_param_items, old_new_props, version_id)
        _copy_prefix_db_distribution(dataset_id, version_id)


def _fix_model_bases(old_new_models: dict, version_id: Version):
    for old_model_pk, new_model_pk in old_new_models.items():
        old_model = Model.objects.filter(pk=old_model_pk).first()
        new_model = Model.objects.filter(pk=new_model_pk).first()
        if old_base := old_model.base:
            old_base_pk = old_base.pk
            new_base = old_base
            new_base.pk = None
            new_base.version_id = version_id
            new_base.save()

            new_model.base = new_base
            new_model.save()

            metadata_of_the_base = Metadata.objects.filter(object_id=old_base_pk, content_type_id=125).first()
            new_metadata_of_the_base = metadata_of_the_base
            new_metadata_of_the_base.pk = None
            new_metadata_of_the_base.metadata_version_id = version_id
            new_metadata_of_the_base.object_id = new_base.pk
            new_metadata_of_the_base.save()


def _fix_enum_values(all_enum_items: list, old_new_props: dict, version_id: Version):
    enum_created = {}
    for enum_item in all_enum_items:
        breakpoint()
        old_enum = enum_item.enum
        old_pk = old_enum.pk
        if old_pk not in enum_created:
            new_enum = old_enum
            new_enum.pk = None
            new_enum.object_id = old_new_props[old_enum.object_id]
            new_enum.version_id = version_id
            new_enum.save()
            enum_created[old_pk] = new_enum


        enum_item.enum = enum_created[old_pk]
        enum_item.save()

def _fix_param_values(all_param_items: list, old_new_props: dict, version_id: Version):
    param_created = {}
    for param_item in all_param_items:
        old_param = param_item.enum
        old_pk = old_param.pk

        if old_pk not in param_created:
            new_param = old_param
            new_param.pk = None
            new_param.object_id = old_new_props[old_param.object_id]
            new_param.version_id = version_id
            new_param.save()
            param_created[old_pk] = new_param

        param_item.enum = param_created[old_pk]
        param_item.save()


def _fix_property_relationship(old_new_models: dict, all_new_props: list, version_id: Version):
    for _property in all_new_props:
        current_model_id = _property.model.pk
        if current_model_id in old_new_models:
            _property.model_id = old_new_models[current_model_id]
            _property.version_id = version_id
            _property.save()


def _copy_prefix_db_distribution(dataset: Dataset, version_id: Version):
    prefixes = Metadata.objects.filter(content_type_id=131, dataset=dataset, draft=True)
    dataset_distributions = Metadata.objects.filter(content_type_id=148, dataset=dataset, draft=True)

    for metadata_prefix in prefixes:
        actual_prefix = Prefix.objects.filter(id=metadata_prefix.object_id).first()
        actual_prefix.pk = None
        actual_prefix.version_id = version_id
        actual_prefix.save()

        metadata_prefix.pk = None
        metadata_prefix.metadata_version_id = version_id
        metadata_prefix.draft = False
        metadata_prefix.object_id = actual_prefix.pk
        metadata_prefix.save()

    for metadata_dataset_distribution in dataset_distributions:
        actual_dataset_distribution = DatasetDistribution.objects.filter(id=metadata_dataset_distribution.object_id).first()
        actual_dataset_distribution.pk = None
        actual_dataset_distribution.connected_version_id = version_id
        actual_dataset_distribution.save()

        metadata_dataset_distribution.pk = None
        metadata_dataset_distribution.metadata_version_id = version_id
        metadata_dataset_distribution.draft = False
        metadata_dataset_distribution.object_id = actual_dataset_distribution.pk
        metadata_dataset_distribution.save()

create_needed_objects(dataset_id=2433)
