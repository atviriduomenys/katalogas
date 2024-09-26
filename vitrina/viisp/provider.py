from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.signals import social_account_added
import bcrypt



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
        personal_code_bytes = data.get('personal_code').encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(personal_code_bytes, salt) 
        return dict(
            personal_code=hash.decode('utf-8'),
            coordinator_phone_number=data.get("phone"),
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
        email_addresses = self.extract_email_addresses(response)
        self.cleanup_email_addresses(common_fields.get("email"), email_addresses)
        socialaccount = SocialAccount(extra_data=extra_data, uid=uid, provider=self.id)
        
        user = User.objects.filter(email=extra_data.get('coordinator_email')).first()
        if user:
            existing_social_account = SocialAccount.objects.filter(user=user).first()
            if existing_social_account:
                socialaccount = existing_social_account
            
        sociallogin = SocialLogin(
            account=socialaccount, email_addresses=email_addresses
        )
        if user and not existing_social_account:
            sociallogin.connect(request, user)
            social_account_added.send(
                sender=SocialLogin, request=request, sociallogin=sociallogin
            )
        else:
            user = sociallogin.user = adapter.new_user(request, sociallogin)
            user.status = User.ACTIVE
            user.set_unusable_password()
            adapter.populate_user(request, sociallogin, common_fields)
        return sociallogin


provider_classes = [VIISPProvider]
providers.registry.register(VIISPProvider)
