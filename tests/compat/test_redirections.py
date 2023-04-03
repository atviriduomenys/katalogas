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
def test_redirect_dataset_search_query_with_old_params(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/datasets?q=&category_id=30',
        new_path='/datasets/?selected_facets=parent_category_exact%3A1&q=',
    )
    response = app.get('/datasets?q=&category_id=30').follow()
    assert response.status_code == 301 and response.location == '?selected_facets=parent_category_exact%3A30&q='

@pytest.mark.django_db
def test_redirect_dataset_search_query_with_multiple_old_params(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/datasets?q=&category_id=30&category_id=31&category_id=32',
        new_path='/datasets/?selected_facets=parent_category_exact%3A30&selected_facets=category_exact%3A31&selected_facets=category_exact%3A32&q=',
    )
    response = app.get('/datasets?q=&category_id=30&category_id=31&category_id=32').follow()
    assert response.status_code == 301 and response.location == '?selected_facets=parent_category_exact%3A30&selected_facets=category_exact%3A31&selected_facets=category_exact%3A32&q='

@pytest.mark.django_db
def test_redirect_dataset_search_query_with_multiple_different_old_params(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/datasets?q=&category_id=30&category_id=31&format=XML&format=JSON',
        new_path='/datasets/?selected_facets=parent_category_exact%3A30&selected_facets=category_exact%3A31&selected_facets=f_exact%3AXML&selected_facets=o_exact%3AJSON&q=',
    )
    response = app.get('/datasets?q=&category_id=30&category_id=31&format=XML&format=JSON').follow()
    assert response.status_code == 301 and response.location == '?selected_facets=parent_category_exact%3A30&selected_facets=category_exact%3A31&selected_facets=f_exact%3AXML&selected_facets=o_exact%3AJSON&q='

@pytest.mark.django_db
def test_redirect_dataset_search_query_with_unchanged_params(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/datasets?q=&category_id=224&category_id=181&date_from=2016-01-03&date_to=2023-04-29',
        new_path='/datasets/?selected_facets=parent_category_exact%3A224&selected_facets=category_exact%3A181&q=&date_from=2016-01-03&date_to=2023-04-29',
    )
    response = app.get('/datasets?q=&category_id=224&category_id=181&date_from=2016-01-03&date_to=2023-04-29').follow()
    assert response.status_code == 301 and response.location == '?selected_facets=parent_category_exact%3A224&selected_facets=category_exact%3A181&q=&date_from=2016-01-03&date_to=2023-04-29'

@pytest.mark.django_db
def test_redirect_with_all_different_changed_params(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/datasets?q=&organization_id=1&category_id=1&data_status=4&format=A&tags=B&updated=kasmet',
        new_path='/datasets/?selected_facets=f_exact%3A4&selected_facets=parent_category_exact%3A1&selected_facets=o_exact%3A1&selected_facets=t_exact%3AB&selected_facets=f_exact%3AA&selected_facets=f_exact%3Akasmet',
    )
    response = app.get('/datasets?q=&organization_id=1&category_id=1&data_status=4&format=A&tags=B&updated=kasmet').follow()
    assert response.status_code == 301 and response.location == '?selected_facets=f_exact%3A4&selected_facets=parent_category_exact%3A1&selected_facets=o_exact%3A1&selected_facets=t_exact%3AB&selected_facets=f_exact%3AA&selected_facets=f_exact%3Akasmet&q='

@pytest.mark.django_db
def test_dataset_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/dataset/1/',
        new_path='/datasets/1/',
    )
    response = app.get('/dataset/1/')
    assert response.status_code == 301 and response.location == '/datasets/1/'

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
        old_path='/page/regulation',
        new_path='/more/regulation/',
    )
    response = app.get('/page/regulation/')
    assert response.status_code == 301 and response.location == '/more/regulation/'


@pytest.mark.django_db
def test_links_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/nuorodos',
        new_path='/more/nuorodos/',
    )
    response = app.get('/page/nuorodos/')
    assert response.status_code == 301 and response.location == '/more/nuorodos/'

@pytest.mark.django_db
def test_notions_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/savokos',
        new_path='/more/savokos/',
    )
    response = app.get('/page/savokos/')
    assert response.status_code == 301 and response.location == '/more/savokos/'

@pytest.mark.django_db
def test_about_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/apie',
        new_path='/more/apie/',
    )
    response = app.get('/page/apie/')
    assert response.status_code == 301 and response.location == '/more/apie/'

@pytest.mark.django_db
def test_contacts_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/contacts',
        new_path='/more/contacts/',
    )
    response = app.get('/page/contacts/')
    assert response.status_code == 301 and response.location == '/more/contacts/'

@pytest.mark.django_db
def test_other_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/other',
        new_path='/more/other/',
    )
    response = app.get('/other/')
    assert response.status_code == 301 and response.location == '/more/other/'

@pytest.mark.django_db
def test_reports_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/reports',
        new_path='/more/reports/',
    )
    response = app.get('/reports/')
    assert response.status_code == 301 and response.location == '/more/reports/'

@pytest.mark.django_db
def test_templates_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/templates',
        new_path='/more/templates/',
    )
    response = app.get('/page/templates/')
    assert response.status_code == 301 and response.location == '/more/templates/'

@pytest.mark.django_db
def test_storage_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/saugykla',
        new_path='/opening-tips/saugykla/',
    )
    response = app.get('/page/saugykla/')
    assert response.status_code == 301 and response.location == '/opening-tips/saugykla/'

@pytest.mark.django_db
def test_guide_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/vadovas',
        new_path='/opening-tips/vadovas/',
    )
    response = app.get('/page/vadovas/')
    assert response.status_code == 301 and response.location == '/opening-tips/vadovas/'

@pytest.mark.django_db
def test_guide_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/vadovas',
        new_path='/opening-tips/vadovas/',
    )
    response = app.get('/page/vadovas/')
    assert response.status_code == 301 and response.location == '/opening-tips/vadovas/'

@pytest.mark.django_db
def test_summary_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/aprasas',
        new_path='/opening-tips/aprasas/',
    )
    response = app.get('/page/aprasas/')
    assert response.status_code == 301 and response.location == '/opening-tips/aprasas/'

@pytest.mark.django_db
def test_data_opening_tools_have_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/data-opening-tools',
        new_path='/opening-tips/data-opening-tools/',
    )
    response = app.get('/page/data-opening-tools/')
    assert response.status_code == 301 and response.location == '/opening-tips/data-opening-tools/'

@pytest.mark.django_db
def test_learning_material_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/opening/learningmaterial',
        new_path='/opening-tips/opening/learningmaterial/',
    )
    response = app.get('/opening/learningmaterial/')
    assert response.status_code == 301 and response.location == '/opening-tips/opening/learningmaterial/'

@pytest.mark.django_db
def test_faq_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/page/opening_faq',
        new_path='/opening-tips/opening_faq/',
    )
    response = app.get('/page/opening_faq/')
    assert response.status_code == 301 and response.location == '/opening-tips/opening_faq/'