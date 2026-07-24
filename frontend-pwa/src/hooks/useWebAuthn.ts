import { useState, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function useWebAuthn() {
  const [registered, setRegistered] = useState(false);
  const [deviceId, setDeviceId] = useState("");
  const [error, setError] = useState("");

  const isAvailable = typeof window !== "undefined" && !!window.PublicKeyCredential;

  const register = useCallback(async () => {
    if (!isAvailable) {
      setError("WebAuthn not available on this device");
      return null;
    }

    try {
      const beginRes = await fetch(`${API_BASE}/webauthn/register/begin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "local", user_name: "Developer", device_name: "PWA" }),
      });
      const { options, challenge } = await beginRes.json();

      options.publicKey.challenge = Uint8Array.from(
        atob(challenge.replace(/-/g, "+").replace(/_/g, "/")),
        (c) => c.charCodeAt(0)
      ).buffer;
      options.publicKey.user.id = new TextEncoder().encode(options.publicKey.user.id).buffer;

      const credential = (await navigator.credentials.create({
        publicKey: options.publicKey,
      })) as PublicKeyCredential;

      const completeRes = await fetch(`${API_BASE}/webauthn/register/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          challenge,
          credential_id: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
          public_key: challenge,
          device_name: "PWA",
        }),
      });

      const result = await completeRes.json();
      if (result.verified) {
        setRegistered(true);
        setDeviceId(result.device_id);
        setError("");
        return result;
      }
      setError("Registration failed");
      return null;
    } catch (e) {
      setError(String(e));
      return null;
    }
  }, [isAvailable]);

  const authenticate = useCallback(async () => {
    if (!isAvailable) {
      setError("WebAuthn not available");
      return null;
    }

    try {
      const beginRes = await fetch(`${API_BASE}/webauthn/authenticate/begin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "local" }),
      });
      const { options, challenge, device_id } = await beginRes.json();

      if (!options) {
        setError("No passkey registered. Register first.");
        return null;
      }

      options.publicKey.challenge = Uint8Array.from(
        atob(challenge.replace(/-/g, "+").replace(/_/g, "/")),
        (c) => c.charCodeAt(0)
      ).buffer;
      if (options.publicKey.allowCredentials) {
        options.publicKey.allowCredentials[0].id = Uint8Array.from(
          atob(options.publicKey.allowCredentials[0].id.replace(/-/g, "+").replace(/_/g, "/")),
          (c) => c.charCodeAt(0)
        ).buffer;
      }

      const assertion = (await navigator.credentials.get({
        publicKey: options.publicKey,
      })) as PublicKeyCredential;

      const completeRes = await fetch(`${API_BASE}/webauthn/authenticate/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          challenge,
          credential_id: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
          user_id: "local",
        }),
      });

      const result = await completeRes.json();
      if (result.verified) {
        setDeviceId(device_id);
        setError("");
        return result;
      }
      setError("Authentication failed");
      return null;
    } catch (e) {
      setError(String(e));
      return null;
    }
  }, [isAvailable]);

  return { isAvailable, registered, deviceId, error, register, authenticate };
}
