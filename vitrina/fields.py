from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms import TextInput, Field, FileField, ImageField, ClearableFileInput
from filer.models import Image, File, Folder


class MultipleValueWidget(TextInput):
    def value_from_datadict(self, data, files, name):
        return data.getlist(name)


class MultipleValueField(Field):
    widget = MultipleValueWidget


def clean_int(x):
    try:
        return int(x)
    except ValueError:
        raise ValidationError("Cannot convert to integer: {}".format(repr(x)))


class MultipleIntField(MultipleValueField):
    def clean(self, value):
        return [clean_int(x) for x in value]


class FilerClearableFileInput(ClearableFileInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value is not False and isinstance(value, int):
            value = File.objects.get(pk=value)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        context['widget'].update({
            'checkbox_name': checkbox_name,
            'checkbox_id': checkbox_id,
            'is_initial': self.is_initial(value),
            'input_text': self.input_text,
            'initial_text': self.initial_text,
            'clear_checkbox_label': self.clear_checkbox_label,
            'value': value,
        })
        return context


class FilerFieldMixin:
    filer_model = None

    def __init__(self, *, upload_to=None, **kwargs):
        self.upload_to = upload_to
        super().__init__(**kwargs)

    def clean(self, data, initial=None):
        file = super().clean(data, initial)

        # False means that field should be cleared
        if file is False:
            if initial and isinstance(initial, int):
                self.filer_model.objects.get(pk=initial).delete()
            return None

        # if file is int, that means it's already uploaded file,
        # and it points to filer's object id
        elif isinstance(file, int):
            file = self.filer_model.objects.get(pk=file)
        elif isinstance(file, UploadedFile):
            # if file was changed, clear the previous one
            if initial and isinstance(initial, int):
                self.filer_model.objects.get(pk=initial).delete()

            current_folder = None
            if self.upload_to:
                folders = self.upload_to.split('/')
                for level, folder_name in enumerate(folders):
                    current_folder, created = Folder.objects.get_or_create(
                        level=level,
                        name=folder_name,
                        parent=current_folder
                    )
            file = self.filer_model.objects.create(
                file=file,
                original_filename=file.name,
                folder=current_folder
            )
        return file


class FilerFileField(FilerFieldMixin, FileField):
    widget = FilerClearableFileInput
    filer_model = File


class FilerImageField(FilerFieldMixin, ImageField):
    widget = FilerClearableFileInput
    filer_model = Image
