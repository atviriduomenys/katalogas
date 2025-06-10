from vitrina.orgs.forms import AgentForm


def test_success_agent_create_form():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": False,
        "open_data_publish_url": ""
    }
    form = AgentForm(data=form_data)
    assert form.is_valid()

def test_success_agent_create_form_open_data_publish_url_is_provided():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": True,
        "open_data_publish_url": "https://example.com"
    }
    form = AgentForm(data=form_data)
    assert form.is_valid()

def test_failure_agent_create_form_open_data_is_published_but_no_url_is_provided():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": True,
        "open_data_publish_url": ""
    }

    form = AgentForm(data=form_data)

    assert not form.is_valid()
    assert form.errors == {
        "open_data_publish_url": [
            "Šis laukas yra privalomas, jei nustatytas požymis \"Atviri duomenys publikuojami Saugykloje\"."
        ]
    }
