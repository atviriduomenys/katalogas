import os
from typing import Dict

from tqdm import tqdm
from typer import run, Argument
import csv
import pandas as pd
import hashlib
import pathlib
import dataclasses

import django


organization_entries = []
dataset_entries = []
repository_dataset_entries = []

UNKNOWN = 'unknown'


def main(
    manifest_path: str = Argument('manifest-data/', help=(
        'Path to where dataset manifest files are saved'
    )),
):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
    django.setup()

    total = 0
    total_xls = 0
    total_not_csv = 0
    standartized = 0
    random = 0
    found_ids = 0
    rows_to_append = []
    manifest_path = pathlib.Path(manifest_path)

    repo_files = []

    orgs = read_orgs_mapping(manifest_path)
    datasets = read_datasets_mapping(manifest_path)
    read_structure_files(orgs, datasets)

    return

    dump_orgs(organization_entries, manifest_path)
    dump_datasets(dataset_entries, manifest_path)

    for root, dirs, files in os.walk(os.path.join(manifest_path, 'datasets/gov/')):
        for filename in files:
            if '.csv' in filename:
                repo_files.append(os.path.join(root, filename))

    pbar2 = tqdm('Reading repository information', total=len(repo_files))
    with (pbar2):
        df = pd.read_csv(os.path.join(manifest_path, 'datasets.csv'), index_col='name')
        for repo_item in repo_files:
            checksum = get_digest(repo_item)
            with open(repo_item, 'r', encoding='utf-8') as f:
                try:
                    dfe = pd.read_csv(f)
                    if not dfe.columns.empty:
                        if 'dataset' in dfe.columns:
                            dataset_code = dfe['dataset'].iat[0]
                            dataset_title = dfe['title'].iat[0]
                            if not pd.isna(dataset_code):
                                if dataset_code not in df.index:
                                    if pd.isna(dataset_title):
                                        dataset_title = ''
                                    rows_to_append.append(['', dataset_code, dataset_title, '', checksum])
                except:
                    print(f'Error reading data from file: {f.name}')
            pbar2.update(1)

    if not os.path.exists(manifest_path):
        os.makedirs(manifest_path)

    dump_repo_datasets(rows_to_append, manifest_path)

    print(f'\nTotal CSV files found in catalog: {total}, excel files: {total_xls}, other formats: {total_not_csv}.\n'
          f'Standartized: {standartized}, random: {random}.\n'
          f'Found: {found_ids} codes in structure files.')
    print(f'Dataset mappings created: {len(dataset_entries)}')
    print(f'Total files in repository: {len(repo_files)}')
    print(f'New dataset mappings found in repository: {len(rows_to_append)}')
    print(f'Organization mappings created: {len(organization_entries)}\n')


@dataclasses.dataclass
class OrganizationMapping:
    id: int
    name: str
    title: str


def read_orgs_mapping(
    manifest_path: pathlib.Path,
) -> Dict[
    str,  # organization id from db
    OrganizationMapping,
]:
    orgs = {}
    orgs_path = manifest_path / 'orgs.csv'
    if orgs_path.exists():
        with orgs_path.open(encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                orgs[row['id']] = OrganizationMapping(
                    id=row['id'],
                    name=row['name'],
                    title=row['name'],
                )
    return orgs


@dataclasses.dataclass
class DatasetMapping:
    id: int
    name: str
    title: str
    organization: str
    checksum: str


def read_datasets_mapping(
    manifest_path: pathlib.Path,
) -> Dict[
    str,  # dataset id from db
    DatasetMapping,
]:
    datasets = {}
    datasets_path = os.path.join(manifest_path, 'datasets.csv')
    if datasets_path.exists():
        with datasets_path.open(encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                datasets[row['id']] = DatasetMapping(
                    id=row['id'],
                    name=row['name'],
                    title=row['title'],
                    organization=row['org'],
                    checksum=row['checksum'],
                )
    return datasets


def read_structure_files(
    orgs: Dict[str, OrganizationMapping],
    datasets: Dict[str, DatasetMapping],
) -> None:  # updates orgs and datasets in place
    qs = get_datasets_in_db()
    pbar = tqdm(qs, 'Exporting manifest information', total=qs.count())

    for dataset in pbar:
        item = dataset.current_structure
        org = dataset.organization

        if org.id in orgs:
            org.name = orgs[org.id]

        if dataset.id in datasets:
            dataset_name = datasets[dataset.id].name

        df = None
        if item.filename.endswith('.csv'):
            with open(item.file.path, encoding='utf-8') as f:
                sample = f.read(20)
            for sep in (',', ';', '\t'):
                if sep in sample:
                    break
            else:
                sep = None
            if sep:
                df = pd.read_csv(item.file.path, sep=sep)
        elif item.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(item.file.path)

        if df is not None and 'dataset' in df.columns:
            idx = df['dataset'].first_valid_index()
            if idx is not None:
                given_dataset_name = df['dataset'].loc[idx]
                if given_dataset_name.startswith('datasets/gov/'):
                    parts = given_dataset_name.split('/')
                    if len(parts) > 2:
                        given_org_name = parts[2]
                        print(given_org_name)

        ns_path = (manifest_path / dataset_name).parent
        ns_path.mkdir(0o755, parents=True, exist_ok=True)

        checksum = get_digest(item.file.path)


def get_datasets_in_db():
    from vitrina.datasets.models import Dataset
    return (
        Dataset.objects.
        select_related(
            'current_structure',
            'organization',
        ).
        filter(
            current_structure__filename__isnull=False,
            current_structure__file__isnull=False,
        )
    )


def get_digest(file_path):
    h = hashlib.sha256()

    with open(file_path, 'rb') as file:
        chunk = True
        while chunk:
            chunk = file.read(h.block_size)
            h.update(chunk)

    return h.hexdigest()


def dump_orgs(data, manifest_path):
    path = os.path.join(manifest_path, 'orgs.csv')
    columns = ['id', 'name', 'title']
    lst = [[x.org_id, x.name, x.title] for x in data]
    df = pd.DataFrame(lst)
    if not os.path.isfile(path):
        print(f'Dumping {len(data)} organization entries to orgs.csv')
        df.to_csv(path, index=False, header=columns, quoting=csv.QUOTE_ALL)
    else:
        print('File orgs.csv already exists, updating existing values...')
        dfe = pd.read_csv(path, index_col='id')
        new_items = []
        for item in data:
            if item.org_id in dfe.index:
                if dfe.loc[item.org_id, 'title'] != item.title:
                    print(f'Updating value for {item.org_id} to: {item.title}')
                    dfe.loc[item.org_id, 'title'] = item.title
            else:
                new_items.append(item)
        n_lst = [[x.org_id, x.name, x.title] for x in new_items]
        dff = pd.DataFrame(n_lst)
        dff.to_csv(path, mode='a', index=False, header=False, quoting=csv.QUOTE_ALL)


def dump_datasets(data, manifest_path):
    multiple_entries = {}
    path = os.path.join(manifest_path, 'datasets.csv')
    columns = ['id', 'name', 'title', 'org', 'checksum']
    lst = [[x.dataset_id, x.name, x.title, x.org, x.checksum] for x in data]
    df = pd.DataFrame(lst)
    if not os.path.isfile(path):
        print(f'Dumping {len(data)} dataset entries to datasets.csv')
        df.to_csv(path, index=False, header=columns, quoting=csv.QUOTE_ALL)
    else:
        print('File datasets.csv already exists, updating existing values...')
        dfe = pd.read_csv(path, index_col='id')
        new_items = []
        for item in data:
            if item.dataset_id in dfe.index:
                rez = dfe.loc[item.dataset_id, 'checksum']
                if len(rez) != 64:
                    multiple_entries[item.dataset_id] = len(rez)
                else:
                    if dfe.loc[item.dataset_id, 'checksum'] != item.checksum:
                        print(f'Checksum mismatch for {item.dataset_id}, updating...')
                        dfe.loc[item.dataset_id, 'checksum'] = item.checksum
            else:
                new_items.append(item)
        n_lst = [[i.dataset_id, i.name, i.title, i.org, i.checksum] for i in new_items]
        dff = pd.DataFrame(n_lst)
        dff.to_csv(path, mode='a', index=False, header=False, quoting=csv.QUOTE_ALL)
    print(f'There are multiple dataset entries: {multiple_entries}')


def dump_repo_datasets(data, manifest_path):
    path = os.path.join(manifest_path, 'datasets.csv')
    dff = pd.DataFrame(data)
    dff.to_csv(path, mode='a', index=False, header=False, quoting=csv.QUOTE_ALL)


def dump_current(file, org_path, manifest_path, dataset):
    unknown_index = 0
    original_ext = '.' + file.name.split('.')[-1]
    parent_dir = os.path.join(manifest_path, 'datasets/gov/')
    if len(org_path) == 0:
        org_path = 'unknown/'
    if not org_path.endswith('/'):
        org_path = org_path + '/'
    if len(dataset.strip()) == 0:
        dataset = 'unknown' + str(unknown_index)
        unknown_index += 1
    file_path = parent_dir + org_path + dataset.strip() + original_ext
    orig = file_path.replace(file_path.split('.')[-1], 'orig')
    if not os.path.exists(parent_dir + org_path):
        os.makedirs(parent_dir + org_path)
    if original_ext == '.csv':
        lines = file.readlines()
        if not os.path.isfile(orig):
            with open(orig, 'w+') as f:
                f.writelines(lines)
        else:
            ch_target = get_digest(orig)
            ch_current = get_digest(file.name)
            if ch_target != ch_current:
                with open(orig, 'w+') as f:
                    f.writelines(lines)
        if not os.path.isfile(file_path):
            with open(file_path, 'w+') as f:
                print('dumping: ', file.readlines())
                f.writelines(lines)
        else:
            ch_target = get_digest(file_path)
            ch_current = get_digest(file.name)
            if ch_target != ch_current:
                print(f'Hash mismatch for dataset: {org_path}{dataset}, catalog {ch_current}, github {ch_target}')


if __name__ == '__main__':
    run(main)
