from unittest.mock import Mock, patch

from django.test import RequestFactory

from vitrina.middleware import AutoRevisionCommentMiddleware
from vitrina.utils import RevisionComment, RevisionSource


def test_noop_when_reversion_not_active(rf: RequestFactory):
    middleware = AutoRevisionCommentMiddleware(get_response=lambda r: None)
    with (
        patch("vitrina.middleware.reversion.is_active", return_value=False),
        patch("vitrina.middleware.reversion.set_comment") as set_comment_mock,
    ):
        middleware.process_view(rf.post(""), view_func=lambda r: None, view_args=[], view_kwargs={})

    set_comment_mock.assert_not_called()


def test_noop_when_comment_already_set(rf: RequestFactory):
    middleware = AutoRevisionCommentMiddleware(get_response=lambda r: None)
    with (
        patch("vitrina.middleware.reversion.is_active", return_value=True),
        patch("vitrina.middleware.reversion.get_comment", return_value="test"),
        patch("vitrina.middleware.reversion.set_comment") as set_comment_mock,
    ):
        middleware.process_view(rf.post(""), view_func=lambda r: None, view_args=[], view_kwargs={})

    set_comment_mock.assert_not_called()


def test_noop_for_admin_view(rf: RequestFactory):
    def admin_view(request):
        return None

    admin_view.model_admin = object()

    middleware = AutoRevisionCommentMiddleware(get_response=lambda r: None)
    with (
        patch("vitrina.middleware.reversion.is_active", return_value=True),
        patch("vitrina.middleware.reversion.get_comment", return_value=None),
        patch("vitrina.middleware.reversion.set_comment") as set_comment_mock,
    ):
        middleware.process_view(rf.post(""), view_func=admin_view, view_args=[], view_kwargs={})

    set_comment_mock.assert_not_called()


def test_sets_comment(rf: RequestFactory):
    request = rf.post("/test/path")
    request.resolver_match = Mock(url_name="test-view")
    middleware = AutoRevisionCommentMiddleware(get_response=lambda r: None)
    view_args = [123]
    view_kwargs = {"a": "b"}

    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="test-view",
        http_method=request.method,
        path=request.path,
        args=view_args,
        kwargs=view_kwargs,
    )

    with (
        patch("vitrina.middleware.reversion.is_active", return_value=True),
        patch("vitrina.middleware.reversion.get_comment", return_value=None),
        patch("vitrina.middleware.reversion.set_comment") as set_comment_mock,
    ):
        middleware.process_view(request, view_func=lambda r: None, view_args=view_args, view_kwargs=view_kwargs)

    set_comment_mock.assert_called_once()
    (comment_json,) = set_comment_mock.call_args.args

    assert comment_json == revision_comment.to_json()
