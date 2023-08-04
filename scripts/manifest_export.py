import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from tqdm import tqdm
from vitrina.datasets.models import DatasetStructure, DatasetStructureMapping, Dataset
from vitrina.orgs.models import Organization, OrganizationMapping
from typer import run, Option
import csv
import pandas as pd
import hashlib

organization_entries = []
dataset_entries = []
repository_dataset_entries = []


def main(
        manifest_path: str = Option("manifest-data/", help=(
                "Path to where dataset manifest files are saved"
        )),
):
    pbar = tqdm("Exporting manifest information", total=DatasetStructure.objects.count())

    total = 0
    total_xls = 0
    total_not_csv = 0
    standartized = 0
    random = 0
    found_ids = 0
    rows_to_append = []

    repo_files = []

    with (pbar):
        for item in DatasetStructure.objects.all():
            if item.filename is not None:
                dataset_id = item.dataset_id
                dataset = Dataset.objects.filter(pk=dataset_id).first()
                org_id = dataset.organization.pk
                org_title = Organization.objects.get(pk=org_id).title

                if item.standardized:
                    standartized += 1
                else:
                    random += 1
                if 'csv' in item.filename:
                    total += 1
                    if item.file is not None:
                        if item.standardized:
                            checksum = get_digest(item.file.path)
                            with open(item.file.path, "r", encoding='utf-8', errors='ignore') as file:
                                reader = csv.reader(file)
                                for row in reader:
                                    for field in row:
                                        if 'datasets/' in field:
                                            found_ids += 1
                                            if '"' in field:
                                                mk1 = field.find('"') + 1
                                                mk2 = field.rfind('"', mk1)
                                                sub = field[mk1: mk2]
                                                if 'ref' in sub:
                                                    q = sub.rfind('"') + 1
                                                    code = sub[q:len(sub)]
                                                    if 'datasets' in code:
                                                        if code.startswith('/'):
                                                            code = code[1:]
                                                        if len(code) > 0:
                                                            substrings = code.split('/')
                                                            org_code = substrings[2]
                                                            org_path = '/'.join(substrings[2:len(substrings) - 1])
                                                            dataset_code = substrings[-1]
                                                            if dataset_code[0].islower():
                                                                add_org_mapping(org_id, org_code, org_title)
                                                                add_dataset_mapping(
                                                                    dataset_id, code, dataset.lt_title(),
                                                                    org_title, checksum, False)
                                                                dump_current(file, org_path, manifest_path,
                                                                             dataset_code)
                                                else:
                                                    code = field[mk1: mk2]
                                                    if code.startswith('/'):
                                                        code = code[1:]
                                                    elif '""' in code:
                                                        st = code.find('"/')
                                                        fin = code.rfind('""')
                                                        code = code[st: fin].replace('"/', '')
                                                    if len(code) > 0:
                                                        if 'datasets' in code:
                                                            substrings = code.split('/')
                                                            org_code = substrings[2]
                                                            org_path = '/'.join(substrings[2:len(substrings) - 1])
                                                            dataset_code = substrings[-1]
                                                            if dataset_code[0].islower():
                                                                add_org_mapping(org_id, org_code, org_title)
                                                                add_dataset_mapping(dataset_id, code,
                                                                                    dataset.lt_title(), org_title,
                                                                                    checksum, False)
                                                                dump_current(file, org_path, manifest_path,
                                                                             dataset_code)
                                            else:
                                                sub = field.find('datasets/')
                                                if ';' in field:
                                                    if field.startswith(';;;;;'):
                                                        field = field[sub:]
                                                        fin = field.find(';')
                                                        field = field[:fin]
                                                    elif field.startswith(';'):
                                                        field = field[1:]
                                                        fin = field.find(';')
                                                        field = field[:fin]
                                                if field.startswith('/'):
                                                    field = field[1:]
                                                elif field.startswith('https') or field.startswith('http'):
                                                    fin = ':format'
                                                    field = field[sub:]
                                                    if fin in field:
                                                        field = field[:field.rfind(fin) - 1]
                                                if len(field) > 0:
                                                    if ';' in field:
                                                        field = field.replace(';', '')
                                                    if field.startswith('1'):
                                                        field = field[1:]
                                                    if 'ref: ' in field:
                                                        field = field.replace('ref: ', '')
                                                    substrings = field.split('/')
                                                    if len(substrings) > 2:
                                                        org_code = substrings[2]
                                                        org_path = '/'.join(substrings[2:len(substrings) - 1])
                                                    dataset_code = substrings[-1]
                                                    add_org_mapping(org_id, org_code, org_title)
                                                    if dataset_code[0].islower():
                                                        add_dataset_mapping(dataset_id, field, dataset.lt_title(),
                                                                            org_title, checksum, False)
                                                        dump_current(file, org_path, manifest_path, dataset_code)
                elif 'xls' in item.filename or 'xlsx' in item.filename:
                    if item.file is not None:
                        checksum = get_digest(item.file.path)
                        if item.standardized:
                            dataframe1 = pd.read_excel(item.file.path)
                            if 'dataset' in dataframe1:
                                for i in range(0, len(dataframe1)):
                                    code = dataframe1.iloc[i]['dataset']
                                    if isinstance(code, str):
                                        found_ids += 1
                                        if '/' in code:
                                            if len(code.split('/')) > 2:
                                                org_code = code.split('/')[2]
                                                org_path = '/'.join(code.split('/')[2:len(code.split('/')) - 1])
                                                add_org_mapping(org_id, org_code, org_title)
                                            dataset_code = code.split('/')[-1]
                                            if len(dataset_code) > 0:
                                                if dataset_code[0].islower():
                                                    add_dataset_mapping(dataset_id, code, dataset.lt_title(), org_title,
                                                                        checksum, False)
                                                    with open(item.file.path, "r", encoding='utf-8') as file:
                                                        dump_current(file, org_path, manifest_path, dataset_code)
                    total_xls += 1
                else:
                    total_not_csv += 1
            pbar.update(1)

    dump_orgs(organization_entries, manifest_path)
    dump_datasets(dataset_entries, manifest_path)

    for root, dirs, files in os.walk(manifest_path + 'datasets/gov/'):
        for filename in files:
            if '.csv' in filename:
                repo_files.append(os.path.join(root, filename))

    pbar2 = tqdm("Reading repository information", total=len(repo_files))
    with (pbar2):
        df = pd.read_csv(manifest_path + 'datasets.csv', index_col='name')
        for repo_item in repo_files:
            checksum = get_digest(repo_item)
            with open(repo_item, "r", encoding='utf-8') as f:
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


def get_digest(file_path):
    h = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(h.block_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def add_dataset_mapping(dataset_id, name, title, org, checksum, repo):
    if repo:
        dataset_id = None
        target = repository_dataset_entries
    else:
        target = dataset_entries
    mapping = DatasetStructureMapping(
        dataset_id=dataset_id,
        name=name,
        title=title,
        org=org,
        checksum=checksum
    )
    target.append(mapping)


def add_org_mapping(org_id, name, title):
    mapping = OrganizationMapping(
        org_id=org_id,
        name=name,
        title=title
    )
    if not any(obj.org_id == org_id for obj in organization_entries):
        organization_entries.append(mapping)


def dump_orgs(data, manifest_path):
    path = manifest_path + 'orgs.csv'
    columns = ['id', 'name', 'title']
    lst = [[x.org_id, x.name, x.title] for x in data]
    df = pd.DataFrame(lst)
    if not os.path.isfile(path):
        print(f"Dumping {len(data)} organization entries to orgs.csv")
        df.to_csv(path, index=False, header=columns, quoting=csv.QUOTE_ALL)
    else:
        print("File orgs.csv already exists, updating existing values...")
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
    path = manifest_path + 'datasets.csv'
    columns = ['id', 'name', 'title', 'org', 'checksum']
    lst = [[x.dataset_id, x.name, x.title, x.org, x.checksum] for x in data]
    df = pd.DataFrame(lst)
    if not os.path.isfile(path):
        print(f"Dumping {len(data)} dataset entries to datasets.csv")
        df.to_csv(path, index=False, header=columns, quoting=csv.QUOTE_ALL)
    else:
        print("File datasets.csv already exists, updating existing values...")
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
    path = manifest_path + 'datasets.csv'
    dff = pd.DataFrame(data)
    dff.to_csv(path, mode='a', index=False, header=False, quoting=csv.QUOTE_ALL)


def dump_current(file, org_path, manifest_path, dataset):
    unknown_index = 0
    original_ext = '.' + file.name.split('.')[-1]
    parent_dir = manifest_path + 'datasets/gov/'
    if len(org_path) == 0:
        org_path = 'unknown/'
    if not org_path.endswith('/'):
        org_path = org_path + "/"
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
