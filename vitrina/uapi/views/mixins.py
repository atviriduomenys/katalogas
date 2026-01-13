from vitrina.api.oauth import (
    OAuth2Authentication,
    IsOAuthTokenValid,
    OAuthTokenHasScopes,
    OAuthTokenHasValidOrganizationClaim,
)
from vitrina.uapi.permissions import IsAgentEnabled


class AgentAuthViewSetMixin:
    authentication_classes = [OAuth2Authentication]
    permission_classes = [
        IsOAuthTokenValid,
        OAuthTokenHasScopes,
        OAuthTokenHasValidOrganizationClaim,
        IsAgentEnabled,
    ]

    # Mapping of DRF action names to the required OAuth scopes.
    # ! Must be defined in subclasses.
    required_scopes: dict[str, list[str]] = {}
