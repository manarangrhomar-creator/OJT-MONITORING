"""
Shared helpers for all PoC scripts.
Provides user registration, approval via Django shell, login, and test image creation.
"""

import requests
import subprocess
import sys
import struct
import zlib
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api"
MEDIA = f"{BASE_URL}/media"
PROJECT_ROOT = Path(__file__).parent.parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
RESULTS = []


def log(msg, level="INFO"):
    prefix = {"INFO": "[*]", "OK": "[+]", "FAIL": "[-]", "WARN": "[!]"}
    print(f"  {prefix.get(level, '[*]')} {msg}")


def record(test_id, description, status, detail=""):
    RESULTS.append({"id": test_id, "description": description, "status": status, "detail": detail})
    log(f"{description}: {status}", "OK" if status == "PASS" else "FAIL")
    if detail:
        log(f"  Detail: {detail}")


def create_test_image():
    """Create a minimal 1x1 red PNG for upload tests. Returns path."""
    test_image = Path("poc_scripts/test_photo.png")
    test_image.parent.mkdir(exist_ok=True)
    if not test_image.exists():
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc & 0xFFFFFFFF)
        raw = zlib.compress(b'\x00\xff\x00\x00')
        idat_crc = zlib.crc32(b'IDAT' + raw)
        idat = struct.pack('>I', len(raw)) + b'IDAT' + raw + struct.pack('>I', idat_crc & 0xFFFFFFFF)
        iend_crc = zlib.crc32(b'IEND')
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc & 0xFFFFFFFF)
        test_image.write_bytes(sig + ihdr + idat + iend)
        log("Created test PNG image", "OK")
    return test_image


def register_user(session, username, email, password, first_name="POC", last_name="Test", role="student"):
    """Register a user via the API. Returns response."""
    resp = session.post(f"{API}/auth/register/", json={
        "username": username,
        "email": email,
        "password": password,
        "password2": password,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
    })
    return resp


def approve_user_via_shell(username):
    """Approve a user by setting approval_status='approved' via manage.py shell."""
    django_code = (
        f"from apps.core.models import User; "
        f"u = User.objects.get(username='{username}'); "
        f"u.approval_status = 'approved'; "
        f"u.save(update_fields=['approval_status']); "
        f"print(f'Approved: {{u.username}} ({{u.approval_status}})')"
    )
    result = subprocess.run(
        [str(VENV_PYTHON), "manage.py", "shell", "-c", django_code],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    if result.returncode == 0:
        log(f"Approved user '{username}' via Django shell", "OK")
        if result.stdout.strip():
            log(f"  {result.stdout.strip()}")
    else:
        log(f"Failed to approve '{username}': {result.stderr[:200]}", "WARN")
    return result.returncode == 0


def create_superuser_via_shell(username="poc_admin", password="PocAdmin@2026!", email="admin@poc.test"):
    """Create a superuser via manage.py shell. Returns (username, password)."""
    django_code = (
        f"from apps.core.models import User; "
        f"u, created = User.objects.get_or_create(username='{username}', "
        f"defaults={{'email': '{email}', 'is_staff': True, 'is_superuser': True, "
        f"'role': 'admin', 'approval_status': 'approved'}}); "
        f"if created: u.set_password('{password}'); u.save(); print(f'Created admin: {username}'); "
        f"else: print(f'Admin already exists: {username}')"
    )
    result = subprocess.run(
        [str(VENV_PYTHON), "manage.py", "shell", "-c", django_code],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    if result.returncode == 0:
        log(f"Superuser setup: {result.stdout.strip()}", "OK")
    else:
        log(f"Superuser creation failed: {result.stderr[:200]}", "WARN")
    return username, password


def create_coordinator_via_shell(username, password, email, first_name="POC", last_name="Coord"):
    """Create a coordinator user via manage.py shell (bypasses API role restriction)."""
    django_code = (
        "from apps.core.models import User; "
        "u, created = User.objects.get_or_create("
        "username='" + username + "', "
        "defaults={'email': '" + email + "', 'role': 'coordinator', 'approval_status': 'approved', "
        "'first_name': '" + first_name + "', 'last_name': '" + last_name + "'}); "
        "u.set_password('" + password + "'); u.save(); "
        "print('CREATED:' + u.username + ':' + u.role)"
    )
    result = subprocess.run(
        [str(VENV_PYTHON), "manage.py", "shell", "-c", django_code],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    if result.returncode == 0:
        log(f"Coordinator setup: {result.stdout.strip()}", "OK")
    else:
        log(f"Coordinator creation failed: {result.stderr[:200]}", "WARN")
    return result.returncode == 0


def login_user(session, identifier, password):
    """Login via the API. Returns token string or None."""
    resp = session.post(f"{API}/auth/login/", json={
        "identifier": identifier,
        "password": password,
    })
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("token") or data.get("key") or data.get("data", {}).get("token")
        if token:
            return token
    log(f"Login failed for '{identifier}': {resp.status_code} {resp.text[:200]}", "WARN")
    return None


def register_and_approve(session, username, password, email, first_name="POC", last_name="Test", role="student"):
    """Register a user, approve via shell, login, return token."""
    log(f"Registering '{username}'...")
    reg = register_user(session, username, email, password, first_name, last_name, role)
    if reg.status_code not in (200, 201):
        log(f"Registration failed: {reg.status_code} {reg.text[:200]}", "WARN")
        return None

    log(f"Approving '{username}'...")
    approve_user_via_shell(username)

    log(f"Logging in '{username}'...")
    token = login_user(session, username, password)
    return token
