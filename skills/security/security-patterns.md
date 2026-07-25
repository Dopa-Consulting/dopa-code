# Security Patterns Reference — Dopa Code

Adaptado de Hainrixz/cyber-neo (MIT). Patrones clave de seguridad para auditoria de codigo.

## SQL Injection

**Pattern**: concatenacion de user input en queries SQL

Vulnerable:
```javascript
const query = `SELECT * FROM users WHERE id = ${req.params.id}`;
```

Seguro:
```javascript
const query = 'SELECT * FROM users WHERE id = $1';
const result = await db.query(query, [req.params.id]);
```

## XSS (Cross-Site Scripting)

**Pattern**: user input renderizado sin sanitizar

Vulnerable:
```jsx
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

Seguro:
```jsx
<div>{userInput}</div>
// o sanitizar con DOMPurify
```

## Hardcoded Secrets

**Pattern**: credenciales en codigo fuente

```javascript
// VULNERABLE
const apiKey = "sk-live-abc123...";
const dbPassword = "admin123";

// SEGURO
const apiKey = process.env.API_KEY;
const dbPassword = process.env.DB_PASSWORD;
```

## Missing Auth Middleware

Vulnerable:
```javascript
app.get('/api/admin/users', (req, res) => {
    res.json(users);  // sin auth
});
```

Seguro:
```javascript
app.get('/api/admin/users', authenticate, requireRole('admin'), (req, res) => {
    res.json(users);
});
```

## Weak Cryptography

Vulnerable: MD5, SHA1 para passwords
Seguro: bcrypt, argon2, scrypt

## JWT Misconfigurations

- `algorithm: 'none'` — permite bypass
- Sin expiracion — token valido para siempre
- Secreto debil — `secret` o `password` como JWT secret

## Debug Mode in Production

```python
# VULNERABLE
app.run(debug=True)

# SEGURO
app.run(debug=os.getenv('DEBUG', 'False').lower() == 'true')
```
