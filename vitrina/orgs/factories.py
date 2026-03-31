import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from vitrina.orgs.models import Organization, Representative, WhitelistedCodeName
from vitrina.users.factories import UserFactory


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = (
            "title",
            "kind",
            "name",
            "company_code",
            "email",
            "phone",
            "address",
        )

    title = factory.Faker("company")
    kind = factory.Faker("word")
    name = factory.Sequence(lambda n: f"datasets/gov/test/{n:04d}/")
    company_code = factory.Faker("bothify", text="?????????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    email = factory.Faker("email")
    phone = Faker().phone_number()
    address = Faker().address()
    is_public = True
    version = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if not kwargs.get("created"):
            kwargs["created"] = timezone.now()
        return model_class.add_root(**kwargs)

    @factory.post_generation
    def whitelisted_names(self, create: bool, extracted: list[str] | None, **kwargs) -> None:
        if not create:
            return
        if extracted:
            for name in extracted:
                WhitelistedCodeNameFactory(organization=self, code_name=name)
        else:
            WhitelistedCodeNameFactory(organization=self, code_name="datasets/gov/ivpk/")


class RepresentativeFactory(DjangoModelFactory):
    class Meta:
        model = Representative
        django_get_or_create = ("first_name", "last_name", "email", "phone")

    organization = None
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = factory.Sequence(lambda n: "+3706%07d" % n)
    version = 1
    role = Representative.OPEN_DATA_COORDINATOR
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name}.{obj.last_name}@gmail.com")
    user = factory.SubFactory(
        UserFactory,
        first_name=factory.SelfAttribute("..first_name"),
        last_name=factory.SelfAttribute("..last_name"),
        phone=factory.SelfAttribute("..phone"),
        email=factory.SelfAttribute("..email"),
    )


class ViispRepresentativeFactory(RepresentativeFactory):
    user = factory.SubFactory(
        UserFactory,
        first_name=factory.SelfAttribute("..first_name"),
        last_name=factory.SelfAttribute("..last_name"),
        phone=factory.SelfAttribute("..phone"),
        email=factory.SelfAttribute("..email"),
        is_viisp_login=True,
        viisp_company_code=factory.SelfAttribute("..content_object.company_code"),
    )
    content_object = factory.SubFactory(OrganizationFactory)


class WhitelistedCodeNameFactory(DjangoModelFactory):
    class Meta:
        django_get_or_create = ("code_name",)
        model = WhitelistedCodeName

    organization = factory.SubFactory(OrganizationFactory)
    code_name = factory.Sequence(lambda n: f"datasets/gov/test/{n:04d}/")
