"""A deliberately tiny identity provider for the identity step.

Serves a JWKS document at http://localhost:9000/.well-known/jwks.json and
prints two ready-to-use tokens: a reader and a publisher.

This is NOT a real IdP. No login, no consent, no refresh, no revocation. It
exists so the identity step is hands-on without anyone standing up Keycloak.

    pip install pyjwt cryptography
    python3 scripts/fake_idp.py
"""

from __future__ import annotations

import base64
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "http://localhost:9000"
AUDIENCE = "http://localhost:3000/mcp"
KEY_ID = "workshop-key-1"
PORT = 9000

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pub = private_key.public_key().public_numbers()


def _b64(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


JWKS = {
    "keys": [
        {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": KEY_ID,
         "n": _b64(pub.n), "e": _b64(pub.e)}
    ]
}


def mint(subject: str, roles: list[str], hours: int = 12) -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": subject, "roles": roles,
         "iat": now, "exp": now + hours * 3600},
        private_key, algorithm="RS256", headers={"kid": KEY_ID},
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/.well-known/jwks.json"):
            body = json.dumps(JWKS).encode()
        elif self.path.startswith("/.well-known/openid-configuration"):
            body = json.dumps({"issuer": ISSUER,
                               "jwks_uri": f"{ISSUER}/.well-known/jwks.json"}).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print()
    print(f"  JWKS serving at {ISSUER}/.well-known/jwks.json")
    print()
    print("  Reader token (can save digests, cannot publish):")
    print(f"  export READER_JWT={mint('reader@example.invalid', ['reader'])}")
    print()
    print("  Publisher token:")
    print(f"  export PUBLISHER_JWT={mint('publisher@example.invalid', ['reader', 'publisher'])}")
    print()
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
