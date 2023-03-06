# 2023-01-02 11:12 Create some tasks

poetry run python manage.py shell
from vitrina.tasks.models import Task
from vitrina.users.models import User 
from vitrina.orgs.models import Organization
user = User.objects.get(email='sirexas@gmail.com')
org = Organization.objects.get(title__startswith='Informacinės visuomenės')
Task.objects.create(title="Test task", user=user, organization=org)
exit()

poetry run python manage.py runserver
