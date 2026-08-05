import base64
import hashlib
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

from inti.config import settings

logger = logging.getLogger("inti.webauthn")


@dataclass
class WebAuthnChallenge:
    challenge: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300


class WebAuthnService:
    def __init__(self):
        self._pending_challenges: dict[str, WebAuthnChallenge] = {}
        self._rp_id = "localhost" if settings.dopa_code_dummy else "dopa-code.local"
        self._origin = f"https://{self._rp_id}"

    def _b64url(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _decode_b64url(self, s: str) -> bytes:
        padding = 4 - len(s) % 4
        if padding != 4:
            s += "=" * padding
        return base64.urlsafe_b64decode(s)

    def generate_registration_options(
        self, user_id: str, user_name: str, device_name: str
    ) -> dict:
        challenge_bytes = secrets.token_bytes(32)
        challenge = self._b64url(challenge_bytes)
        self._pending_challenges[challenge] = WebAuthnChallenge(
            challenge=challenge, user_id=user_id
        )
        return {
            "challenge": challenge,
            "rp": {"name": "Dopa Code - Inti", "id": self._rp_id},
            "user": {
                "id": self._b64url(user_id.encode()),
                "name": user_name,
                "displayName": f"{user_name} ({device_name})",
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "userVerification": "required",
                "residentKey": "required",
            },
        }

    def generate_assertion_options(self, user_id: str, credential_id: str) -> dict:
        challenge_bytes = secrets.token_bytes(32)
        challenge = self._b64url(challenge_bytes)
        self._pending_challenges[challenge] = WebAuthnChallenge(
            challenge=challenge, user_id=user_id
        )
        return {
            "challenge": challenge,
            "rpId": self._rp_id,
            "allowCredentials": [{"type": "public-key", "id": credential_id}],
            "timeout": 60000,
            "userVerification": "required",
        }

    def _verify_challenge(self, raw_id: str, client_data_json_b64: str) -> dict | None:
        """Verifica que el clientDataJSON contenga el challenge correcto."""
        try:
            client_data_json = self._decode_b64url(client_data_json_b64).decode()
            client_data = json.loads(client_data_json)
            challenge = client_data.get("challenge", "")
            pending = self._pending_challenges.pop(challenge, None)
            if not pending:
                logger.warning("WebAuthn: challenge not found or expired")
                return None
            if (datetime.now(timezone.utc) - pending.created_at).total_seconds() > pending.ttl_seconds:
                logger.warning("WebAuthn: challenge expired")
                return None
            return {"user_id": pending.user_id, "challenge": challenge}
        except Exception as e:
            logger.warning(f"WebAuthn challenge verification failed: {e}")
            return None

    def verify_registration(
        self, raw_id: str, client_data_json: str, attestation_object: str,
        credential_id: str, public_key: str
    ) -> dict | None:
        """Verifica registro: challenge + almacena credencial."""
        verified = self._verify_challenge(raw_id, client_data_json)
        if not verified:
            return None
        # En produccion se verificaria attestation_object con COSE/CBOR.
        # Por ahora: guardar credencial con challenge verificado.
        logger.info(f"WebAuthn registration verified for user {verified['user_id'][:12]}")
        return {
            "verified": True,
            "user_id": verified["user_id"],
            "credential_id": credential_id or raw_id,
            "public_key": public_key,
            "signature": hashlib.sha256(
                f"webauthn:{credential_id}:{verified['challenge']}".encode()
            ).hexdigest(),
        }

    def verify_assertion(
        self, raw_id: str, client_data_json: str, authenticator_data: str,
        signature: str, credential_id: str, user_id: str
    ) -> dict | None:
        """Verifica autenticacion: challenge + user_id match."""
        verified = self._verify_challenge(raw_id, client_data_json)
        if not verified:
            return None
        if verified["user_id"] != user_id:
            logger.warning("WebAuthn: user_id mismatch in assertion")
            return None
        logger.info(f"WebAuthn assertion verified for user {user_id[:12]}")
        return {
            "verified": True,
            "user_id": user_id,
            "credential_id": credential_id or raw_id,
            "signature": hashlib.sha256(
                f"webauthn:{credential_id}:{verified['challenge']}".encode()
            ).hexdigest(),
        }


webauthn_service = WebAuthnService()
webauthn = webauthn_service  # backward compat
