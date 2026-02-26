from django.views import View
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from vitrina.api.oauth import OAuthClientAuthenticator
from vitrina.uapi.models import AgentEnv


class IsAgentEnabled(BasePermission):
    message = "The agent is disabled. Enable the agent in the Data catalog to access this API."

    def has_permission(self, request: Request, view: View) -> bool:
        if not (oauth_client_id := OAuthClientAuthenticator.resolve_client_id_from_token(request.auth)):
            return False

        if AgentEnv.not_archived.filter(oauth_client_id=oauth_client_id, is_enabled=True).exists():
            return True

        return False
