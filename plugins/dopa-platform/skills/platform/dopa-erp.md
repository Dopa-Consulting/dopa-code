# dopa-erp
**Categoria**: platform
**Tags**: dopa, erp, backend, sunat, multi-tenant

## Steps
1. Identificar el modulo ERP afectado (facturacion, inventario, POS, inbox)
2. Verificar compatibilidad con multi-tenant (companyId en queries)
3. Validar contra reglas SUNAT (IGV, retencion, serie)
4. Verificar integracion con webhooks y BYOK
5. Testear con datos de prueba multi-pais (PE, MX, CO)

## Best Practices
- Siempre incluir companyId en queries (nunca bypassMultiTenant)
- No modificar endpoints del ERP core sin coordinacion
- Respetar el modelo de datos Sequelize + Postgres
- Mantener compatibilidad con facturacion electronica SUNAT
