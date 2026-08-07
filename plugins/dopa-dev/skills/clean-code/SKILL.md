---
name: clean-code
description: Estándares de código limpio para Dopa. Usar al escribir o revisar cualquier código en los repos Dopa.
---

# Clean Code — Dopa Standards

## Principios

1. **Conciso sobre verboso.** Menos código = menos bugs. Si una función pasa de 30 líneas, extraela.
2. **Directo sobre abstracto.** No crees abstracciones "por si acaso". YAGNI.
3. **Nombres que mienten = bugs.** `data`, `info`, `temp`, `result` no dicen nada. Usa `unpaidInvoices`, `activeTenantCount`.
4. **Un nivel de indentación.** Si anidas 3 niveles, extrae una funcion.
5. **Sin comentarios obvios.** `// incrementa i` no. `// Usamos UTC porque SUNAT exige timestamps en zona horaria Peru` si.

## TypeScript

- `const` por defecto, `let` solo si muta.
- Sin `any` sin justificacion en comentario.
- Tipos explicitos en firmas publicas, inferidos en internas.
- `async/await` sobre `.then()`.

## Python (Inti)

- Type hints en TODAS las firmas de funciones publicas.
- `snake_case` para variables y funciones.
- `from inti.X import Y` (imports relativos al paquete).
- Docstrings solo cuando el nombre no cuenta toda la historia.

## React

- Un componente = una responsabilidad.
- Estado tan abajo como sea posible (lift up solo cuando se comparte).
- `useCallback`/`useMemo` solo cuando hay problemas de rendimiento medibles.
- Sin estilos inline (usar MUI `sx` o Tailwind).
