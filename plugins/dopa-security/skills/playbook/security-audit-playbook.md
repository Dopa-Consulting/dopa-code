# security-audit-playbook
**Categoria**: security
**Tags**: security, audit, playbook, methodology, checklist

## Steps
1. Leer las 10 lecciones del playbook de Hermes (L1-L10)
2. Aplicar checklist reusable antes de empezar la auditoría
3. Triar por RIESGO, no por tamaño
4. Money paths: race RMW, charge-before-validation, refund-on-failure
5. Controles: default fail-CLOSED ante error/desconocido
6. Flags/bypass: una sola codificación (grep string Y symbol)
7. Tenant scope: valida VALOR, no presencia. OR con scope en todas las ramas
8. Merges recursivos: guard de __proto__
9. IDOR: endpoint usa req.user.companyId, no id del body
10. Mass-assignment: create pinna companyId DESPUÉS del spread
11. CI: pull_request_target? secrets gateados? actions pineadas?
12. Cobertura: código cambiado tiene test que falla al revertir
13. Reporte: file .md con file:línea, escenario concreto, severidad, fix

## Las 10 lecciones (L1-L10)

### L1 — Contrastá el diff contra los patrones seguros que YA existen en el repo
Cuando veas un débito/contador/estado compartido, buscá si ya hay un helper/patrón canónico y comparalo.

### L2 — Dinero: buscá los 3 clásicos
Race read-modify-write, charge-before-validation, sin rollback/refund

### L3 — Controles de seguridad: buscá el modo fail-OPEN
Default ante lo desconocido debe ser el MÁS restrictivo (fail-closed)

### L4 — Flags de seguridad: una sola codificación
Buscá todas las variantes (string Y symbol) y confirmá que coincidan

### L5 — Presencia ≠ valor, y semántica de OR
Validar VALOR de companyId, no solo presencia. En OR, scope en TODAS las ramas

### L6 — Prototype pollution en merges recursivos
Saltar __proto__/constructor/prototype en deepMerge sobre input externo

### L7 — Toggles de producción NO dependen de datos del tenant
Gate por NODE_ENV/env flag, nunca por dato controlado por el usuario

### L8 — CI: el orden de peligro
pull_request_target, ${{ github.event }} interpolation, secrets en PR, actions sin SHA

### L9 — Verificá cobertura de tests del código que cambió
Todo fix de seguridad ship con test que falla si se revierte

### L10 — Verificá tus propias afirmaciones contra el código real
No confundas nombres. Leer antes de sobrescribir. git show --stat del squash

## Patrones de fix verificados
- Débito atómico: UPDATE con literal SQL y chequeo de [affected]
- Hook test sin DB: función pura (options) => void, test directo
- Bypass RBAC para admin/superadmin es INTENCIONAL (SMB) — no re-flaggear
