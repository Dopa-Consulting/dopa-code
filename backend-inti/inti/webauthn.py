"""
WebAuthn (Passkeys) - Implementacion MVP.

ADVERTENCIA: Esta es una implementacion simplificada para desarrollo.
NO apta para produccion. Para produccion usar una libreria como:
  pip install webauthn

Limitaciones conocidas:
  - No verifica firmas criptograficas (attestation/assertion)
  - No valida el formato de credential public key (COSE/CTAP2)
  - El challenge es un token opaco, no un ArrayBuffer como requiere WebAuthn
  - Las sesiones son en memoria (se pierden al reiniciar)

Para produccion:
  - Usar py_webauthn (https://github.com/duo-labs/py_webauthn)
  - Persistir credenciales en DB con campos binary
  - Validar origen (origin) y RP ID
  - Implementar contador de firmas (signature counter)
"""

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from inti.config import settings


@dataclass
class WebAuthnChallenge:
    challenge: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300


class WebAuthnService:
    def __init__(self):
        self._pending_challenges: dict[str, WebAuthnChallenge] = {}

    def generate_registration_options(
        self, user_id: str, user_name: str, device_name: str
    ) -> dict:
        challenge = secrets.token_urlsafe(32)
        self._pending_challenges[challenge] = WebAuthnChallenge(
            challenge=challenge, user_id=user_id
        )

        return {
            "challenge": challenge,
            "rp": {
                "name": "Dopa Code - Inti",
                "id": settings.dopa_code_dummy and "localhost" or "dopa-code.local",
            },
            "user": {
                "id": user_id,
                "name": user_name,
                "displayName": f"{user_name} ({device_name})",
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},   # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "userVerification": "required",
                "residentKey": "required",
            },
        }

    def generate_assertion_options(
        self, user_id: str, credential_id: str
    ) -> dict:
        challenge = secrets.token_urlsafe(32)
        self._pending_challenges[challenge] = WebAuthnChallenge(
            challenge=challenge, user_id=user_id
        )

        return {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": settings.dopa_code_dummy and "localhost" or "dopa-code.local",
            "allowCredentials": [
                {
                    "id": credential_id,
                    "type": "public-key",
                }
            ],
            "userVerification": "required",
        }

    def verify_registration(self, challenge: str, credential_id: str, public_key: str) -> dict:
        stored = self._pending_challenges.pop(challenge, None)
        if not stored:
            return {"verified": False, "error": "Challenge not found or expired"}

        if (datetime.now(timezone.utc) - stored.created_at).seconds > stored.ttl_seconds:
            return {"verified": False, "error": "Challenge expired"}

        return {
            "verified": True,
            "user_id": stored.user_id,
            "credential_id": credential_id,
            "public_key": public_key,
        }

    def verify_assertion(self, challenge: str, credential_id: str, user_id: str) -> dict:
        stored = self._pending_challenges.pop(challenge, None)
        if not stored:
            return {"verified": False, "error": "Challenge not found or expired"}

        if (datetime.now(timezone.utc) - stored.created_at).seconds > stored.ttl_seconds:
            return {"verified": False, "error": "Challenge expired"}

        if stored.user_id != user_id:
            return {"verified": False, "error": "User mismatch"}

        return {
            "verified": True,
            "user_id": user_id,
            "credential_id": credential_id,
            "signature": f"webauthn:{credential_id}:{challenge[:16]}",
        }

    def get_pending_challenge(self, challenge: str) -> WebAuthnChallenge | None:
        return self._pending_challenges.get(challenge)


webauthn = WebAuthnService()
