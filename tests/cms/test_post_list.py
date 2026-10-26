from types import SimpleNamespace

from django.template.loader import render_to_string


def test_post_list_uses_the_grouper_main_image():
    post_content = SimpleNamespace(
        title="Naujiena",
        abstract="Santrauka",
        post=SimpleNamespace(main_image=SimpleNamespace(url="/media/main.jpg")),
    )

    html = render_to_string(
        "vitrina/cms/post_list.html",
        {"postcontent_list": [post_content]},
    )

    assert 'src="/media/main.jpg"' in html
