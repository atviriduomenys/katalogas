from django import forms
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Frequency
from vitrina.comments.models import Comment
from vitrina.requests.models import Request


PROJECT_STATUSES = (
    (None, _("---------")),
    (Comment.APPROVED, _("Patvirtintas")),
    (Comment.REJECTED, _("Atmestas"))
)


class CommentForm(forms.ModelForm):
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Comment
        fields = ('is_public', 'body',)

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if obj and isinstance(obj.__class__, ModelBase):
            self.auto_id = 'id_' + str(obj.pk)
            self.fields['body'].label = _("Komentaro tekstas objektui: ") + " " + str(obj)
            self.fields['body'].widget.attrs.update({'title': _("Komentaras"),
                                                     'id': 'id_' + 'body_' + str(obj.pk)})
            self.fields['is_public'].widget.attrs.update({'id': 'id_' + 'is_public_' + str(obj.pk)})
            self.obj = obj


class RegisterRequestForm(CommentForm):
    register_request = forms.BooleanField(label=_("Registruoti kaip prašymą"), required=False)

    class Meta(CommentForm.Meta):
        fields = ('is_public', 'register_request', 'body',)


class DatasetCommentForm(RegisterRequestForm):
    increase_frequency = forms.ModelChoiceField(
        label=_("Didinti duomenų atnaujinimo periodiškumą"),
        required=False,
        queryset=Frequency.objects.all(),
        to_field_name='title'
    )

    class Meta(CommentForm.Meta):
        fields = ('is_public', 'register_request', 'increase_frequency', 'body',)


class RequestCommentForm(CommentForm):
    status = forms.ChoiceField(choices=Request.STATUSES, required=False, label=_("Būsena"))

    class Meta(CommentForm.Meta):
        fields = ('is_public', 'status', 'body',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False

    def clean(self):
        body = self.cleaned_data.get('body')
        status = self.cleaned_data.get('status')
        if not status or (status and status == Comment.REJECTED):
            if not body:
                self.add_error('body', _("Šis laukas yra privalomas"))
        return self.cleaned_data


class ProjectCommentForm(CommentForm):
    status = forms.ChoiceField(choices=PROJECT_STATUSES, required=False, label=_("Būsena"))

    class Meta(CommentForm.Meta):
        fields = ('is_public', 'status', 'body',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False

    def clean(self):
        body = self.cleaned_data.get('body')
        status = self.cleaned_data.get('status')
        if not status and not body:
            self.add_error('body', _("Šis laukas yra privalomas"))
        if self.obj.status == status:
            self.add_error('body', _("Dabartinė būsena sutampa su jūsų pateikta"))
        return self.cleaned_data

