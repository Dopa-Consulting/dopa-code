# dopa-web
**Categoria**: platform
**Tags**: dopa, web, ecommerce, nextjs, storefront

## Steps
1. Identificar si el cambio es en el storefront (Next.js) o en el dashboard
2. Verificar compatibilidad con el tema activo del tenant
3. Validar contra el design system de DopaWeb
4. Testear en mobile y desktop (responsive)
5. Verificar integracion con pasarela de pago (MercadoPago, Stripe)

## Best Practices
- Usar componentes del design system, no estilos inline
- Respetar la configuracion de checkout por tenant
- No hardcodear textos — usar i18n
- Mantener el gradiente #00E9D9 → #6900FF consistente
