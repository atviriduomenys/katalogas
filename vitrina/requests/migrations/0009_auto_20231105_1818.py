# Generated by Django 3.2.22 on 2023-11-05 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_requests', '0008_auto_20230906_0653'),
    ]

    def create_assignment_for_requests_with_org(apps, schema_editor):
        Request = apps.get_model("vitrina_requests", "Request")
        RequestAssignment = apps.get_model("vitrina_requests", "RequestAssignment")
        requests = Request.objects.all()
        for request in requests:
            if len(request.organizations.all()) > 0:
                for org in request.organizations.all():
                    request_assignment_exists = RequestAssignment.objects.filter(
                        organization=org,
                        request=request
                    ).first()
                    if not request_assignment_exists:
                        reqA = RequestAssignment.objects.create(
                            organization=org,
                            request=request,
                            status=request.status,
                            created=request.created
                        )
                        reqA.save()

    operations = [
        migrations.AddField(
            model_name='requestassignment',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.RunPython(create_assignment_for_requests_with_org),
    ]