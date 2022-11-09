from django import forms
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Frequency
from vitrina.comments.models import Comment


REQUEST_STATUSES = (
    (None, _("---------")),
    (Comment.OPENED, _("Atvertas")),
    (Comment.APPROVED, _("Patvirtintas")),
    (Comment.REJECTED, _("Atmestas"))
)


class CommentForm(forms.ModelForm):
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Comment
        fields = ('is_public', 'body',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].label = False


class DatasetCommentForm(CommentForm):
    register_request = forms.BooleanField(label=_("Registruoti kaip prašymą"), required=False)
    increase_frequency = forms.ModelChoiceField(
        label=_("Didinti duomenų atnaujinimo periodiškumą"),
        required=False,
        queryset=Frequency.objects.all(),
        to_field_name='title'
    )

    class Meta(CommentForm.Meta):
        fields = ('is_public', 'register_request', 'increase_frequency', 'body',)


class RequestCommentForm(CommentForm):
    status = forms.ChoiceField(choices=REQUEST_STATUSES, required=False, label=_("Būsena"))

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


