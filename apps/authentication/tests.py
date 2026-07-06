"""
Tests for the authentication app
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Course, User
from apps.core.utils import cache
from .models import EmailVerificationToken, LoginAttempt, PasswordResetOTP


# ── Model tests ─────────────────────────────────────────────────────────

class EmailVerificationTokenTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='evuser', email='ev@test.com', password='pass123',
        )

    def test_generate_creates_token(self):
        tok = EmailVerificationToken.generate(self.user)
        self.assertIsNotNone(tok.token)
        self.assertFalse(tok.verified)
        self.assertTrue(tok.is_valid())

    def test_expired_token_is_invalid(self):
        tok = EmailVerificationToken.generate(self.user)
        tok.expires_at = timezone.now() - timedelta(hours=1)
        tok.save()
        self.assertFalse(tok.is_valid())

    def test_verified_token_is_invalid(self):
        tok = EmailVerificationToken.generate(self.user)
        tok.verified = True
        tok.save()
        self.assertFalse(tok.is_valid())


class PasswordResetOTPTest(TestCase):
    def test_generate_otp_creates_record(self):
        otp = PasswordResetOTP.generate_otp('test@test.com')
        self.assertEqual(len(otp.otp), 6)
        self.assertTrue(otp.is_valid())

    def test_expired_otp_is_invalid(self):
        otp = PasswordResetOTP.generate_otp('test@test.com')
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        self.assertFalse(otp.is_valid())

    def test_used_otp_is_invalid(self):
        otp = PasswordResetOTP.generate_otp('test@test.com')
        otp.is_used = True
        otp.save()
        self.assertFalse(otp.is_valid())


# ── View tests ──────────────────────────────────────────────────────────

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()  # reset rate limiter

    def test_student_register_creates_user(self):
        resp = self.client.post('/api/auth/register/', {
            'username': 'newstudent',
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'Student',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='newstudent').exists())

    def test_student_register_returns_pending_message(self):
        resp = self.client.post('/api/auth/register/', {
            'username': 'pending',
            'email': 'pend@test.com',
            'first_name': 'Pen',
            'last_name': 'Ding',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, format='json')
        self.assertIn('wait', resp.data['message'].lower())

    def test_register_password_mismatch(self):
        resp = self.client.post('/api/auth/register/', {
            'username': 'mismatch',
            'email': 'mm@test.com',
            'first_name': 'M',
            'last_name': 'M',
            'password': 'StrongPass123!',
            'password2': 'DifferentPass123!',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        User.objects.create_user(
            username='dup', email='dup@test.com', password='pass123',
        )
        resp = self.client.post('/api/auth/register/', {
            'username': 'dup',
            'email': 'dup2@test.com',
            'first_name': 'D',
            'last_name': 'U',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, format='json')
        self.assertEqual(resp.status_code, 400)


class VerifyEmailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='vuser', email='v@test.com', password='pass123',
        )

    def test_valid_token_verifies(self):
        tok = EmailVerificationToken.generate(self.user)
        resp = self.client.post('/api/auth/verify-email/', {'token': str(tok.token)})
        self.assertEqual(resp.status_code, 200)

    def test_invalid_token_returns_400(self):
        resp = self.client.post('/api/auth/verify-email/', {'token': 'bad-token'})
        self.assertEqual(resp.status_code, 400)

    def test_missing_token_returns_400(self):
        resp = self.client.post('/api/auth/verify-email/')
        self.assertEqual(resp.status_code, 400)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='luser', email='l@test.com', password='pass123',
            approval_status='approved',
        )
        cache.clear()

    def test_login_success(self):
        resp = self.client.post('/api/auth/login/', {
            'identifier': 'luser', 'password': 'pass123',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.data)

    def test_login_by_email(self):
        resp = self.client.post('/api/auth/login/', {
            'identifier': 'l@test.com', 'password': 'pass123',
        }, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_login_wrong_password(self):
        resp = self.client.post('/api/auth/login/', {
            'identifier': 'luser', 'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_unapproved_student_cannot_login(self):
        User.objects.create_user(
            username='unapproved', email='ua@test.com',
            password='pass123', role='student', approval_status='pending',
        )
        resp = self.client.post('/api/auth/login/', {
            'identifier': 'unapproved', 'password': 'pass123',
        }, format='json')
        self.assertEqual(resp.status_code, 401)
