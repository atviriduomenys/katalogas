import pytest
from django.utils.html import escape

from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan
from vitrina.requests.forms import PlanChoiceField

XSS_PAYLOAD = "<script>alert('xss')</script>"


@pytest.mark.django_db
class TestPlanChoiceFieldRequestsXSS:
    def test_label_from_instance_escapes_title(self):
        plan = PlanFactory(title=XSS_PAYLOAD)
        field = PlanChoiceField(queryset=Plan.objects.all())

        result = field.label_from_instance(plan)

        assert XSS_PAYLOAD not in str(result)
        assert escape(XSS_PAYLOAD) in str(result)
