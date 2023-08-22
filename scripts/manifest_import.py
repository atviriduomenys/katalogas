import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from django.core.files import File as DjangoFile
from filer.models import File
from tqdm import tqdm
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Organization
from typer import run, Option
import pandas as pd
from vitrina.structure.services import create_structure_objects

organization_entries = []
dataset_entries = []
repository_dataset_entries = []


def main(
        manifest_path: str = Option("manifest-data/", help=(
                "Path to where dataset manifest files are saved"
        )),
):
    dataset_names_added = 0
    org_names_added = 0
    structures_overwritten = 0
    models_created = 0

    datasets_file = manifest_path + 'datasets.csv'
    with open(datasets_file, 'r', encoding='utf-8') as fd:
        dfd = pd.read_csv(fd)

    pbar = tqdm("Reading dataset information", total=len(dfd.index))
    with (pbar):
        for val in dfd.values.tolist():
            dataset_id = val[0]
            dataset_name = val[1]
            file_path = manifest_path + dataset_name + '.csv'
            if dataset_id > 0:
                dataset = Dataset.objects.filter(pk=dataset_id)
                if dataset.get().name is None:
                    dataset.update(name=dataset_name)
                    dataset_names_added += 1
                if os.path.isfile(file_path):
                    try:
                        structure = DatasetStructure.objects.filter(pk=dataset.get().current_structure_id).first()
                    except DatasetStructure.DoesNotExist:
                        structure = None
                    if structure:
                        if structure.file:
                            new_f = DjangoFile(
                                open(file_path, mode='rb'),
                                name=structure.filename
                            )
                            file, created = File.objects.get_or_create(
                                file=new_f,
                                original_filename=structure.filename,
                            )
                            structure.file = file
                            structure.save(update_fields=['file'])
                            structures_overwritten += 1
                            try:
                                create_structure_objects(structure)
                                models_created += 1
                            except:
                                print(f'Something went wrong with dataset {dataset_name}')
            pbar.update(1)

    orgs_file = manifest_path + 'orgs.csv'
    with open(orgs_file, 'r', encoding='utf-8') as f:
        dfo = pd.read_csv(f)

    pbar2 = tqdm('Reading organization information', total=len(dfo.index))
    with (pbar2):
        for val in dfo.values.tolist():
            org_id = val[0]
            org_name = val[1]
            org = Organization.objects.filter(pk=org_id)
            if org.get().name is None:
                org.update(name=org_name)
                org_names_added += 1
            pbar2.update(1)

    print(f'Dataset names added: {dataset_names_added}')
    print(f'Organization names added: {org_names_added}')
    print(f'Structure files overwritten: {structures_overwritten}')
    print(f'Models created: {models_created}')


if __name__ == '__main__':
    run(main)
