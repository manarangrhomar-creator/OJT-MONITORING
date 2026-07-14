#!/usr/bin/env python3
"""
Runner: Execute all PoC scripts sequentially and produce a combined report.

Usage:
    python poc_scripts/run_all.py

Requires dev server running at http://localhost:8000
"""

import subprocess
import sys
import json
import time
from pathlib import Path

POC_DIR = Path(__file__).parent
SCRIPTS = [
    "poc_01_unauth_narrative_photos.py",
    "poc_02_unauth_attendance_photos.py",
    "poc_03_idor_student_profiles.py",
]

def main():
    print("=" * 70)
    print("  PoC Runner — Running all vulnerability proof-of-concept scripts")
    print("=" * 70)
    print()

    results = []
    start_time = time.time()

    for script in SCRIPTS:
        script_path = POC_DIR / script
        if not script_path.exists():
            print(f"\n[-] Script not found: {script}")
            results.append({"script": script, "status": "MISSING"})
            continue

        print(f"\n{'='*70}")
        print(f"  Running: {script}")
        print(f"{'='*70}\n")

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(POC_DIR.parent),  # Run from project root
            )
            print(proc.stdout)
            if proc.stderr:
                print(f"  STDERR: {proc.stderr[:500]}")
            results.append({
                "script": script,
                "status": "OK" if proc.returncode == 0 else f"EXIT {proc.returncode}",
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            print(f"\n[-] TIMEOUT: {script} exceeded 120 seconds")
            results.append({"script": script, "status": "TIMEOUT"})
        except Exception as e:
            print(f"\n[-] ERROR: {script}: {e}")
            results.append({"script": script, "status": f"ERROR: {e}"})

    elapsed = time.time() - start_time

    # Combined summary
    print("\n" + "=" * 70)
    print("  COMBINED RESULTS")
    print("=" * 70)
    for r in results:
        icon = "[+]" if r["status"] == "OK" else "[-]"
        print(f"  {icon} {r['script']}: {r['status']}")
    print(f"\n  Total time: {elapsed:.1f}s")

    # Load and merge individual result files
    combined = {"pocs": [], "summary": {}}
    total_tests = 0
    total_pass = 0
    vulns_confirmed = []

    for result_file in sorted(POC_DIR.glob("poc_*_results.json")):
        with open(result_file) as f:
            data = json.load(f)
        combined["pocs"].append(data)
        total_tests += len(data.get("results", []))
        total_pass += sum(1 for r in data.get("results", []) if r.get("status") == "PASS")
        if data.get("conclusion") == "VULNERABILITY CONFIRMED":
            vulns_confirmed.append(f"{data['vulnerability']} — {data['title']}")

    combined["summary"] = {
        "total_tests": total_tests,
        "total_passed": total_pass,
        "vulnerabilities_confirmed": vulns_confirmed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    combined_path = POC_DIR / "combined_results.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)

    if vulns_confirmed:
        print(f"\n  *** {len(vulns_confirmed)} VULNERABILITIES CONFIRMED ***")
        for v in vulns_confirmed:
            print(f"    - {v}")
    else:
        print("\n  [-] No vulnerabilities confirmed")

    print(f"\n  Combined report: {combined_path}")
    print()

if __name__ == "__main__":
    main()
