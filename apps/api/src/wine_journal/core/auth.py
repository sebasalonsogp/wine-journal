from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from wine_journal.core.errors import ApiError

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: UUID


class TokenVerifier:
    def __init__(self, issuer: str) -> None:
        self.issuer = issuer
        self.keys = PyJWKClient(
            issuer + "/.well-known/jwks.json",
            cache_keys=False,
            lifespan=300,
            timeout=5,
            cooldown_duration=30,
        )

    def verify(self, token: str) -> Principal:
        if len(token) > 8192:
            raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue.")
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in {"ES256", "RS256"}:
                raise jwt.InvalidTokenError()
            kid = header.get("kid")
            if not isinstance(kid, str) or not 1 <= len(kid) <= 128:
                raise jwt.InvalidTokenError()
            key = self.keys.get_signing_key(kid)
            if key.algorithm_name != header["alg"]:
                raise jwt.InvalidTokenError()
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
                issuer=self.issuer,
                options={
                    "require": ["exp", "iat", "sub", "iss", "aud", "role"],
                    "strict_aud": True,
                },
                leeway=5,
            )
            if claims["role"] != "authenticated" or claims.get("is_anonymous", False) is not False:
                raise jwt.InvalidTokenError()
            return Principal(self.issuer, UUID(claims["sub"]))
        except PyJWKClientConnectionError:
            raise ApiError(
                503, "AUTH_UNAVAILABLE", "Sign-in verification is temporarily unavailable."
            ) from None
        except (jwt.InvalidTokenError, PyJWKClientError, ValueError, TypeError, KeyError):
            raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue.") from None


def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue.")
    verifier: TokenVerifier | None = request.app.state.token_verifier
    if verifier is None:
        raise ApiError(503, "AUTH_UNAVAILABLE", "Sign-in verification is not configured.")
    return verifier.verify(credentials.credentials)
