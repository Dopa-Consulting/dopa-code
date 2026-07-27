---
name: customize-branding
description: Personalizar identidad visual de una tienda Dopa Web (colores, logo, tipografía, metadata). Usar cuando el usuario pide cambiar la apariencia de su storefront.
---

# Personalizar Branding de Tienda

Modificar la identidad visual de un tenant sin tocar lógica de negocio.

## Steps

1. Leer el tenant actual via `getTenant()` del header `x-tenant-id`
2. Identificar qué quiere cambiar el usuario: colores, logo, nombre, metadata
3. Los colores se guardan en `Tenants.primaryColor` y `Tenants.secondaryColor`
4. El layout inyecta `--tenant-primary` y `--tenant-secondary` como CSS vars
5. Todos los componentes del storefront usan esas variables
6. Para logo: campo `storeLogo` en Tenants (media upload via Payload)
7. Metadata: `metadataTitle`, `metadataDescription` para SEO

## Best Practices

- NUNCA hardcodear colores en componentes. Usar CSS vars.
- Paleta Dopa: #00E9D9 (turquesa), #6900FF (morado), #189DE8 (celeste)
- Gradiente corporativo: #00E9D9 → #6900FF (90°)
- Botones: texto blanco sobre gradiente, NUNCA texto oscuro
- Tipografía: Geist (sans) + Geist Mono para código
- Clean Solid dark theme (#0B0E11 bg, #E2E8F0 text)

## Ejemplo

```tsx
// ✅ CORRECTO
<button style={{
  background: 'var(--tenant-primary)',
  color: '#FFFFFF',
}}>Comprar</button>

// ❌ INCORRECTO
<button style={{ background: '#4A7C59' }}>Comprar</button>
```
