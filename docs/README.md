# 🚀 Auth Service (Production-Grade Identity & Access Management)

A production-ready authentication and authorization service built using **FastAPI**, designed for scalability, security, and enterprise-grade identity management.

## ✨ Features

### 🔐 Authentication
- JWT-based authentication
- Refresh token rotation
- Token blacklisting
- Magic link login (passwordless)
- OTP login (SMS/Email)

### 🔒 Multi-Factor Authentication (MFA)
- TOTP (Authenticator apps)
- Recovery codes
- WebAuthn (biometric / passkeys)

### 🌐 OAuth Providers
- Google OAuth
- GitHub OAuth
- Microsoft OAuth

### 🧠 Authorization (RBAC)
- Role-based access control
- Permission management
- Admin APIs

### 📱 Session & Device Management
- Multi-device login support
- Device fingerprinting
- Active session tracking
- Force logout (all devices)

### 🛡️ Security
- Rate limiting (Redis + Lua scripts)
- Token versioning
- Secure password hashing
- OAuth state validation

### 📊 Observability
- Prometheus metrics
- Grafana dashboards
- Structured logging
- Distributed tracing

### 🧾 Audit System
- User activity tracking
- Async audit worker

## 🏗️ Architecture
- **FastAPI** (Backend API)
- **PostgreSQL** (Primary DB)
- **Redis** (Caching, Rate limiting, OTP)
- **Prometheus + Grafana** (Monitoring)
- **Docker + Kubernetes** (Deployment)

## 📂 Project Structure

```markdown
app/
├── api/            # API routes (auth, admin, health)
├── services/       # Business logic
├── repositories/   # DB access layer
├── models/         # SQLAlchemy models
├── security/       # JWT, rate limiting, token logic
├── auth_providers/ # OAuth & login providers
├── middleware/     # Rate limit, logging
├── observability/  # Metrics, tracing
├── cache/          # Redis client
├── workers/        # Async background jobs

``` 


## ⚙️ Local Setup
```bash
git clone <repo>
cd auth-service
cp .env.example .env
docker-compose up --build
```

## 🧪 Run Tests
```bash
pytest --cov=app --cov-report=term-missing
```

## 🔄 CI/CD

### CI (GitHub Actions)
- Linting
- Unit & Integration Tests
- Coverage checks

### CD
- Docker image build
- Kubernetes deployment

## ☸️ Kubernetes Deployment
Located in:

```markdown 
k8s/
├── deployment.yaml
├── service.yaml
├── postgres.yaml
├── redis.yaml
├── prometheus.yaml
├── grafana.yaml

```

## 📊 Observability
- Prometheus metrics endpoint
- Grafana dashboards
- Request tracing & logging

## 🔐 Auth Flows
Detailed flows available in: `docs/auth/`

## 📡 API Documentation
Available via Swagger UI: `/docs`

## 🚀 Future Improvements
- Multi-tenant support
- SSO (SAML / OIDC)
- Fine-grained policy engine (ABAC)
- Risk-based authentication

## 👨‍💻 Author
**Santosh Kumar Bharty**
