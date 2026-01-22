import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import (
    LicenceFactory,
    FrequencyFactory,
    StatusFactory,
)
from vitrina.classifiers.models import Licence, Frequency, Status
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_default_licence(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    LicenceFactory(is_default=True)
    another_licence = LicenceFactory(is_default=False)
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_classifiers_licence_change', args=[another_licence.pk])).forms['licence_form']
    form['is_default'] = True
    form.submit()
    assert list(Licence.objects.filter(is_default=True)) == [another_licence]


@pytest.mark.django_db
def test_change_default_frequency(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    FrequencyFactory(is_default=True)
    another_frequency = FrequencyFactory(is_default=False)
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_classifiers_frequency_change',
                           args=[another_frequency.pk])).forms['frequency_form']
    form['is_default'] = True
    form.submit()
    assert list(Frequency.objects.filter(is_default=True)) == [another_frequency]


@pytest.mark.django_db
def test_change_default_status(app: DjangoTestApp):
    """
        Test that changing the default status via the Django admin form works correctly.

        This test verifies that when an existing status is updated to be the new default
        (`is_default=True`), the previous default status is automatically unset
        (`is_default=False`). It simulates an admin user modifying a status through
        the admin interface.

        Steps:
            - Create an admin user and two status instances (one default, one not).
            - Authenticate as the admin user.
            - Submit a change form to make the non-default status the new default.
            - Assert that the new default is updated correctly, and the old default is unset.

        Args:
            app (DjangoTestApp): A test app instance from `pytest-django` or `WebTest`
                configured to simulate requests to the Django app.
        """
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    default_status = StatusFactory(is_default=True)
    another_status = StatusFactory(is_default=False)
    app.set_user(admin)
    form = app.get(
        reverse("admin:vitrina_classifiers_status_change", args=[another_status.pk])
    ).forms["status_form"]
    form["is_default"] = True
    form["name"] = "Test"

    form.submit()

    assert Status.objects.filter(id=default_status.id).values_list("is_default", flat=True)[0] is False
    assert Status.objects.filter(id=another_status.id).values_list("is_default", flat=True)[0] is True
