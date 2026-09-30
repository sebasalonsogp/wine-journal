"""Probe real loopback Storage using a disposable bucket; never print capabilities or keys."""

import json
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
import jwt
from configure_storage import local_credentials

from wine_journal.integrations.storage import MAX_UPLOAD_BYTES, Storage, new_staging_key


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def rejected_as(response: httpx.Response, expected: int) -> bool:
    if response.is_success:
        return False
    # Local Storage sometimes wraps an underlying 413/415 in HTTP 400.
    try:
        return response.status_code == expected or str(response.json().get("statusCode")) == str(
            expected
        )
    except ValueError:
        return False


def main() -> None:
    settings, anon = local_credentials()
    bucket = "wj-storage-probe-" + uuid4().hex
    settings = settings.model_copy(update={"bucket": bucket})
    storage = Storage(settings)
    keys = [new_staging_key(uuid4()) for _ in range(3)]
    service_headers = {
        "Authorization": "Bearer " + settings.service_key.get_secret_value(),
        "apikey": settings.service_key.get_secret_value(),
    }
    anon_headers = {
        "Authorization": "Bearer " + anon.get_secret_value(),
        "apikey": anon.get_secret_value(),
    }
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        try:
            storage.ensure_private_bucket()
            storage.ensure_private_bucket()
            capability = storage.sign_upload(keys[0])
            url = capability.url.get_secret_value()
            upload_headers = {**anon_headers, "Content-Type": "image/jpeg"}
            # Prove server-side expiry with a correctly signed, already-expired LOCAL
            # capability, without waiting two hours. Never inspect a hosted project's keys.
            inspected = subprocess.run(
                ["docker", "inspect", "supabase_storage_wine-journal"],
                capture_output=True,
                text=True,
                check=True,
            )
            environment = dict(
                item.split("=", 1) for item in json.loads(inspected.stdout)[0]["Config"]["Env"]
            )
            parsed = urlsplit(url)
            token = parse_qs(parsed.query)["token"][0]
            claims = jwt.decode(token, environment["AUTH_JWT_SECRET"], algorithms=["HS256"])
            claims.update(iat=int(time.time()) - 7201, exp=int(time.time()) - 1)
            expired = jwt.encode(claims, environment["AUTH_JWT_SECRET"], algorithm="HS256")
            expired_url = urlunsplit(parsed._replace(query=urlencode({"token": expired})))
            response = client.put(expired_url, headers=upload_headers, content=b"expired")
            check(response.status_code in {400, 401, 403}, "expired_capability")
            # Storage checks MIME and bytes, not image decoding (M03 owns that).
            contents = b"synthetic-storage-probe"
            response = client.put(url, headers=upload_headers, content=contents)
            check(response.status_code == 200, "signed_upload")
            info = storage.info(keys[0])
            check(info.size == len(contents) and info.content_type == "image/jpeg", "object_info")
            response = client.put(
                url, headers={**upload_headers, "x-upsert": "true"}, content=b"replacement"
            )
            check(
                response.status_code in {400, 403, 409},
                f"immutable_upload_http_{response.status_code}",
            )
            check(storage.info(keys[0]).size == len(contents), "unchanged_object")
            base = settings.url
            for path in (f"object/{bucket}/{keys[0]}", f"object/public/{bucket}/{keys[0]}"):
                response = client.get(f"{base}/{path}", headers=anon_headers)
                check(response.status_code in {400, 401, 403, 404}, "private_read")
            response = client.post(
                f"{base}/object/{bucket}/{keys[1]}", headers=upload_headers, content=contents
            )
            check(response.status_code in {400, 401, 403}, "unsigned_upload")
            changed_url = url.replace(keys[0], keys[1])
            response = client.put(changed_url, headers=upload_headers, content=contents)
            check(response.status_code in {400, 401, 403}, "path_bound_capability")
            oversize = storage.sign_upload(keys[1]).url.get_secret_value()
            response = client.put(
                oversize, headers=upload_headers, content=b"x" * (MAX_UPLOAD_BYTES + 1)
            )
            check(rejected_as(response, 413), "bucket_byte_limit")
            wrong_type = storage.sign_upload(keys[2]).url.get_secret_value()
            response = client.put(
                wrong_type, headers={**anon_headers, "Content-Type": "text/html"}, content=b"<html>"
            )
            check(rejected_as(response, 415), "bucket_type_limit")
            # A signed upload capability is not a signed download capability.
            response = client.get(url, headers=anon_headers)
            check(response.status_code in {400, 401, 403, 404}, "upload_not_read")
            check(urlsplit(url).hostname == "127.0.0.1", "loopback_capability")
            print(
                "PASS: private bucket, signed upload, immutable key, trusted size/type, "
                "anonymous denial,"
            )
            print(
                "path binding, expiry, upload-only access and real byte/MIME limits. "
                "No capabilities printed."
            )
        finally:
            # Only this run's UUID bucket is removed; never empty a configured application bucket.
            response = client.request(
                "DELETE",
                f"{settings.url}/object/{bucket}",
                headers=service_headers,
                json={"prefixes": keys},
            )
            check(response.status_code == 200, "probe_object_cleanup")
            response = client.delete(f"{settings.url}/bucket/{bucket}", headers=service_headers)
            check(response.status_code == 200, "probe_bucket_cleanup")
            storage.close()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(f"Local Storage check failed: {error}; credentials withheld.")
    except Exception as error:
        sys.exit(f"Local Storage check failed ({type(error).__name__}); details withheld.")
