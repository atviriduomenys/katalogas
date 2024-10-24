from importlib import import_module

import pytest
from django.apps import apps
from django.db import connection
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.users.models import User, UserEmailDevice

data_migration = import_module('vitrina.users.migrations.0004_auto_20220909_1301')


@pytest.mark.django_db
def test_fix_user_passwords(app: DjangoTestApp):
    user = User.objects.create(
        email="user@test.com",
        password="$2a$12$k8fGchaf72fh8PO1g/HOI.EMw29jC8pPJoSfFXq1v2nJRo9ELSvPm"
    )

    # try to log in with unchanged password
    form = app.get(reverse('login')).forms['login-form']
    form['username'] = "user@test.com"
    form['password'] = "test"
    resp = form.submit()
    assert len(resp.context['form'].errors) == 1

    data_migration.fix_passwords(apps, connection.schema_editor())

    user.refresh_from_db()
    assert user.password == "bcrypt$$2a$12$k8fGchaf72fh8PO1g/HOI.EMw29jC8pPJoSfFXq1v2nJRo9ELSvPm"

    # try to log in again
    form = app.get(reverse('login')).forms['login-form']
    form['username'] = "user@test.com"
    form['password'] = "test"
    resp = form.submit(name="otp_challenge")
    form = resp.forms['login-form']
    form['otp_token'] = UserEmailDevice.objects.filter(user=user).first().token
    resp = form.submit()
    assert resp.status_code == 302
    assert resp.url == reverse('home')


