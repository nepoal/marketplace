from open_schools_platform.common.selectors import selector_factory
from open_schools_platform.marketplace_management.models import (
    OidcClient,
    OidcAuthorizationCode,
    OidcAccessToken,
    OidcRefreshToken,
)


@selector_factory(OidcClient)
def get_oidc_client(*, filters=None, prefetch_related_list=None) -> OidcClient:
    filters = filters or {}
    qs = OidcClient.objects.select_related("app").all()
    if "client_id" in filters:
        qs = qs.filter(client_id=filters["client_id"])
    if "id" in filters:
        qs = qs.filter(id=filters["id"])
    return qs.first()


@selector_factory(OidcAuthorizationCode)
def get_auth_code(*, filters=None, prefetch_related_list=None) -> OidcAuthorizationCode:
    filters = filters or {}
    qs = OidcAuthorizationCode.objects.select_related("client", "user").all()
    if "code" in filters:
        qs = qs.filter(code=filters["code"])
    return qs.first()


@selector_factory(OidcAccessToken)
def get_access_token(*, filters=None, prefetch_related_list=None) -> OidcAccessToken:
    filters = filters or {}
    qs = OidcAccessToken.objects.select_related("client", "user").all()
    if "token" in filters:
        qs = qs.filter(token=filters["token"])
    return qs.first()


@selector_factory(OidcRefreshToken)
def get_refresh_token(*, filters=None, prefetch_related_list=None) -> OidcRefreshToken:
    filters = filters or {}
    qs = OidcRefreshToken.objects.select_related("client", "user").all()
    if "token" in filters:
        qs = qs.filter(token=filters["token"])
    return qs.first()
