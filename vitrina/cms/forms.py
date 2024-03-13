import datetime

from django import forms

from django.utils.translation import gettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLFormField

from vitrina.cms.models import LearningMaterial, Faq, ExternalSite
from vitrina.orgs.models import PublishedReport


class LearningMaterialAdminForm(forms.ModelForm):
    author_name = forms.CharField(label=_("Autorius"), required=False)
    topic = forms.CharField(label=_("Pavadinimas"))
    description = HTMLFormField(label=_("Aprašymas"))

    class Meta:
        model = LearningMaterial
        fields = ('published', 'author_name', 'topic', 'description', 'summary', 'image', 'video_url',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        if not instance:
            self.initial['published'] = datetime.date.today()


class FaqAdminForm(forms.ModelForm):
    question = forms.CharField(label=_("Klausimas"), widget=forms.Textarea)
    answer = forms.CharField(label=_("Atsakymas"), widget=forms.Textarea)

    class Meta:
        model = Faq
        fields = ('question', 'answer',)


class ExternalSiteAdminForm(forms.ModelForm):
    title = forms.CharField(label=_("Pavadinimas"))
    type = forms.ChoiceField(label=_("Tipas"), choices=ExternalSite.TYPE_CHOICES)
    url = forms.CharField(label=_("Nuoroda"))

    class Meta:
        model = ExternalSite
        fields = ('title', 'type', 'url', 'image',)


class PublishedReportAdminForm(forms.ModelForm):
    title = forms.CharField(label=_("Pavadinimas"))
    data = forms.CharField(label=_("Duomenys"), widget=forms.Textarea)

    class Meta:
        model = PublishedReport
        fields = ('title', 'data',)

