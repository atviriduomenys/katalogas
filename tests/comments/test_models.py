import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape

from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.orgs.factories import OrganizationFactory
from vitrina.plans.factories import PlanFactory

XSS_PAYLOAD = "<script>alert('xss')</script>"


@pytest.mark.django_db
class TestCommentBodyTextXSS:
    def test_plan_body_text_escapes_plan_title(self):
        plan = PlanFactory(title=XSS_PAYLOAD)
        comment = CommentFactory(type=Comment.PLAN, rel_content_object=plan)

        result = comment.body_text()

        assert XSS_PAYLOAD not in str(result)
        assert escape(XSS_PAYLOAD) in str(result)

    def test_structure_body_text_escapes_content_object(self):
        org = OrganizationFactory(title=XSS_PAYLOAD)
        content_type = ContentType.objects.get_for_model(org)
        comment = CommentFactory(
            type=Comment.STRUCTURE,
            content_type=content_type,
            object_id=org.pk,
        )

        result = comment.body_text()

        assert XSS_PAYLOAD not in str(result)
        assert escape(XSS_PAYLOAD) in str(result)
