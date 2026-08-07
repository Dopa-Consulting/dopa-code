---
name: test-driven-development
description: TDD para comportamiento NO trivial. Usar al implementar logica de negocio, auth, pagos o codigo fiscal. NO para wrappers CRUD simples.
---

# TDD — Test-Driven Development

## Cuando usar TDD

- ✅ Logica de negocio (calculo de impuestos, generacion de facturas)
- ✅ Auth / permisos (RBAC, scopes, aislamiento de tenant)
- ✅ Flujos de pago (Stripe, Culqi)
- ✅ Codigo fiscal (integracion SUNAT/Nubefact)
- ❌ Wrappers CRUD simples
- ❌ Layout/CSS de UI

## Ciclo

1. **RED** — Escribi un test que falle (prueba el bug o feature faltante).
2. **GREEN** — Escribi el MINIMO codigo para pasar. Sin refactorizar todavia.
3. **REFACTOR** — Limpia. Extrae funciones, mejora nombres.

## Patrones de test por proyecto

- **DopaCRM (backend):** Vitest + `vi.hoisted` para mocks. Mockear modelos, no DB.
- **Dopa Web (dopa-sites):** Vitest + RTL para componentes.
- **Dopa Code (Inti):** pytest + pytest-asyncio. Testear endpoints de API.

## Como se ve un buen test

```typescript
it('rechaza emitir boleta sin add-on fiscal activo', async () => {
  const company = mockCompany({ fiscalStatus: 'none', entitlements: {} });
  expect(canEmitFiscal(company)).toBe(false);
});
```

- Testea el COMPORTAMIENTO, no la implementacion.
- El nombre describe QUE prueba, no COMO.
- Una asercion por test (o aserciones estrechamente relacionadas).
