import pytest
from django_webtest import DjangoTestApp
from django.contrib.redirects.models import Redirect
from vitrina.users.models import User


@pytest.mark.django_db
def test_redirection_doesnt_exist(app: DjangoTestApp):
    response = app.get('/neegzistuoja/', expect_errors=True)
    assert response.status_code == 404


@pytest.mark.django_db
def test_redirection_exists_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
        new_path='/labas_naujas/',
    )
    response = app.get('/labas/')
    assert response.status_code == 301


@pytest.mark.django_db
def test_redirection_exists_no_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
    )
    response = app.get('/labas/', expect_errors=True)
    assert response.status_code == 410

@pytest.mark.django_db
def test_dataset_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/dataset/',
        new_path='/datasets/',
    )
    response = app.get('/dataset/')
    assert response.status_code == 301 and response.location == '/datasets/'

@pytest.mark.django_db
def test_usecases_examples_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/usecases/examples/',
        new_path='/projects/',
    )
    response = app.get('/usecases/examples/')
    assert response.status_code == 301 and response.location == '/projects/'

@pytest.mark.django_db
def test_usecases_applications_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/usecases/applications/',
        new_path='/projects/',
    )
    response = app.get('/usecases/applications/')
    assert response.status_code == 301 and response.location == '/projects/'

@pytest.mark.django_db
def test_usecase_has_new_path(app: DjangoTestApp):
    user1 = User.objects.create_user(email='user1@test.com', password='12345')
    app.set_user(user1)
    Redirect.objects.create(
        site_id=1,
        old_path='/usecase/',
        new_path='/projects/add/',
    )   
    response = app.get('/usecase/')
    assert response.status_code == 301 and response.location == '/projects/add/'

@pytest.mark.django_db
def test_policy_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/regulation/',
        new_path='/more/regulation/',
    )
    response = app.get('/page/regulation/')
    assert response.status_code == 301 and response.location == '/more/regulation/'


@pytest.mark.django_db
def test_links_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/nuorodos/',
        new_path='/more/nuorodos/',
    ) 
    response = app.get('/page/nuorodos/')
    assert response.status_code == 301 and response.location == '/more/nuorodos/'

@pytest.mark.django_db
def test_notions_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/savokos/',
        new_path='/more/savokos/',
    ) 
    response = app.get('/page/savokos/')
    assert response.status_code == 301 and response.location == '/more/savokos/'

@pytest.mark.django_db
def test_about_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/apie/',
        new_path='/more/apie/',
    ) 
    response = app.get('/page/apie/')
    assert response.status_code == 301 and response.location == '/more/apie/'

@pytest.mark.django_db
def test_contacts_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/contacts/',
        new_path='/more/contacts/',
    ) 
    response = app.get('/page/contacts/')
    assert response.status_code == 301 and response.location == '/more/contacts/'

@pytest.mark.django_db
def test_templates_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/templates/',
        new_path='/more/templates/',
    )    
    response = app.get('/page/templates/')
    assert response.status_code == 301 and response.location == '/more/templates/'

@pytest.mark.django_db
def test_storage_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/saugykla/',
        new_path='/opening-tips/saugykla/',
    )
    response = app.get('/page/saugykla/')
    assert response.status_code == 301 and response.location == '/opening-tips/saugykla/'

@pytest.mark.django_db
def test_guide_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/vadovas/',
        new_path='/opening-tips/vadovas/',
    )
    response = app.get('/page/vadovas/')
    assert response.status_code == 301 and response.location == '/opening-tips/vadovas/'

@pytest.mark.django_db
def test_summary_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/aprasas/',
        new_path='/opening-tips/aprasas/',
    )
    response = app.get('/page/aprasas/')
    assert response.status_code == 301 and response.location == '/opening-tips/aprasas/'

@pytest.mark.django_db
def test_data_opening_tools_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/data-opening-tools/',
        new_path='/opening-tips/data-opening-tools/',
    )
    response = app.get('/page/data-opening-tools/')
    assert response.status_code == 301 and response.location == '/opening-tips/data-opening-tools/'

@pytest.mark.django_db
def test_learning_material_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/opening/learningmaterial/',
        new_path='/opening-tips/opening/learningmaterial/',
    )
    response = app.get('/opening/learningmaterial/')
    assert response.status_code == 301 and response.location == '/opening-tips/opening/learningmaterial/'

@pytest.mark.django_db
def test_faq_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/opening_faq/',
        new_path='/opening-tips/opening_faq/',
    )
    response = app.get('/page/opening_faq/')
    assert response.status_code == 301 and response.location == '/opening-tips/opening_faq/'