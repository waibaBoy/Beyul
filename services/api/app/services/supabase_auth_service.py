from __future__ import annotations

import asyncio
import base64
import json
import time
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from typing import Any
from urllib.request import urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives import hashes
from fastapi import HTTPException, status
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings


class SupabaseAuthService:
    def __init__(self) -> None:
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cached_at: float = 0
        self._lock = asyncio.Lock()

    async def verify_bearer_token(self, authorization: str | None) -> dict[str, Any]:
        token = self._extract_bearer_token(authorization)
        header = self._decode_token_segment(token, 0)
        payload = self._decode_token_segment(token, 1)
        signature = self._decode_signature(token)

        algorithm = header.get("alg")
        if not algorithm:
            raise self._unauthorized("JWT header is missing the signing algorithm.")

        if algorithm.startswith("HS"):
            self._verify_hmac_token(token, signature, algorithm)
        else:
            jwk_payload = await self._get_signing_key(header.get("kid"))
            self._verify_asymmetric_token(token, signature, algorithm, jwk_payload)

        self._validate_registered_claims(payload)
        return payload

    def _extract_bearer_token(self, authorization: str | None) -> str:
        if not authorization:
            raise self._unauthorized("Missing Authorization header.")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise self._unauthorized("Authorization header must be in the format 'Bearer <token>'.")
        return token

    def _decode_token_segment(self, token: str, index: int) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise self._unauthorized("JWT must contain exactly three segments.")
        try:
            raw = self._base64url_decode(parts[index])
            return json.loads(raw.decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            raise self._unauthorized("JWT contains an invalid JSON segment.") from exc

    def _decode_signature(self, token: str) -> bytes:
        parts = token.split(".")
        if len(parts) != 3:
            raise self._unauthorized("JWT must contain exactly three segments.")
        try:
            return self._base64url_decode(parts[2])
        except ValueError as exc:
            raise self._unauthorized("JWT signature segment is invalid.") from exc

    def _verify_hmac_token(self, token: str, signature: bytes, algorithm: str) -> None:
        if not settings.supabase_jwt_secret:
            raise self._unauthorized("No Supabase JWT secret is configured for symmetric token verification.")

        hash_algorithm = {"HS256": sha256}.get(algorithm)
        if hash_algorithm is None:
            raise self._unauthorized(f"Unsupported HMAC JWT algorithm: {algorithm}.")

        signing_input = ".".join(token.split(".")[:2]).encode("utf-8")
        expected_signature = hmac_new(
            settings.supabase_jwt_secret.encode("utf-8"),
            signing_input,
            hash_algorithm,
        ).digest()
        if not compare_digest(signature, expected_signature):
            raise self._unauthorized("Invalid JWT signature.")

    async def _get_signing_key(self, key_id: str | None) -> dict[str, Any]:
        if not key_id:
            raise self._unauthorized("JWT header is missing the key identifier.")

        jwks = await self._get_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == key_id:
                return key
        raise self._unauthorized("No matching JWKS signing key was found for this token.")

    async def _get_jwks(self) -> dict[str, Any]:
        async with self._lock:
            now = time.time()
            if self._jwks_cache is not None and now - self._jwks_cached_at < 300:
                return self._jwks_cache

            jwks_url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
            try:
                payload = await asyncio.to_thread(self._download_json, jwks_url)
            except OSError as exc:
                raise self._unauthorized(f"Failed to download Supabase JWKS: {exc}") from exc

            if not isinstance(payload, dict) or "keys" not in payload:
                raise self._unauthorized("Supabase JWKS response is invalid.")

            self._jwks_cache = payload
            self._jwks_cached_at = now
            return payload

    def _download_json(self, url: str) -> dict[str, Any]:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _verify_asymmetric_token(
        self,
        token: str,
        signature: bytes,
        algorithm: str,
        jwk_payload: dict[str, Any],
    ) -> None:
        signing_input = ".".join(token.split(".")[:2]).encode("utf-8")

        try:
            if algorithm == "ES256":
                public_key = self._load_ec_public_key(jwk_payload)
                raw_length = len(signature) // 2
                der_signature = encode_dss_signature(
                    int.from_bytes(signature[:raw_length], "big"),
                    int.from_bytes(signature[raw_length:], "big"),
                )
                public_key.verify(der_signature, signing_input, ec.ECDSA(hashes.SHA256()))
                return

            if algorithm == "RS256":
                public_key = self._load_rsa_public_key(jwk_payload)
                public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
                return
        except InvalidSignature as exc:
            raise self._unauthorized("Invalid JWT signature.") from exc
        except ValueError as exc:
            raise self._unauthorized("Invalid JWKS signing key.") from exc

        raise self._unauthorized(f"Unsupported JWT algorithm: {algorithm}.")

    def _load_ec_public_key(self, jwk_payload: dict[str, Any]) -> EllipticCurvePublicKey:
        if jwk_payload.get("crv") != "P-256":
            raise self._unauthorized("Unsupported EC curve for JWT verification.")
        x = int.from_bytes(self._base64url_decode(jwk_payload["x"]), "big")
        y = int.from_bytes(self._base64url_decode(jwk_payload["y"]), "big")
        public_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
        return public_numbers.public_key()

    def _load_rsa_public_key(self, jwk_payload: dict[str, Any]) -> RSAPublicKey:
        modulus = int.from_bytes(self._base64url_decode(jwk_payload["n"]), "big")
        exponent = int.from_bytes(self._base64url_decode(jwk_payload["e"]), "big")
        public_numbers = rsa.RSAPublicNumbers(exponent, modulus)
        return public_numbers.public_key()

    def _validate_registered_claims(self, payload: dict[str, Any]) -> None:
        issuer = payload.get("iss")
        expected_issuer = settings.supabase_url.rstrip("/") + "/auth/v1"
        if issuer != expected_issuer:
            raise self._unauthorized("JWT issuer does not match this Supabase project.")

        now = int(time.time())
        exp = payload.get("exp")
        if exp is not None and int(exp) < now:
            raise self._unauthorized("JWT has expired.")

        nbf = payload.get("nbf")
        if nbf is not None and int(nbf) > now:
            raise self._unauthorized("JWT is not yet valid.")

    def _base64url_decode(self, value: str) -> bytes:
        padding_length = (-len(value)) % 4
        return base64.urlsafe_b64decode(value + ("=" * padding_length))

    def _unauthorized(self, detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
