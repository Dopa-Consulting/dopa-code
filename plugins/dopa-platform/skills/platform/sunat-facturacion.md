# sunat-facturacion
**Categoria**: platform
**Tags**: dopa, erp, sunat, facturacion, peru

## Steps
1. Verificar que el comprobante sigue el formato SUNAT (serie, numero, RUC)
2. Validar calculos de IGV (18%), retencion, detraccion
3. Verificar estados de factura: pending → paid → refunded/cancelled
4. Confirmar generacion de CDR y XML firmado
5. Testear con Comprobante de Prueba antes de produccion

## Best Practices
- Los montos deben incluir IGV en el total
- Validar RUC contra SUNAT antes de emitir
- Mantener trazabilidad de anulaciones y notas de credito
- No modificar la logica de facturacion sin aprobacion explicita
- Respetar el modelo Invoice + InvoiceDetail de Sequelize
