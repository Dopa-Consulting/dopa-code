# customize_product_page

Modificar layout de pagina de producto sin tocar checkout ni ERP.

**Tags**: dopaweb, theme, product, safe

## Steps

1. Analizar el template actual de producto
2. Identificar zonas editables (componentes, estilos)
3. Aplicar cambios solo en src/components/product/ y src/styles/
4. Verificar que useCheckout y ERP siguen intactos
5. Test visual y funcional

## Best Practices

- Nunca modificar src/hooks/useCheckout.ts
- No tocar imports de erp-client, facturacion, o tax-calculator
- Los datos del producto vienen del ERP via API, no modificar el fetch
- Probar en mobile y desktop

## Guardrails activos

Este perfil tiene guardrails que bloquean cambios en:
- src/integrations/erp/
- src/lib/facturacion/
- src/hooks/useCheckout.ts
- src/webhooks/
