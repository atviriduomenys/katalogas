import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

from tqdm import tqdm
from typer import run, Option
from filer.models import Image, File, Folder
from django.core.files import File as DjangoFile
from vitrina.cms.models import FileResource
from vitrina.datasets.models import DatasetStructure
from vitrina.resources.models import DatasetDistribution

IMAGE_TYPE = 0
FILE_TYPE = 1


def create_folders(path: str):
    path = os.path.normpath(path)
    root_folder_name = os.path.basename(path)
    root_folder = None
    for root, dirs, files in os.walk(path):
        rel_folders = root.partition(path)[2].strip(os.path.sep).split(os.path.sep)
        while '' in rel_folders:
            rel_folders.remove('')
        folder_names = [root_folder_name] + rel_folders
        current_parent = None
        for folder_name in folder_names:
            if not Folder.objects.filter(name=folder_name):
                current_parent = Folder.objects.create(name=folder_name, parent=current_parent)
            else:
                current_parent = Folder.objects.filter(name=folder_name).first()
            if folder_name == root_folder_name:
                root_folder = current_parent
    return root_folder


def migrate_distribution_files(pbar, root_path, folder):
    for distribution in DatasetDistribution.objects.filter(
        filename__isnull=False,
        identifier__isnull=False
    ):
        file_path = os.path.join(root_path, distribution.identifier)
        if os.path.exists(file_path):
            dj_file = DjangoFile(
                open(file_path, mode='rb'),
                name=distribution.filename
            )
            file, created = File.objects.get_or_create(
                file=dj_file,
                original_filename=distribution.filename,
                folder=folder
            )
            distribution.file = file
            distribution.save(update_fields=['file'])
        else:
            print(f'File with path "{file_path}" was not found')
        pbar.update(1)


def migrate_structure_files(pbar, root_path, folder):
    for structure in DatasetStructure.objects.filter(
            filename__isnull=False,
            identifier__isnull=False
    ):
        file_path = os.path.join(root_path, structure.identifier)
        if os.path.exists(file_path):
            dj_file = DjangoFile(
                open(file_path, mode='rb'),
                name=structure.filename
            )
            file, created = File.objects.get_or_create(
                file=dj_file,
                original_filename=structure.filename,
                folder=folder
            )
            structure.file = file
            structure.save(update_fields=['file'])
        else:
            print(f'File with path "{file_path}" was not found')
        pbar.update(1)


def migrate_cms_files(pbar, root_path, folder):
    for resource in FileResource.objects.filter(
            filename__isnull=False,
            identifier__isnull=False
    ):
        obj = resource.content_object
        file_path = os.path.join(root_path, resource.identifier)
        if os.path.exists(file_path):
            dj_file = DjangoFile(
                open(file_path, mode='rb'),
                name=resource.filename
            )
            if resource.type == IMAGE_TYPE:
                image, created = Image.objects.get_or_create(
                    file=dj_file,
                    original_filename=resource.filename,
                    folder=folder
                )
                obj.image = image
                obj.save(update_fields=['image'])

                # since images are already saved in object's image field,
                # we don't need to have them in FileResource table anymore
                resource.delete()
            else:
                file, created = File.objects.get_or_create(
                    file=dj_file,
                    original_filename=resource.filename,
                    folder=folder
                )
                resource.file = file
                resource.save(update_fields=['file'])
        else:
            print(f'File with path "{file_path}" was not found')
        pbar.update(1)


def main(
    distribution_path: str = Option("data/", help=(
        "Path to where dataset distribution files are saved"
    )),
    cms_path: str = Option("data/files/", help=(
        "Path to where news and CMS page files are saved"
    )),
    structure_path: str = Option("data/structure/", help=(
        "Path to where dataset structure files are saved"
    )),
):
    """
    Migrate files to Filer.
    """

    pbar = tqdm("Migrating files", total=(
        FileResource.objects.filter(
            filename__isnull=False,
            identifier__isnull=False
        ).count() +
        DatasetDistribution.objects.filter(
            filename__isnull=False,
            identifier__isnull=False
        ).count() +
        DatasetStructure.objects.filter(
            filename__isnull=False,
            identifier__isnull=False
        ).count()
    ))

    distribution_folder = create_folders(distribution_path)
    cms_folder = create_folders(cms_path)
    structure_folder = create_folders(structure_path)

    with pbar:
        migrate_distribution_files(pbar, distribution_path, distribution_folder)
        migrate_cms_files(pbar, cms_path, cms_folder)
        migrate_structure_files(pbar, structure_path, structure_folder)


if __name__ == '__main__':
    run(main)
