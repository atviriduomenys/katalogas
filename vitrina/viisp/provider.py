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

    def get_default_scope(self):
        scope = ['read']
        return scope



provider_classes = [VIISPProvider]
providers.registry.register(VIISPProvider)
