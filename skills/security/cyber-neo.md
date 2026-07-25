# cyber_neo_security_audit

Auditoria de seguridad integral basada en OWASP 2025 Top 10 y CWE Top 25.
11 dominios, 60+ patrones de secretos, reporte profesional con CVSS.

**Origen**: [Hainrixz/cyber-neo](https://github.com/Hainrixz/cyber-neo) (MIT, 214 stars)
**Tags**: general, security, audit, owasp, cwe, universal

## Iron Law (regla de hierro)

**Read-only sobre el proyecto objetivo.** Cyber Neo:
- NUNCA modifica archivos del proyecto
- NUNCA ejecuta codigo del proyecto
- NUNCA instala paquetes ni dependencias
- NUNCA ejecuta comandos de auto-fix
- Solo escribe el reporte de salida
- Los secretos detectados NUNCA se incluyen en el reporte

## 11 dominios de seguridad

| # | Dominio | Que detecta |
|---|---------|-------------|
| 1 | **Code Security (SAST)** | SQL injection, XSS, command injection, path traversal, SSRF |
| 2 | **Auth & Authorization** | Missing auth middleware, JWT flaws, broken access control, IDOR |
| 3 | **Crypto** | Weak algorithms (MD5, SHA1, DES), hardcoded keys, insecure random |
| 4 | **Secrets** | 60+ patterns: AWS, GCP, GitHub, Slack, Stripe, DB creds, API keys |
| 5 | **Dependencies (SCA)** | CVEs conocidos en npm, pip, cargo, bundler, composer, Go |
| 6 | **Web Security** | Missing headers (CSP, HSTS), CSRF, cookie flags, open redirects |
| 7 | **Supply Chain** | Lock file integrity, dependency confusion, unpinned versions |
| 8 | **CI/CD Security** | GitHub Actions injection, permissive permissions, secret exposure |
| 9 | **Docker/Container** | Root user, unpinned images, secrets in layers, privileged mode |
| 10 | **Error Handling** | Debug in prod, stack traces, empty catch blocks |
| 11 | **Logging Security** | Sensitive data in logs, log injection, missing security events |

## Steps

### Phase 1: Reconnaissance
1. Detectar tech stack (Node/Python/Go/Rust/etc.)
2. Detectar frameworks (Express, FastAPI, Django, Next.js, etc.)
3. Estimar scope: small (<1K files), medium (1-10K), large (10K+)
4. Aplicar tier de escaneo segun scope

### Phase 2: Parallel Analysis (5 subagentes)
1. **Subagent 1**: Dependency vulnerabilities + supply chain
2. **Subagent 2**: Code patterns (SAST) + crypto
3. **Subagent 3**: Secret detection (60+ patterns batch scan)
4. **Subagent 4**: Auth + web security + config
5. **Subagent 5**: CI/CD + Docker + error handling + logging

### Phase 3: Report Generation
1. Deducir hallazgos duplicados
2. Clasificar por CVSS (Critical 9.0+, High 7.0+, Medium 4.0+, Low 1.0+, Info)
3. Mapear a OWASP 2025 y CWE Top 25
4. Generar executive summary con risk score
5. Ordenar por severidad
6. Incluir remediation concreta para cada finding
7. Guardar en `docs/security-reports/<project>-<date>.md`

## Severity Scoring (CVSS-aligned)

| Nivel | Score | Accion |
|-------|-------|--------|
| Critical | 9.0-10.0 | Fix inmediato. Bloquea deploy |
| High | 7.0-8.9 | Fix antes del proximo deploy |
| Medium | 4.0-6.9 | Fix en este sprint |
| Low | 1.0-3.9 | Fix cuando sea posible |
| Info | 0.0-0.9 | Considerar mejora |

## OWASP 2025 Top 10 Coverage

| ID | Categoria | Nuestros dominios |
|----|-----------|-------------------|
| A01 | Broken Access Control | Auth & Authorization (#2) |
| A02 | Security Misconfiguration | Web Security (#6) + Error Handling (#10) |
| A03 | Supply Chain Failures | Supply Chain (#7) + CI/CD (#8) |
| A04 | Cryptographic Failures | Crypto (#3) + Secrets (#4) |
| A05 | Injection | Code Security (#1) |
| A06 | Insecure Design | Auth (#2) + Web (#6) |
| A07 | Authentication Failures | Auth & Authorization (#2) |
| A08 | Data Integrity Failures | Supply Chain (#7) |
| A09 | Logging/Monitoring Failures | Logging (#11) |
| A10 | Exceptional Conditions | Error Handling (#10) |

## Best Practices

### Secret patterns (top 10)

```regex
# AWS Key
AKIA[0-9A-Z]{16}

# Stripe Key
sk_live_[0-9a-zA-Z]{24}

# GitHub Token
ghp_[0-9a-zA-Z]{36}

# Slack Webhook
https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+

# Private Key
-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----

# JWT Token
eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}

# Database URL
(mysql|postgres|mongodb|redis)://[^:]+:[^@]+@

# Generic API Key
(api[_-]?key|apikey|secret|token|password)\s*[:=]\s*['"][A-Za-z0-9_\-]{20,}['"]

# Google API Key
AIza[0-9A-Za-z\-_]{35}

# OpenAI Key
sk-[A-Za-z0-9]{32,}
```

### Remediation template

Cada finding debe incluir:
```
[ID] Titulo del finding
Severity: Critical/High/Medium/Low CVSS X.X
CWE: CWE-XXX (Description)
OWASP: AXX:2025 (Category)
Location: archivo:linea

Description: que esta mal y por que

Evidence: (codigo vulnerable)

Remediation: (codigo arreglado, paso a paso)

References: links a CWE, OWASP, docs relevantes
```

### Integracion con Dopa Code

- Si el proyecto es DopaWeb, verificar guardrails ERP adicionales
- Si el proyecto usa Dopa como backend, verificar isolation multi-tenant
- El reporte se integra con el PostMortem del job
- Findings criticos bloquean deploy via PreDeployAudit
