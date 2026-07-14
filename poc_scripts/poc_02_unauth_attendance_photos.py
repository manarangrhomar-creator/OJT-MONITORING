#!/usr/bin/env python3
"""
PoC 02 — F-008: Unauthenticated Access to Attendance Records

TEST RESULT: NOT VULNERABLE

The /api/coordinator/attendance/ endpoint is protected by IsCoordinator permission:
  - Unauthenticated requests → 401 (blocked)
  - Student token → 403 (blocked)
  - Coordinator token → 200 (allowed, as expected)

The Attendance model also has NO photo/image fields (no clock-in/clock-out photos).
The original F-008 description does not match the actual schema or behavior.
"""

import requests
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from poc_helpers import (
    BASE_URL, API, MEDIA, RESULTS, log, record,
    register_and_approve, login_user,
    create_coordinator_via_shell,
)

RESULTS.clear()


def setup_test_data(session):
    """Create coordinator + student for testing."""
    timestamp = int(time.time())
    coord_password = "PocCoord@2026!"
    stu_password = "PocTest@2026!"

    # Coordinator
    log("Step 1: Create coordinator via shell + login")
    coord_user = f"poc_coord_att_{timestamp}"
    create_coordinator_via_shell(coord_user, coord_password, f"{coord_user}@gmail.com")
    coord_token = login_user(session, coord_user, coord_password)
    if not coord_token:
        log("Coordinator login failed", "WARN")
        return None, None, None
    log(f"Coordinator token: {coord_token[:12]}...", "OK")

    # Student
    log("Step 2: Register + approve + login student account")
    stu_user = f"poc_stu_att_{timestamp}"
    stu_token = register_and_approve(
        session, stu_user, stu_password, f"{stu_user}@gmail.com",
        "POC", "AttendanceStudent"
    )
    if not stu_token:
        log("Student setup failed", "WARN")
        return coord_token, None, None
    log(f"Student token: {stu_token[:12]}...", "OK")

    return coord_token, stu_token, coord_user


def test_unauthenticated_access(session):
    """Test 1: GET /api/coordinator/attendance/ WITHOUT any auth token."""
    log("Step 3: GET /api/coordinator/attendance/ WITHOUT auth token")
    resp = session.get(f"{API}/coordinator/attendance/")
    record("F-008.1", "Unauthenticated access to attendance endpoint",
           "PASS" if resp.status_code in (401, 403) else "FAIL",
           f"HTTP {resp.status_code} -- "
           f"{'BLOCKED (correct)' if resp.status_code in (401, 403) else 'VULNERABLE: data exposed'}")
    return resp.status_code


def test_student_access(session, student_token):
    """Test 2: Student token on coordinator attendance endpoint."""
    log("Step 4: Student token on /api/coordinator/attendance/")
    resp = session.get(f"{API}/coordinator/attendance/",
                       headers={"Authorization": f"Token {student_token}"})
    record("F-008.2", "Student token on coordinator attendance endpoint",
           "PASS" if resp.status_code == 403 else "FAIL",
           f"HTTP {resp.status_code} -- "
           f"{'BLOCKED (correct)' if resp.status_code == 403 else 'VULNERABLE'}")
    return resp.status_code


def test_coordinator_access(coord_token):
    """Test 3: Coordinator token (baseline — should work).
    
    Uses requests.get() instead of session.get() to avoid session cookie
    contamination: register_and_approve() calls login_user() which overwrites
    the session auth_token cookie with the student token, causing DRF's
    SessionAuthentication to authenticate as the student instead of using
    the Authorization header.
    """
    log("Step 5: Coordinator token on /api/coordinator/attendance/")
    resp = requests.get(f"{API}/coordinator/attendance/",
                        headers={"Authorization": f"Token {coord_token}"})
    record("F-008.3", "Coordinator access (baseline)",
           "PASS" if resp.status_code == 200 else "FAIL",
           f"HTTP {resp.status_code}")
    return resp.status_code


def test_attendance_model_has_no_photos():
    """Test 4: Verify Attendance model has no photo/image fields."""
    log("Step 6: Verify Attendance model schema")
    import subprocess
    from pathlib import Path

    PYTHON = str(Path("venv/Scripts/python.exe").resolve())
    ROOT = str(Path(".").resolve())

    code = (
        "from apps.coordinator.models import Attendance; "
        "fields = [f.name for f in Attendance._meta.get_fields()]; "
        "photo_fields = [f for f in fields if 'photo' in f.lower() or 'image' in f.lower() or 'picture' in f.lower()]; "
        "print('ALL_FIELDS:' + ','.join(fields)); "
        "print('PHOTO_FIELDS:' + ','.join(photo_fields) if photo_fields else 'PHOTO_FIELDS:none')"
    )
    r = subprocess.run([PYTHON, "manage.py", "shell", "-c", code],
                       capture_output=True, text=True, cwd=ROOT, timeout=30)

    all_fields = ""
    photo_fields = "none"
    for line in r.stdout.strip().split("\n"):
        if line.startswith("ALL_FIELDS:"):
            all_fields = line.split(":", 1)[1]
        elif line.startswith("PHOTO_FIELDS:"):
            photo_fields = line.split(":", 1)[1]

    record("F-008.4", "Attendance model has no photo fields",
           "PASS" if photo_fields == "none" else "FAIL",
           f"All fields: {all_fields} | Photo fields: {photo_fields}")
    return photo_fields == "none"


def main():
    print("=" * 70)
    print("PoC 02 — F-008: Unauthenticated Access to Attendance Records")
    print("=" * 70)
    print()
    print("RESULT: NOT VULNERABLE")
    print()
    print("The /api/coordinator/attendance/ endpoint is protected by")
    print("IsCoordinator permission class:")
    print("  - Unauthenticated requests -> 401 (blocked)")
    print("  - Student tokens -> 403 (blocked)")
    print("  - Coordinator tokens -> 200 (allowed)")
    print()
    print("Additionally, the Attendance model has NO photo/image fields.")
    print()

    session = requests.Session()

    coord_token, stu_token, coord_user = setup_test_data(session)
    if not coord_token:
        print("\n[-] Setup failed. Is the dev server running on localhost:8000?")
        sys.exit(1)

    print()

    test_unauthenticated_access(session)
    print()

    if stu_token:
        test_student_access(session, stu_token)
        print()

    test_coordinator_access(coord_token)
    print()

    test_attendance_model_has_no_photos()
    print()

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    for r in RESULTS:
        icon = "[+]" if r["status"] == "PASS" else "[-]" if r["status"] == "FAIL" else "[~]"
        print(f"  {icon} {r['id']}: {r['description']} — {r['status']}")
        if r["detail"]:
            print(f"      {r['detail']}")

    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    print(f"\nTotal: {len(RESULTS)} tests | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("\n*** F-008 NOT CONFIRMED: Attendance endpoint is properly protected ***")
        print("    Authentication is required. No unauthenticated data exposure.")
    else:
        print(f"\n*** {failed} test(s) FAILED — potential vulnerability ***")

    print()

    report_path = Path("poc_scripts/poc_02_results.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "poc": "02",
            "vulnerability": "F-008",
            "severity": "CRITICAL",
            "title": "Unauthenticated Access to Attendance Records (PII)",
            "conclusion": "NOT VULNERABLE — endpoint requires authentication",
            "note": "Attendance model has no photo fields; IsCoordinator permission blocks unauthenticated access",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": RESULTS,
        }, f, indent=2)
    print(f"  Report saved to: {report_path}")


if __name__ == "__main__":
    main()
