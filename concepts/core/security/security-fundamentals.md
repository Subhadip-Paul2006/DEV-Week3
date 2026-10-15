---
id: foundation.security-fundamentals
category: foundation
owning_agent: F-20
maturity: stable
languages:
- any
tags:
- owasp
- auth
- injection
- input-validation
- xss
- csrf
- secrets
- encryption
- authentication
- authorization
- security
related:
- foundation.observability
- foundation.client-server
- foundation.circuit-breaker
- foundation.caching
- foundation.fault-tolerance
domain: core
---

# Security Fundamentals

## 1. Overview

Security fundamentals are the foundational principles, threat categories, and defensive mechanisms that must be applied at every layer of a software system — from input validation at the API boundary to access control in the data layer to secrets management in the deployment layer. A system is only as secure as its weakest link, which means security is not a feature you add at the end — it is a quality attribute embedded in every design decision. This concept covers the three pillars of application security: authentication (who you are), authorization (what you can do), and data protection (keeping secrets secret and data private). It covers the OWASP Top 10 threat categories, the most common exploit patterns, how to defend against them, and how to verify with static analysis.

## 2. Core Principles

1. **Never trust client input** — all input is hostile until validated; network calls, form data, API payloads, file uploads, headers, cookies, and internal service calls can all be attack vectors.
2. **Defense in depth** — every layer must validate: input validation at the API boundary, parameterized queries at the database layer, output encoding at the rendering layer.
3. **Fail securely** — a system that encounters an unexpected error during a security check must default to *deny*, not *allow*.
4. **Secrets never touch source control** — passwords, API keys, TLS certificates, and tokens must be injected at runtime via a secrets manager.
5. **Least privilege** — every user, service account, database role, and IAM policy must have the minimum permissions needed to perform its function and nothing more.
6. **Audit everything security-relevant** — authentication attempts, authorization decisions, privilege escalations, and access to sensitive data must produce immutable audit logs.
7. **Keep it simple, keep it auditable** — prefer well-understood, battle-tested libraries to custom crypto.

## 3. Sub-Concepts

### 3.1 Authentication (Who You Are)

**Definition:** The process of verifying the identity of a principal (user, service account, device). The result is a credential that the system can trust.

**Mechanisms:**
- **Password-based** — must be hashed with bcrypt or Argon2id; never plaintext, never MD5/SHA-256.
- **Token-based** — JWT (signed, RS256), opaque bearer tokens.
- **Session-based** — server-side session store (Redis) with HttpOnly cookie.
- **OAuth 2.0 / OIDC** — delegated authorization; Authorization Code, Client Credentials, Refresh Token grant types.
- **mTLS** — both parties present certificates; service-to-service auth.
- **API Keys** — pre-shared secret; only for machine-to-machine.

```python
# CORRECT: Argon2id password hashing
import argon2
hasher = argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
hash = hasher.hash(password)
hasher.verify(hash, password_attempt)

# CORRECT: JWT validation (RS256, verify all claims)
import jwt
claims = jwt.decode(
    token, PUBLIC_KEY, algorithms=["RS256"],
    audience="my-api", issuer="https://auth.mycompany.com",
    options={"require": ["exp", "iat", "aud", "iss"]},
)
if claims["exp"] < datetime.now(timezone.utc).timestamp():
    raise AuthenticationError("token expired")
if revoke_store.is_revoked(claims["jti"]):
    raise AuthenticationError("token revoked")
```

### 3.2 Authorization (What You Can Do)

**Definition:** Determining whether an authenticated principal has permission to perform an operation on a resource.

**Models:**
- **ACL** — list of principals and their permissions per resource. Simple, doesn't scale per-object.
- **RBAC** — permissions assigned to roles; users assigned to roles. Scales well.
- **ABAC** — policies evaluate attributes (role, resource type, time, IP). Most flexible.
- **ReBAC** — permissions based on relationships between resources. Used by GitHub, Google Drive.

```python
# RBAC in Python
class Role(Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

PERMISSIONS = {
    Role.ADMIN:  ["read", "write", "delete", "manage_users", "manage_billing"],
    Role.EDITOR: ["read", "write"],
    Role.VIEWER: ["read"],
}

def check_permission(user: User, action: str) -> bool:
    return action in PERMISSIONS.get(user.role, [])
```

```go
// ABAC with OPA/Rego
// policy.rego
package org.authz
default allow = false
allow { input.user.role == "admin" }
allow { input.user.id == input.resource.owner_id; input.action == "write" }
allow { input.user.team_id == input.resource.team_id; input.action == "read" }
```

### 3.3 Injection Attacks

**Definition:** Untrusted input sent to an interpreter as part of a command or query. Changes the intended command.

**SQL Injection — #1 vulnerability:**

```python
# WRONG: string concatenation — SQL INJECTION
query = f"SELECT * FROM users WHERE id = '{user_id}'"
cursor.execute(query)
# Attacker: user_id = "1' OR '1'='1" → returns ALL users

# CORRECT: parameterized query
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

```go
// CORRECT: parameterized query
func getUser(db *pgx.Conn, userID string) (*User, error) {
    var user User
    err := db.QueryRow(ctx,
        "SELECT id, email, name FROM users WHERE id = $1", userID).Scan(
        &user.ID, &user.Email, &user.Name)
    return &user, err
}
```

**Command Injection:**
```python
# WRONG: shell=True with untrusted input
subprocess.run(f"cat /uploads/{filename}", shell=True)
# Attacker: filename = "; rm -rf /"

# CORRECT: list form, validate input
if not re.match(r'^[\w\-\.]+$', filename):
    raise ValueError("invalid filename")
result = subprocess.run(["cat", f"/uploads/{filename}"], capture_output=True)
```

**NoSQL Injection:**
```python
# WRONG
db.users.find({"email": email})
# Attacker: {"$ne": ""} → leaks all users

# CORRECT: validate format first
if not re.match(r'^[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}$', email or ""):
    raise ValueError("invalid email")
users = db.users.find({"email": email})
```

### 3.4 Cross-Site Scripting (XSS)

**Definition:** Attacker injects malicious scripts into web pages viewed by other users.

**Types:** Stored (malicious script stored in DB), Reflected (script in URL, reflected in response), DOM-based (JS processes untrusted input and writes to DOM).

**Prevention:**
- Encode output (HTML encoding for HTML, JS encoding for JS).
- CSP header: `Content-Security-Policy: default-src 'self'`.
- Template auto-escaping (Jinja2, React JSX, Vue templates).
- HttpOnly cookies: `Set-Cookie: session=...; HttpOnly; Secure; SameSite=Strict`.

```python
# WRONG
return f"<h1>Welcome, {user_name}!</h1>"   # user_name could be <script>alert(1)</script>

# CORRECT: Jinja2 auto-escapes
return render_template("profile.html", user_name=user_name)
```

### 3.5 Cross-Site Request Forgery (CSRF)

**Definition:** Attacker tricks an authenticated user's browser into making a state-changing request.

**Prevention:**
- CSRF tokens (server generates per session, embedded in form, verified on POST).
- SameSite cookie attribute: `SameSite=Strict` or `Lax`.
- Custom request headers (`X-CSRF-Token`, `X-Requested-With: XMLHttpRequest`).

```python
# CORRECT: Flask-WTF CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
# Template includes {{ csrf_token() }} — validated on POST automatically
```

### 3.6 Input Validation

**Definition:** Validating all external input for type, format, range, and business rules before processing.

```python
# CORRECT: Pydantic multi-layer validation
from pydantic import BaseModel, EmailStr, Field, field_validator

class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    age: int = Field(ge=13, le=150)

    @field_validator("username")
    @classmethod
    def no_reserved_usernames(cls, v):
        if v.lower() in {"admin", "root", "system"}:
            raise ValueError("username is reserved")
        return v

    @field_validator("email")
    @classmethod
    def no_disposable_email(cls, v):
        domain = v.split("@")[-1]
        if domain in {"mailinator.com", "guerrillamail.com"}:
            raise ValueError("disposable emails not allowed")
        return v
```

```typescript
// CORRECT: Zod validation (TypeScript)
import { z } from "zod";
const CreateUserSchema = z.object({
    email: z.string().email().max(255),
    username: z.string().min(3).max(30).regex(/^[a-zA-Z0-9_-]+$/),
    age: z.number().int().min(13).max(150),
});
```

### 3.7 Cryptography (Encryption, Hashing, Signing)

**Definition:** Cryptographic algorithms protecting data confidentiality, integrity, and authenticity.

**Key rules:**
- Never roll your own crypto.
- AES-GCM for symmetric encryption.
- RSA-OAEP or ECDSA for asymmetric signing.
- HMAC-SHA256 for message authentication.
- Never reuse IVs/nonces with AES-GCM.
- Use constant-time comparison for secrets (`compare_digest`, `timingSafeEqual`).

```python
# CORRECT: AES-GCM (Python)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_data(plaintext: bytes, key: bytes) -> bytes:
    nonce = os.urandom(12)               # NEVER reused with same key
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext            # prepend nonce for decryption
```

```typescript
// CORRECT: HMAC with constant-time comparison (Node.js)
import crypto from "crypto";

function verifySignature(payload: string, signature: string, secret: string): boolean {
    const hmac = crypto.createHmac("sha256", secret);
    const expected = hmac.update(payload).digest("hex");
    return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

### 3.8 Secrets Management

**Definition:** Lifecycle management of sensitive credentials — creation, storage, rotation, distribution.

**Rules:**
- Never commit secrets. Use `.gitignore` and `gitleaks`/`detect-secrets`.
- Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager).
- Short-lived credentials (IAM roles, workload identity).
- Rotate secrets regularly (30-90 days).
- Encrypt at rest (envelope encryption).

```python
# CORRECT: AWS Secrets Manager
import boto3, json
secrets_client = boto3.client("secretsmanager")
secret = secrets_client.get_secret_value(SecretId="prod/database/credentials")
creds = json.loads(secret["SecretString"])

# WRONG: hardcoded
DATABASE_PASSWORD = "p@ssw0rd123"   # NEVER
```

### 3.9 SSRF (Server-Side Request Forgery)

**Definition:** Attacker tricks a server into making a request to an arbitrary destination (internal services, cloud metadata endpoints).

```python
# CORRECT: SSRF protection
import ipaddress, urllib.parse

PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # cloud metadata
]
ALLOWED_SCHEMES = {"https"}
ALLOWED_HOSTS = {"api.stripe.com", "api.github.com"}

def is_url_safe(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"scheme {parsed.scheme} is not allowed")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"host {parsed.hostname} is not allowed")
    ip = socket.gethostbyname(parsed.hostname)
    if any(ipaddress.ip_address(ip) in net for net in PRIVATE_RANGES):
        raise ValueError(f"resolved IP {ip} is in a private range")
    return True
```

### 3.10 Rate Limiting and Abusive Traffic

**Definition:** Limiting the number of requests a client can make in a time window.

**Algorithms:**
- **Token Bucket** — N tokens refill at fixed rate; allows burstiness.
- **Sliding Window** — count in rolling window; more accurate than fixed.
- **Fixed Window** — count in fixed windows; simple, boundary-burst vulnerable.

```python
# Token Bucket with Redis
r = redis.Redis(host="localhost", port=6379)

def rate_limit(key: str, limit: int, window: int) -> bool:
    bucket_key = f"rate_limit:{key}"
    current = r.get(bucket_key)
    if current is None or int(current) < limit:
        r.incr(bucket_key, 1)
        if current is None:
            r.expire(bucket_key, window)
        return True
    return False

def check_rate_limit(user_id: str):
    if not rate_limit(user_id, limit=100, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Password hashing library (argon2, bcrypt) | any | regex: `from argon2\|import bcrypt\|require bcrypt` | High |
| JWT validation with key/secret | Python/TS/Go | regex: `decode\(.*key=\|verify\(.*secret\|jwt.verify` | High |
| Session store (Redis, database) | any | regex: `Session\(\)\|session_store` | Medium |
| Parameterized SQL queries | any | regex: `execute\(.*%s\|execute\(.*\$1\|\?\|:name` | High |
| ORM used for all DB access | any | regex: `from sqlalchemy\|typeorm\|prisma` | Medium |
| CSP header set | any | regex: `Content-Security-Policy` in response headers | High |
| HttpOnly / Secure / SameSite cookie | any | regex: `HttpOnly\|Secure\|SameSite` | High |
| CSRF token middleware | any | regex: `CSRFProtect\|csrf_token\|csrf()` | Medium |
| Input validation library | Python/TS/Go | regex: `pydantic\|zod\|class-validator\|go-playground/validator` | High |
| Secrets manager client imported | Python/TS/Go | regex: `from boto3\|secretsmanager\|google.cloud.secretmanager` | Medium |
| URL allowlist validation | any | regex: `is_url_safe\|PRIVATE_RANGES\|allowed_hosts` | Medium |
| AES-GCM encryption | Python/TS/Go | regex: `AESGCM\|NewGCM\|createCipheriv` | Medium |
| HMAC with constant-time compare | Python/TS/Go | regex: `compare_digest\|timingSafeEqual` | Medium |
| `.gitignore` contains `.env` | any | glob: `.gitignore` with `.env` | High |
| `gitleaks` or `detect-secrets` in CI | YAML | regex: `gitleaks\|detect-secrets\|truffleHog` | Medium |
| OAuth/OIDC configuration | any | regex: `client_id\|client_secret\|oauth2` | High |
| ABAC/OPA policy check | any | regex: `rego\|opa.evaluate\|policy.check` | Medium |
| SSRF URL validation | any | regex: `PRIVATE_RANGES\|is_url_safe\|allowed_hosts` | Medium |
| Rate limiter middleware | any | regex: `rate_limit\|RateLimiter\|token_bucket` | Medium |
| CORS with allowlist (not `*`) | any | regex: `Access-Control-Allow-Origin` without wildcard | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No password hashing in auth service | any | absence of `argon2`, `bcrypt`, `pbkdf2` | High |
| No parameterized queries | any | regex: `f"SELECT\|f'SELECT` with interpolation | High |
| No input validation in API service | any | absence of pydantic/zod/joi/validator | High |
| No CSP header in web app | any | absence of `Content-Security-Policy` | High |
| No HttpOnly / Secure on cookies | any | `Set-Cookie` without `HttpOnly` | High |
| No CSRF token on POST/PUT/DELETE | any | absence of CSRF middleware | Medium |
| No secrets manager; `.env` in Git | any | `.env` file in repo; hardcoded `API_KEY =` | High |
| No URL validation before HTTP fetch | any | `requests.get(url)` without validation | Medium |
| No rate limiting on public API | any | absence of rate limiter on public endpoints | High |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| JWT decoded with `verify=False` | Python/TS/Go | regex: `verify_signature.*False\|verify=False` | High |
| bcrypt with rounds < 10 | Python/Go | regex: `bcrypt.gensalt(rounds=\d\)` < 10 | High |
| MD5 or SHA-1 for password hashing | any | regex: `hashlib.md5\|hashlib.sha1\|md5.new` | High |
| AES in ECB mode | Python | regex: `AES.MODE_ECB` | High |
| SQL string concatenation | any | regex: `f"SELECT.*{var}"` | High |
| `shell=True` in subprocess | Python | regex: `shell=True` | High |
| `innerHTML` / `v-html` with dynamic content | any | regex: `innerHTML\|v-html\|dangerouslySetInnerHTML` | Medium |
| CSP with `'unsafe-inline'` or `'unsafe-eval'` | any | regex: `'unsafe-inline'\|'unsafe-eval'` in CSP | Medium |
| SameSite=None without Secure | any | regex: `SameSite=None` without `Secure` | Medium |
| Secrets in source code | any | regex: `AKIA[0-9A-Z]{16}\|ghp_\|sk_live_\|-----BEGIN.*PRIVATE KEY` | High |
| Open CORS with `*` | any | regex: `Access-Control-Allow-Origin.*\*` | Medium |
| TLS 1.0 or 1.1 | any | regex: `tls_min_version.*1.0\|ssl_protocols.*SSLv3` | High |
| Default admin/admin credentials | any | regex: `"admin"\s*:\s*"admin"` | High |

## 5. Anti-Patterns

#### Anti-Pattern: Insecure Password Storage

```python
# WRONG: plaintext
db.execute("INSERT INTO users VALUES (%s, %s)", (username, password))
# WRONG: fast hash (SHA-256)
hashed = hashlib.sha256(password.encode()).hexdigest()
```

**Fix:** Use Argon2id with memory >= 64MB, time >= 2, parallelism >= 2.

#### Anti-Pattern: String Concatenation for SQL

```python
# WRONG
query = f"SELECT * FROM orders WHERE user_id = '{user_id}'"
cursor.execute(query)
```

**Fix:** Always use parameterized queries.

#### Anti-Pattern: Trusting Internal Service Calls

```python
@app.post("/api/internal/process-payment")
def process_payment(data: dict):
    process_payment_logic(data)   # no auth check
```

**Fix:** Enforce mTLS between services or include signed internal tokens.

#### Anti-Pattern: No Input Validation on File Uploads

```python
@app.post("/upload")
def upload(file):
    file.save(f"/uploads/{file.filename}")   # no validation
```

**Fix:** Validate extension, MIME type, actual content (magic numbers). Store outside web root.

#### Anti-Pattern: Overly Permissive IAM

```hcl
policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"   # for a Lambda
```

**Fix:** Create least-privilege IAM policies. Use AWS IAM Access Analyzer.

#### Anti-Pattern: Secrets in Git History

```bash
git commit -m "add config"  # includes API_KEY=sk_live_...
echo "API_KEY=sk_live_..." >> .gitignore  # too late
```

**Fix:** Use `git secret`/`blackbox` for encrypted secrets. Use `git filter-branch` or `BFG` to purge secrets.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `password_hashing.algorithm` | string | "bcrypt" | "argon2id" | Password hashing algorithm |
| `password_hashing.argon2.memory_kb` | int | 65536 | 65536 (64 MB) | Memory hardness |
| `password_hashing.argon2.time_cost` | int | 2 | 2–3 | Iterations |
| `password_hashing.bcrypt.rounds` | int | 12 | 12–14 | 2^12 = 4096 rounds |
| `session.cookie.httponly` | bool | true | true | Prevents JS access to cookie |
| `session.cookie.secure` | bool | true | true (prod), false (dev) | Only over HTTPS |
| `session.cookie.samesite` | string | "lax" | "strict" (most sensitive) | CSRF protection |
| `jwt.algorithm` | string | "RS256" | "RS256" (asymmetric) | JWT signing algorithm |
| `jwt.expiry_seconds` | int | 900 | 900 (15m access tokens) | Access token TTL |
| `cors.allowed_origins` | list | [] | specific origins (never `*`) | CORS origin allowlist |
| `rate_limit.requests_per_window` | int | 100 | 100–1000 | Requests per window |
| `rate_limit.window_seconds` | int | 60 | 60 | Rate limit window |
| `tls.min_version` | string | "TLSv1.2" | "TLSv1.3" (preferred) | Minimum TLS version |
| `secrets.rotation_days` | int | 90 | 30–90 | How often secrets are rotated |
| `secrets.manager` | string | "none" | "vault"/"aws_secrets_manager"/"gcp_secret_manager" | Secrets backend |
| `security_scan.tools` | list | [] | `[bandit, semgrep, gitleaks, snyk, trivy]` | Security scanning tools |

## 7. Integration Points

- **Observability** — security events (auth failures, privilege changes, SSRF attempts) must be logged with structured fields and correlated with trace IDs.
- **HLD** — security boundaries (DMZ, private VPC, security groups, WAF) are defined at the HLD layer.
- **Circuit Breaker** — brute-force attacks should trip a circuit breaker (lockout after N failed auth attempts from same IP).
- **Rate Limiting** — rate limiters often use Redis as a fast counter store; `rate_limit:*` keys share infrastructure with other caches.
- **Client-Server** — TLS termination typically at load balancer; downstream services may use mTLS.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Failed login attempts (rate) | Prometheus | > 5/min from same IP → warn, > 50/min → page | Block IP; check credential stuffing |
| Account lockout rate | Prometheus | > 10/hr → warn | Check brute-force; review lockout policy |
| CSRF token validation failure rate | Prometheus | > 1% → warn | Check for broken client |
| Rate limit rejection rate | Prometheus | > 30% of traffic → warn | Adjust limits or investigate abuse |
| Secret rotation age (days) | Custom | > rotation_days → warn | Rotate secrets |
| PII logged (count) | Loki / Splunk | Any → page | Stop; investigate log pipeline |
| TLS certificate expiry (days) | Prometheus / cert-manager | < 30 days → warn, < 7 days → page | Renew certificate |

**Log events that must be emitted:**
- Every authentication attempt (success and failure) with user_id, IP, method, timestamp, outcome.
- Every authorization failure with user_id, resource, action, reason.
- Every secret access (who accessed the vault, which secret).
- Every privilege escalation (role change, permission grant).
- Every rate limit hit with client IP, endpoint, limit, current count.

## 9. Evolution / Version Tracking

**1990s–2000s — Perimeter security:** Firewalls and VPNs were the primary defense. The internal network was trusted. "We don't need to authenticate internal service calls" was standard.

**2005–2010 — OWASP Top 10:** The OWASP Top 10 gave developers a concrete, prioritized list of vulnerabilities. Password hashing with bcrypt replaced MD5. Input validation libraries became mainstream.

**2013 — Password hashing evolution:** SHA-1 deprecated. bcrypt became the minimum acceptable standard. Argon2 (2015) became the gold standard.

**2015–2018 — OAuth 2.0 / JWT era:** JWT became the de-facto standard. OAuth 2.0 and OIDC became the identity framework. JWT is often misused (no signature verification, infinite expiry, no revocation).

**2018–2021 — Zero Trust:** Google's BeyondCorp (2014) popularized "never trust, always verify." mTLS for service-to-service communication becomes standard.

**2022–present — Passwordless and passkeys:** FIDO2/WebAuthn gains adoption. Apple, Google, and Microsoft ship passkey support. Hardware-backed, phishing-resistant credentials.

**Emerging patterns:** Passkeys/FIDO2; IAM Roles Anywhere / Workload Identity; Policy-as-Code (OPA); Supply-chain security (SBOM, sigstore, SLSA); SSRF protection by default (IMDSv2); Chaos Engineering for security.

**Deprecated patterns:** MD5/SHA-1 for passwords; Session IDs in URL query parameters; IP-based trust; Custom cryptography; Static admin passwords; `*` CORS wildcard.

## 10. References

- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [NIST SP 800-63 — Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)
- [Argon2 — Password Hashing Competition Winner](https://github.com/P-H-C/phc-winner-argon2)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [HashiCorp Vault Documentation](https://developer.hashicorp.com/vault/docs)
- [CSP — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy)
- [WebAuthn — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)
- [OpenPolicyAgent Documentation](https://www.openpolicyagent.org/docs/)
- [gitleaks — Secret Scanning](https://github.com/gitleaks/gitleaks)
- [detect-secrets — Yelp](https://github.com/Yelp/detect-secrets)
- [The Tangled Web — Michal Zalewski](https://nostarch.com/tangledweb)