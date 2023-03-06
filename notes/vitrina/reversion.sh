# 2022-10-19 14:19 Fix history migrations

poetry run python manage.py shell
from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from vitrina.requests.models import Request
from vitrina.requests.models import RequestEvent
from reversion.models import Revision
from reversion.models import Version
for request in Request.objects.values('id').annotate(events=Count('id')).filter(events=1):
    content_type = ContentType.objects.get_for_model(Request)
    request = Request.objects.get(id=request['id'])
    revision = Revision.objects.create(
        date_created=request.created,
        comment="CREATED",
        user=request.user,
    )
    Version.objects.create(
        object_id=request.id,
        content_type=content_type,
        object_repr=str(request),
        format="json",
        db="default",
        revision=revision,
    )
exit()


poetry run python manage.py shell
from django.contrib.contenttypes.models import ContentType
from vitrina.projects.models import Project
from reversion.models import Revision
from reversion.models import Version
for project in Project.objects.all():
    content_type = ContentType.objects.get_for_model(Project)
    revision = Revision.objects.create(
        date_created=project.created,
        comment="CREATED",
        user=project.user,
    )
    Version.objects.create(
        object_id=project.id,
        content_type=content_type,
        object_repr=str(project),
        format="json",
        db="default",
        revision=revision,
    )
exit()

poetry run python manage.py runserver

poetry run python manage.py makemigrations vitrina_projects --empty
