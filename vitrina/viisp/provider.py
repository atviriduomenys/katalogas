from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.signals import social_account_added



class VIISPAccount(ProviderAccount):
    pass


class VIISPProvider(OAuth2Provider):
    id = 'viisp'
    name = 'Viisp'
    account_class = VIISPAccount

    def extract_uid(self, data):
        return str(data['ticket_id'])

    def get_default_scope(self):
        return ["first_name", "last_name", "email", "phone"]

    def extract_common_fields(self, data):
        ret = {}
        if data.get("first_name"):
            ret["first_name"] = data.get("first_name")
        if data.get("last_name"):
            ret["last_name"] = data.get("last_name")
        if data.get("email"):
            ret["email"] = data.get("email")
        if data.get("phone_number"):
            ret["phone"] = data.get("phone_number")
        return ret

    def extract_extra_data(self, data):
        return dict(
            comapny_code=data.get("lt_company_Code"),
            company_name=data.get("company_name"),
            coordinator_phone_number=data.get("phone_number"),
            coordinator_email=data.get("email"),
            password_not_set=True
        )

    def sociallogin_from_response(self, request, response):
        # NOTE: Avoid loading models at top due to registry boot...
        from allauth.socialaccount.models import SocialAccount, SocialLogin
        from vitrina.users.models import User
        adapter = get_adapter(request)
        uid = self.extract_uid(response)
        extra_data = self.extract_extra_data(response)
        common_fields = self.extract_common_fields(response)
        socialaccount = SocialAccount(extra_data=extra_data, uid=uid, provider=self.id)
        email_addresses = self.extract_email_addresses(response)
        self.cleanup_email_addresses(common_fields.get("email"), email_addresses)
        sociallogin = SocialLogin(
            account=socialaccount, email_addresses=email_addresses
        )
        
        user = User.objects.filter(email=extra_data.get('coordinator_email')).first()
        if user:
            sociallogin.connect(request, user)
            social_account_added.send(
                sender=SocialLogin, request=request, sociallogin=sociallogin
            )
        else:
            user = sociallogin.user = adapter.new_user(request, sociallogin)
            user.set_unusable_password()
            adapter.populate_user(request, sociallogin, common_fields)
        return sociallogin

provider_classes = [VIISPProvider]
providers.registry.register(VIISPProvider)
