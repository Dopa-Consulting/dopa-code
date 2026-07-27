---
name: customize-checkout
description: Modificar el flujo de checkout de Dopa Web (pasarelas, shipping, impuestos, formulario). Usar cuando el usuario quiere cambiar cómo se procesan los pagos o el envío.
---

# Personalizar Checkout

Modificar el flujo de compra sin romper la integración con ERP ni fiscal.

## Steps

1. El checkout usa `CheckoutComplete.tsx` (client component) + `useCart()`
2. API endpoint: `POST /api/checkout` valida stock, calcula impuestos, crea order
3. Pasarelas: `ensureProviders()` → `getActiveProvider()` → `createCharge()`
4. Stripe: `POST /api/onboarding/create-checkout` → session → redirect
5. MercadoPago: brick en frontend, preference en backend
6. Fiscal: `validateFiscalDoc()` con RUC/DNI (PE), RUT (CL), RFC (MX)

## Guardrails

- NUNCA modificar `src/hooks/useCheckout.ts`
- No tocar imports de `erp-client`, `facturacion`, `tax-calculator`
- Stripe SIEMPRE lazy init (dentro del handler, no a nivel módulo)
- API version: `2026-06-24.dahlia`

## Anti-patrones

```tsx
// ❌ INCORRECTO — Stripe a nivel módulo (rompe build)
const stripe = new Stripe(process.env.KEY || '')

// ✅ CORRECTO — lazy init
export async function POST(req) {
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY)
  ...
}
```
