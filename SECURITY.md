# Security Policy

## Reporting Security Vulnerabilities

We take security vulnerabilities seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please send an email to: **security@agentmarketplace.com**

Please include the following information:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment of the vulnerability

### Response Timeline

- **Initial Response**: Within 48 hours, we will acknowledge receipt of your report
- **Status Update**: Within 7 days, we will provide a more detailed timeline for the fix
- **Resolution**: We aim to release a fix within 30 days, depending on complexity

## Security Best Practices

### For Users

1. **Keep your `SECRET_KEY` confidential**
   - Never commit it to version control
   - Use strong, randomly generated keys
   - Rotate keys periodically

2. **Use HTTPS/WSS in production**
   - Always use `wss://` for WebSocket connections
   - Configure TLS certificates

3. **Monitor your agents**
   - Review logs regularly
   - Set up alerts for unusual activity

### For Developers

1. **Input Validation**
   - Never trust user input
   - Use Pydantic models for validation
   - Sanitize all data before processing

2. **Authentication**
   - Implement proper token validation
   - Use short-lived access tokens
   - Implement token refresh mechanisms

3. **Rate Limiting**
   - Enable rate limiting in production
   - Configure appropriate thresholds

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | ✅ Full Support    |
| 1.x     | ⚠️ Security Only  |
| < 1.0   | ❌ Not Supported   |

## Security Updates

We will publish security updates as patch releases. We recommend always using the latest version.

---

Thank you for helping keep Agent Marketplace secure! 🔐
