# Post-Exploitation & Impact Analysis

**Application:** OJT Monitoring System
**Framework:** Django 4.2 + DRF 3.14, ASGI (Daphne), SQLite
**Date:** July 13, 2026

---

## 1. Attack Chain Scenarios

### Scenario A: Low-Privilege Student → Coordinator (Privilege Escalation)

```
Step 1  Attacker registers as student, gains Token auth
Step 2  Attacker calls PATCH /api/student/profiles/me/
        → mass-assignment on "role" field (no serializer restrict)
Step 3  Attacker self-assigns role="coordinator" + creates OJTProgram
Step 4  Attacker approves own OJTApplication
Step 5  Attacker has coordinator privileges; accesses coordinator dashboard
```

**Impact:** Full compromise of OJT approval workflow. Attacker can create fake programs, approve arbitrary students, and access coordinator endpoints.

### Scenario B: Face Verification Bypass (Attendance Fraud)

```
Step 1  Attacker obtains a photo of victim student
Step 2  Attacker calls POST /api/student/face/register/
        → registers victim's face under attacker's account
Step 3  Attacker calls POST /api/student/face/verify/
        → passes face check because it matches attacker's stored face
Step 4  Attacker calls POST /api/student/attendance/check-in/
        → attendance recorded with location + timestamp
Step 5  Attacker clocks out normally; no physical presence required
```

**Impact:** Attacker can accumulate attendance records without physical presence, defrauding the OJT program of required hours.

### Scenario C: Token Theft via CORS Misconfiguration → Full Account Takeover

```
Step 1  Attacker hosts malicious page on attacker-controlled origin
Step 2  CORS misconfiguration: CORS_ALLOW_ALL_ORIGINS=True or permissive whitelist
Step 3  Victim (coordinator/admin) visits attacker page while logged in
Step 4  Attacker JS reads auth_token from cookie (if not httpOnly)
        OR exploits CSRF on token-authenticated endpoints
Step 5  Attacker replays token from own browser → full account access
```

**Impact:** Complete account takeover of any user (coordinator or admin) whose token is captured.

---

## 2. Data Exposure Analysis

| Model | Fields at Risk | Sensitivity | Attack Vector |
|---|---|---|---|
| `User` | `email`, `phone_number`, `profile_picture`, `faculty_id` | **High** — PII | IDOR on `/api/auth/register/` or profile endpoints |
| `StudentProfile` | `student_id`, `GPA`, `enrollment_status`, `address`, `resume` | **High** — academic + financial PII | Unrestricted profile read via token auth |
| `FacialRecognition` | `face_encoding` (512-d float blob), `face_image` | **Critical** — biometric data | Direct DB read; face images served from media |
| `Attendance` | `check_in_time`, `check_out_time`, `location.latitude/longitude` | **High** — location tracking data | Coordinator can view all attendance; no per-student filter |
| `StudentNarrativeReport` | `content`, `photos` (JSON), `grade`, `feedback` | **Medium** — academic work | Accessible to all coordinators via `/api/student/narratives/` |
| `OJTApplication` | `status`, `coordinator_notes` | **Medium** — internal admin notes | Exposed in API responses |
| `LoginAttempt` | `ip_address`, `user_agent`, `success` | **Medium** — operational security | Logged for every login; no retention policy |
| `SystemLog` | `action`, `details`, `ip_address`, `user` | **Medium** — operational audit trail | Accessible via admin panel API |

**Critical concern:** `FacialRecognition.face_encoding` is a biometric data blob stored unencrypted in SQLite. A SQL dump exposes all registered face embeddings.

---

## 3. Lateral Movement Potential

| Compromised Role | Can Escalate To | Method |
|---|---|---|
| Student | Coordinator | Mass-assignment on `role` field in profile PATCH |
| Student | Admin | Direct DB access via SQL injection or credential theft |
| Coordinator | Admin | `IsCoordinator` permission only checks `program.coordinator_id`; does not verify role immutability |
| Admin | System | Full CRUD via `/api/admin/` — can modify `User`, `SystemSettings`, create superusers |

**Cross-service lateral movement:**
- SQLite file (`db.sqlite3`) contains all tokens, passwords (if weak hashing), and biometric blobs. Compromise of any single user can pivot to full DB access.
- `CORS_ALLOW_ALL_ORIGINS=True` means any origin can make authenticated requests if cookie is not httpOnly — enabling CSRF-based lateral movement between roles.

---

## 4. Business Impact

| Impact Category | Description |
|---|---|
| **Operational Disruption** | Fake attendance records destroy integrity of OJT hour tracking; coordinators cannot trust attendance data |
| **Academic Fraud** | Students can bypass face verification to log hours they did not work, undermining program credibility |
| **Reputational Damage** | Biometric data breach (face embeddings) is reportable under Philippine law and damages institutional trust |
| **Regulatory Penalty** | RA 10173 (Philippine Data Privacy Act) carries fines up to ₱5,000,000 for personal data breaches; facial data is "sensitive personal information" |
| **Litigation Risk** | Students whose biometric data is exposed may pursue civil damages under RA 10173 §28 |
| **Audit Failure** | Missing CSRF protection, permissive CORS, and role escalation violate standard internal audit controls |
| **Financial Loss** | Re-issuance of credentials, forensic investigation, and potential regulatory fines |

---

## 5. Philippine Data Privacy Act (RA 10173) Compliance

| Requirement | Status | Finding |
|---|---|---|
| **§12 — Sensitive Personal Information** | ❌ Non-Compliant | Facial embeddings (`face_encoding`) classified as sensitive personal information; stored unencrypted in plain SQLite |
| **§11(a) — Consent** | ⚠️ Partial | Registration captures consent implicitly; no explicit consent for biometric collection and face image processing |
| **§11(f) — Security Measures** | ❌ Non-Compliant | No encryption at rest for sensitive data; SQLite database file is plaintext; no database encryption configured |
| **§20 — Breach Notification** | ⚠️ Unknown | No breach notification workflow defined in codebase; `SystemLog` exists but not connected to alerting |
| **§21 — Data Retention** | ❌ Non-Compliant | `LoginAttempt` records retained indefinitely; no data retention/deletion policy; `PasswordResetOTP` never purged |
| **§42 — Security of Processing** | ❌ Non-Compliant | No access controls on SQLite file; face images stored on local filesystem with no encryption |
| **§43 — Data Protection Officer** | ⚠️ Unknown | No evidence of DPO designation or contact information in application |

**Key risk:** Facial recognition data (face images + embeddings) constitutes **sensitive personal information** under RA 10173 §3(l). The application processes this without encryption at rest, creating direct regulatory exposure.

---

## 6. Prioritized Remediation Roadmap

### Priority 1 — Critical (Immediate: within 1 week)

| # | Fix | Issue Addressed | Implementation |
|---|---|---|---|
| 1.1 | **Encrypt database at rest** | Face embeddings in plaintext SQLite | Enable SQLite encryption via `sqlcipher` or migrate to PostgreSQL with TDE |
| 1.2 | **Fix mass-assignment on profile PATCH** | Role escalation from student → coordinator | Explicitly whitelist allowed fields in `StudentProfileSerializer.update()` |
| 1.3 | **Restrict CORS to known origins** | Token theft via cross-origin requests | Set `CORS_ALLOWED_ORIGINS` to actual frontend domain(s); remove `CORS_ALLOW_ALL_ORIGINS` |
| 1.4 | **Enforce httpOnly on auth cookies** | Token theft via XSS | Ensure `auth_token` cookie is set with `httponly=True` and `secure=True` |

### Priority 2 — High (Within 1 month)

| # | Fix | Issue Addressed | Implementation |
|---|---|---|---|
| 2.1 | **Add CSRF middleware** | Cross-site request forgery on token-authenticated endpoints | Re-enable Django CSRF middleware; exempt only pure API endpoints with token auth |
| 2.2 | **Implement data retention policy** | RA 10173 §21 non-compliance | Purge `LoginAttempt` after 90 days; purge `PasswordResetOTP` after 24 hours; add management command |
| 2.3 | **Add explicit biometric consent** | RA 10173 §11(a) consent requirement | Add consent checkbox + audit log before face registration |
| 2.4 | **Encrypt face images at rest** | Biometric data exposure | Encrypt `face_image` file field contents; store encryption key in environment variable |

### Priority 3 — Medium (Within 3 months)

| # | Fix | Issue Addressed | Implementation |
|---|---|---|---|
| 3.1 | **Implement breach notification workflow** | RA 10173 §20 compliance | Add `SecurityIncident` model with notification workflow; alert DPO/admin on detection |
| 3.2 | **Harden face verification** | Face verification bypass (attendance fraud) | Add liveness detection (blink/depth); require device geofencing; add rate limiting on verify endpoint |
| 3.3 | **Add API rate limiting** | Brute-force on login/OTP endpoints | Apply DRF throttling to all authentication endpoints; escalate lockout thresholds |
| 3.4 | **Audit IDOR on attendance** | Cross-student attendance access | Ensure `StudentAttendanceViewSet` filters by `request.user`; verify no horizontal IDOR |

### Priority 4 — Low (Ongoing)

| # | Fix | Issue Addressed | Implementation |
|---|---|---|---|
| 4.1 | **Implement WAF/CDN** | Network-layer protection | Deploy Cloudflare or AWS WAF in front of application |
| 4.2 | **Add security headers** | Clickjacking, MIME sniffing, etc. | Add `django-csp`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` |
| 4.3 | **Set up security scanning** | Regression detection | Add `bandit` to CI pipeline; schedule quarterly penetration test |
| 4.4 | **DPO designation** | RA 10173 §43 compliance | Formally designate DPO; publish contact information in privacy policy |

---

*Report generated from static code analysis of the OJT Monitoring codebase.*
*No exploitation was performed — this is a pre-deployment security assessment.*
