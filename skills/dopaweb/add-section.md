---
name: add-section
description: Agregar una nueva sección al storefront de Dopa Web (hero, features, testimonios, FAQ, grids). Usar cuando el usuario pide añadir contenido a su tienda.
---

# Agregar Sección al Storefront

Añadir componentes visuales al layout de la tienda sin romper el diseño existente.

## Steps

1. Identificar qué tipo de sección: hero, features grid, testimonios, FAQ, CTA
2. El layout `(store)/layout.tsx` usa `<main>` con max-width 1200px
3. Crear componente en `src/components/storefront/` con `'use client'` si usa hooks
4. Si es server component, puede usar `getTenant()` para colores dinámicos
5. CSS vars disponibles: `--tenant-primary`, `--tenant-secondary`

## Patrones

### Hero section
```tsx
<section style={{ padding: '4rem 0', textAlign: 'center' }}>
  <h1 style={{
    fontSize: 'clamp(2rem, 5vw, 3.5rem)',
    fontWeight: 800,
    background: 'linear-gradient(90deg, var(--tenant-primary), #6900FF)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  }}>
    {title}
  </h1>
</section>
```

### Features grid
```tsx
<div style={{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: '1px',
  background: 'rgba(255,255,255,0.03)',
}}>
  {features.map(f => (
    <div key={f.title} style={{ background: '#0D1117', padding: '2rem' }}>
      <h3 style={{ color: '#FFFFFF', fontWeight: 600 }}>{f.title}</h3>
      <p style={{ color: '#6B7280', marginTop: '0.5rem' }}>{f.body}</p>
    </div>
  ))}
</div>
```

## Guardrails

- No usar emojis en UI (identidad Dopa)
- No glassmorphism (Clean Solid theme)
- Sin sombras de color
- Márgenes: padding generoso, max-width 1200px
