# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Ishani-Core / TechBuzz AI, please report it responsibly:

1. **Email:** piyushmani33@gmail.com
2. **Subject line:** `[SECURITY] Ishani-Core — <brief description>`
3. **Do NOT** open a public GitHub issue for security vulnerabilities.

You can expect:
- Acknowledgement within **48 hours**
- A fix or mitigation plan within **7 days** for critical issues
- Credit in the changelog (unless you prefer anonymity)

## Security Best Practices

- **Never commit `.env` files** — use `.env.example` as a template
- **Rotate API keys** if you suspect they have been exposed
- **Use HTTPS** in production deployments
- **Keep dependencies updated** — review Dependabot alerts regularly
- All SQL queries are **parameterised** and **scoped to `user_id`**

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch (latest) | ✅ |
| Older commits | ❌ |
