from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class VIISPAccount(ProviderAccount):
    def to_str(self):
        dflt = super(VIISPAccount, self).to_str()
        return dflt


class VIISPProvider(OAuth2Provider):
    id = 'viisp'
    name = 'Viisp'
    account_class = VIISPAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        from pprint import pprint
        return dict(username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],)

    def get_default_scope(self):
        scope = ['read']
        return scope



provider_classes = [VIISPProvider]
providers.registry.register(VIISPProvider)
