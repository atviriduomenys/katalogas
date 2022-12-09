import factory
from factory.django import DjangoModelFactory, FileField, ImageField
from filer.models import File, Image, Folder


class FolderFactory(DjangoModelFactory):
    class Meta:
        model = Folder
        django_get_or_create = ('name',)

    name = "data"


class FilerFileFactory(DjangoModelFactory):
    class Meta:
        model = File
        django_get_or_create = ('file',)

    file = FileField(filename='file.csv', data=b'Column\nValue')
    original_filename = "file.csv"
    folder = factory.SubFactory(FolderFactory)


class FilerImageFactory(DjangoModelFactory):
    class Meta:
        model = Image
        django_get_or_create = ('file',)

    file = ImageField(filename="image.png")
    original_filename = "image.png"
    folder = factory.SubFactory(FolderFactory)
