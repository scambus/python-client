# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@scambus.net**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Security Best Practices for Users

### API Key Security

1. **Never commit API keys** to version control
   ```bash
   # Use environment variables
   export SCAMBUS_API_KEY="your-key-here"
   ```

2. **Use different API keys** for different environments (dev, staging, production)

3. **Rotate API keys** regularly and immediately if compromised

4. **Limit API key permissions** to only what's needed

### Client Configuration

1. **Always use HTTPS** endpoints:
   ```python
   client = ScambusClient(
       api_url="https://api.scambus.net/api",  # HTTPS, not HTTP
       api_token="your-token"
   )
   ```

2. **Set appropriate timeouts** to prevent hanging connections:
   ```python
   client = ScambusClient(
       api_url="https://api.scambus.net/api",
       api_token="your-token",
       timeout=30  # 30 seconds
   )
   ```

3. **Validate inputs** before sending to API:
   ```python
   # Sanitize user inputs
   description = user_input.strip()[:1000]  # Limit length
   ```

### Data Handling

1. **Sanitize sensitive data** before logging or displaying
2. **Use secure communication channels** for transmitting API keys
3. **Store credentials securely** using system keychains or secret managers
4. **Implement rate limiting** in your applications

### Dependencies

1. **Keep the client updated**:
   ```bash
   pip install --upgrade scambus-client
   ```

2. **Monitor security advisories**:
   - Watch this repository for security updates
   - Enable GitHub security alerts
   - Subscribe to release notifications

3. **Audit dependencies** regularly:
   ```bash
   pip list --outdated
   pip-audit  # If you have pip-audit installed
   ```

## Security Features

### Built-in Security

- **HTTPS-only** communication
- **Request timeouts** to prevent hanging connections
- **Input validation** on client side
- **Secure credential handling** with environment variable support
- **No credential logging** in debug output
- **TLS certificate verification** enabled by default

### Dependencies

We maintain minimal dependencies to reduce attack surface:
- `requests` - HTTP client with security updates
- `websockets` - WebSocket client for real-time features

All dependencies are regularly updated to patch security vulnerabilities.

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported via email
2. **Day 1-2**: Initial response and triage
3. **Day 3-7**: Investigate and develop fix
4. **Day 7-14**: Test and validate fix
5. **Day 14**: Coordinated disclosure
   - Security patch released
   - Security advisory published
   - CVE assigned if applicable

## Security Updates

Security updates are released as:
- **Patch versions** (e.g., 0.1.1) for minor security fixes
- **Minor versions** (e.g., 0.2.0) for security fixes requiring changes
- **Security advisories** on GitHub for critical vulnerabilities

Subscribe to releases on GitHub to stay informed.

## Security Hall of Fame

We acknowledge security researchers who responsibly disclose vulnerabilities:

<!-- List of contributors will appear here -->

*No vulnerabilities have been reported yet.*

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Scambus Security Documentation](https://docs.scambus.net/security)

## Contact

For security concerns: **security@scambus.net**

For general questions: [GitHub Discussions](https://github.com/scambus/scambus-python-client/discussions)

---

*This security policy is subject to change. Last updated: November 11, 2025*
