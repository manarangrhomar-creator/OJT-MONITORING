# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Three equally-weighted primary roles:**

- **Administrators** — manage the overall system, approve coordinator registrations, oversee programs, view system logs and settings.
- **Coordinators** — define OJT programs, manage sites and site assignments, approve/reject student applications, monitor attendance via live dashboard, grade/narrative reports.
- **Students** — register and build a profile, apply to OJT programs, clock in/out using facial recognition with liveness detection, submit narrative reports with photos, track accumulated hours toward the 480-hour requirement.

## Product Purpose

Digitize and manage the complete On-the-Job Training (OJT) lifecycle for Isabela State University — Cauayan Campus. The system replaces paper-based tracking with a unified platform spanning registration, program application, biometric attendance, narrative reporting, evaluation, and compliance monitoring.

## Positioning

**Unified OJT lifecycle management.** The system integrates the entire OJT workflow — program application, facial-recognition attendance tracking with anti-spoofing, narrative reporting, site assignment, and 480-hour minimum monitoring — into a single cohesive platform that serves administrators, coordinators, and students equally. No generic attendance tracker or academic portal combines these OJT-specific workflows with biometric integrity and real-time cross-role visibility.

## Operating Context

- University academic calendar governs OJT program scheduling.
- Students complete OJT at external partner sites (companies, organizations) under a coordinator's oversight.
- The 480-hour minimum requirement may be split across up to two OJT programs.
- Three roles interact as a hierarchy: admin approves coordinators, coordinators approve students, students execute OJT.
- Each role has a dedicated dashboard with role-specific tools and data views.
- WebSocket connections deliver live dashboard updates for attendance, applications, and notifications.
- Facial recognition is performed on-device or via uploaded photos; liveness detection prevents spoofing.
- The system is web-based (responsive, PWA-capable) and designed for desktop and mobile browsers.

## Capabilities and Constraints

### Confirmed capabilities
- Role-based registration and authentication (admin, coordinator, student).
- Coordinator approval by admin; student approval by coordinator.
- OJT program creation and management (coordinator).
- Site management and coordinator-to-site assignment.
- Student application to OJT programs with coordinator approval/rejection.
- Facial-recognition attendance clock-in/clock-out with liveness detection.
- Narrative report submission with optional photo uploads.
- 480-hour minimum tracking across up to two OJT programs per student.
- Live dashboards with WebSocket-driven real-time updates.
- Unified notification system (in-app list + WebSocket push).
- Password reset via 3-step OTP flow.
- Admin panel for system settings, logs, and user management.
- REST API layer (DRF) for all core operations.
- Celery background tasks for async processing.
- drf-spectacular OpenAPI docs at `/api/docs/`.
- PWA manifest for installable web app experience.

### Technical stack
- **Backend:** Django 4.2, Django REST Framework 3.14, Celery, Redis
- **Frontend:** Django templates, Bootstrap 5, vanilla JavaScript
- **Database:** SQLite (dev), PostgreSQL (production)
- **Real-time:** Django Channels (Daphne/ASGI), WebSocket consumers
- **Facial recognition:** InsightFace
- **Auth:** DRF Token Auth, custom User model (UUID PK, `role` field)
- **API docs:** drf-spectacular (Swagger UI at `/api/docs/`)

### Naming conventions
- OJT = On-the-Job Training
- ISU = Isabela State University
- Program = an OJT opportunity (title, description, slots, duration)
- Site = an external organization hosting OJT students
- Narrative Report = periodic student-written summary of activities
- Clock-in/Clock-out = attendance marking via facial recognition

### Deliberately undecided
- Classroom/lecture component beyond OJT fieldwork (not modeled).
- External learning management system (LMS) integration.
- Mobile native app (PWA strategy is current but not exclusive).
- Grading rubric or scoring formula for narrative reports.
- Export/analytics beyond what exists in dashboard views.

## Brand Commitments

- **Product name:** OJT Monitoring System.
- **Stakeholder:** Isabela State University — Cauayan Campus.
- **Visual identity:** Forest green (`#0F5436`), Gold (`#C8A44A`), warm paper background (`#F7F5F0`).
- **Typography:** Fraunces (serif headings), DM Sans (body text).
- **Assets:** ISU seal and institutional branding appear on login page, dashboard headers, and templates.
- **Tone:** Professional, academic, institutional.

## Evidence on Hand

- Full Django project at this repository root (`C:\Users\THUNDEROBOT\OJT-MONITORING`).
- Templates in `templates/` with Bootstrap 5, responsive layouts, ISU branding.
- PWA manifest at `static/manifest.json` confirming installable web intent.
- Model definitions, serializer classes, ViewSets, and URL routers in `apps/{core,authentication,admin_panel,coordinator,student}/`.
- WebSocket consumers at `apps/core/consumers.py` for notifications and dashboard.
- Celery task definitions in `apps/core/tasks.py`.
- Branding visible across login page, registration forms, dashboard headers, and 404/500 pages.

No marketing copy, testimonials, case studies, press mentions, or deployment documentation exist. Future work must not fabricate these.

## Product Principles

1. **Three-role parity.** Each role has a dedicated, full-featured dashboard with tools specific to its job. No role is an afterthought.
2. **Biometric integrity.** Facial recognition with liveness detection ensures attendance records are trustworthy and resistant to spoofing.
3. **End-to-end lifecycle.** The platform covers every stage from registration through final evaluation with no workflow gaps — students should never need a separate tool or paper form.
4. **Real-time visibility.** WebSocket-driven updates keep administrators, coordinators, and students informed of attendance, applications, and approvals as they happen.
5. **Academic compliance by design.** The 480-hour minimum requirement and two-program limit are enforced at the data model and validation layer, not through manual auditing.

## Accessibility & Inclusion

WCAG AA is the target standard.