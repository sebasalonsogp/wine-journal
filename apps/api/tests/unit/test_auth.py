import json
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from wine_journal.core.auth import TokenVerifier
from wine_journal.core.errors import ApiError

type Authority = tuple[TokenVerifier, ec.EllipticCurvePrivateKey, dict[str, object]]


@pytest.fixture
def authority() -> Iterator[tuple[TokenVerifier, ec.EllipticCurvePrivateKey, dict[str, object]]]:
    private = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private.public_key()))
    public.update(kid="first", alg="ES256", use="sig")
    state: dict[str, object] = {"keys": [public], "requests": 0, "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state["requests"] = int(str(state["requests"])) + 1
            self.send_response(int(str(state["status"])))
            self.end_headers()
            self.wfile.write(json.dumps({"keys": state["keys"]}).encode())

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield TokenVerifier(f"http://127.0.0.1:{server.server_port}/auth/v1"), private, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def signed(verifier: TokenVerifier, key: ec.EllipticCurvePrivateKey, **changes: object) -> str:
    claims = {
        "iss": verifier.issuer,
        "sub": str(uuid4()),
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "first"})


def test_valid_identity_and_cached_public_keys(authority: Authority) -> None:
    verifier, key, state = authority
    token = signed(verifier, key)
    principal = verifier.verify(token)
    assert str(principal.subject) == jwt.decode(token, options={"verify_signature": False})["sub"]
    verifier.verify(token)
    assert state["requests"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "service_role"},
        {"aud": ["authenticated", "other"]},
        {"exp": 1},
        {"sub": None},
        {"sub": ""},
        {"sub": "not-a-uuid"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"iat": int(time.time()) + 3600},
    ],
)
def test_rejects_invalid_claims(authority: Authority, changes: dict[str, object]) -> None:
    verifier, key, _ = authority
    with pytest.raises(ApiError) as exc:
        verifier.verify(signed(verifier, key, **changes))
    assert exc.value.status == 401


def test_rejects_forged_signature(authority: Authority) -> None:
    verifier, _, _ = authority
    with pytest.raises(ApiError) as exc:
        verifier.verify(signed(verifier, ec.generate_private_key(ec.SECP256R1())))
    assert exc.value.status == 401


def test_rejects_missing_expiry(authority: Authority) -> None:
    verifier, key, _ = authority
    claims = jwt.decode(signed(verifier, key), options={"verify_signature": False})
    del claims["exp"]
    with pytest.raises(ApiError) as exc:
        verifier.verify(jwt.encode(claims, key, algorithm="ES256", headers={"kid": "first"}))
    assert exc.value.status == 401


def test_key_rotation_refetches_after_cooldown(authority: Authority) -> None:
    verifier, first, state = authority
    verifier.verify(signed(verifier, first))
    second = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(second.public_key()))
    public.update(kid="second", alg="ES256", use="sig")
    state["keys"] = [public]
    claims = jwt.decode(signed(verifier, second), options={"verify_signature": False})
    token = jwt.encode(claims, second, algorithm="ES256", headers={"kid": "second"})
    with pytest.raises(ApiError):
        verifier.verify(token)
    assert state["requests"] == 1  # Unknown IDs cannot force a fetch on every request.
    verifier.keys.cooldown_duration = 0  # Simulate the elapsed window without sleeping.
    verifier.verify(token)
    assert state.get("requests") == 2
    with pytest.raises(ApiError):
        verifier.verify(signed(verifier, first))


def test_key_server_failure_is_safe_and_recoverable(authority: Authority) -> None:
    verifier, key, state = authority
    state["status"] = 503
    with pytest.raises(ApiError) as exc:
        verifier.verify(signed(verifier, key))
    assert exc.value.status == 503
    assert verifier.issuer not in exc.value.message
    state["status"] = 200
    verifier.verify(signed(verifier, key))


@pytest.mark.parametrize("token", ["not-a-token", "x" * 8193])
def test_bad_input_never_fetches_keys(authority: Authority, token: str) -> None:
    verifier, _, state = authority
    with pytest.raises(ApiError):
        verifier.verify(token)
    assert state["requests"] == 0
