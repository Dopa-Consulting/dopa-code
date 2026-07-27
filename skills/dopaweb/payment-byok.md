---
name: payment-byok
description: Configurar Bring Your Own Keys (BYOK) para pasarelas de pago. Permite que un tenant use SUS propias credenciales de Stripe o MercadoPago.
---

# Pagos BYOK (Bring Your Own Keys)

Permitir que tenants enterprise usen sus propias cuentas de pago en vez de las de Dopa.

## Steps

1. El tenant configura sus credenciales en Panel → Pagos → Agregar pasarela
2. Credenciales se guardan cifradas en `TenantCredentials`:
   - `provider`: `"stripe"` o `"mercadopago"`
   - `mode`: `"byok"`
   - `encryptedKey`: secreto cifrado
3. `PaymentRouterService.resolveProvider(tenantId)` detecta BYOK
4. Si BYOK: usa la key del tenant. Si no: usa la key master de Dopa
5. Webhooks: cada tenant configura su endpoint en su dashboard

## Arquitectura

```
Checkout → PaymentRouterService
              ↓
         ¿tenant tiene BYOK?
         ├── Sí → usar TenantCredential.encryptedKey
         └── No  → usar key master de Dopa
              ↓
         createCharge()
              ↓
         Webhook → validar firma → procesar
```

## Stripe BYOK

```ts
const key = await getTenantStripeKey(tenantId)
const stripe = new Stripe(key, { apiVersion: '2026-06-24.dahlia' })
const session = await stripe.checkout.sessions.create({...})
```

## MercadoPago BYOK

```ts
const token = await getTenantMPToken(tenantId)
const mp = new MercadoPagoConfig({ accessToken: token })
```

## Guardrails

- Credenciales NUNCA en logs ni en DB sin cifrar
- Webhook con verificación de firma obligatoria
- Cada tenant tiene su propio webhook URL
