from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')

        if not uploaded_file.name.endswith(('.yaml', '.yml')):
            raise forms.ValidationError('Only YAML files are allowed.')

        return uploaded_file
