import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import LicenceFactory, FrequencyFactory
from vitrina.classifiers.models import Licence, Frequency
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_default_licence(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    default_licence = LicenceFactory(is_default=True)
    another_licence = LicenceFactory(is_default=False)
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_classifiers_licence_change', args=[another_licence.pk])).forms['licence_form']
    form['is_default'] = True
    form.submit()
    assert list(Licence.objects.filter(is_default=True)) == [another_licence]


@pytest.mark.django_db
def test_change_default_frequency(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    default_frequency = FrequencyFactory(is_default=True)
    another_frequency = FrequencyFactory(is_default=False)
    app.set_user(admin)
    form = app.get(reverse('admin:vitrina_classifiers_frequency_change',
                           args=[another_frequency.pk])).forms['frequency_form']
    form['is_default'] = True
    form.submit()
    assert list(Frequency.objects.filter(is_default=True)) == [another_frequency]
