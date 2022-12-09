from factory.django import DjangoModelFactory, FileField, ImageField
from filer.models import File, Image


class FilerFileFactory(DjangoModelFactory):
    class Meta:
        model = File
        django_get_or_create = ('file',)

    file = FileField(filename='file.csv', data=b'Column\nValue')


class FilerImageFactory(DjangoModelFactory):
    class Meta:
        model = Image
        django_get_or_create = ('file',)

    file = ImageField(filename="image.png")
