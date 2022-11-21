from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class VIISPAccount(ProviderAccount):
    def to_str(self):
        dflt = super(VIISPAccount, self).to_str()
        return dflt


class VIISPProvider(OAuth2Provider):
    id = "viisp"
    name = "VIISP"
    account_class = VIISPAccount

    def extract_uid(self, data):
        return data['id']

    def get_fields(self):
        settings = self.get_settings()
        default_fields = [
            "id",
            "email",
            "firstName",
            "lastName",
            "phone",
            "companyName",
        ]
        return settings.get("FIELDS", default_fields)

    def extract_common_fields(self, data):
        return dict(email=data.get("email"), phone=data.get("phone"), companyName=data.get("companyName"),
                    firstName=data.get("firstName"), lastName=data.get("lastName"))

    def get_default_scope(self):
        return ["email", "identify"]


provider_classes = [VIISPProvider]
providers.registry.register(VIISPProvider)
