import pytest
from vitrina.viisp.forms import FakeViispForm
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_fake_viisp_form_valid_email():
    user = UserFactory(email="valid@test.com")
    form = FakeViispForm(data={"email": user.email})
    assert form.is_valid()


@pytest.mark.django_db
def test_fake_viisp_form_invalid_email():
    # Email not in DB
    form = FakeViispForm(data={"email": "not.existing@test.com"})
    assert not form.is_valid()
    assert "Naudotojas su tokiu el. paštu nerastas." in form.errors["email"][0]
