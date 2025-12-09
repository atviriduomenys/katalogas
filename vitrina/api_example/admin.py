from django.contrib import admin
from .models import ApiExample
from vitrina.admin import RevisionCommentVersionAdmin


@admin.register(ApiExample)
class ApiExampleAmin(RevisionCommentVersionAdmin):
    pass
