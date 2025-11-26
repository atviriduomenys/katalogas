import pytest
from vitrina.viisp.forms import FakeViispForm
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_fake_viisp_form_valid_email():
    user = UserFactory(email="valid@test.com")
    user.set_password("test")
    user.save()
    form = FakeViispForm(data={"username": user.email, "password": "test"})
    assert form.is_valid()


@pytest.mark.django_db
def test_fake_viisp_form_invalid_email():
    form = FakeViispForm(data={"username": "not.existing@test.com", "password": "abc"})
    assert not form.is_valid()
    assert "Įveskite teisingą Elektroninis paštas ir slaptažodį. Abiejuose laukuose didžiosios mažosios raidės skiriasi." in form.errors["__all__"]
