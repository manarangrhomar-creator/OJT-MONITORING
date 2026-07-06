"""
Tests for the core app
"""
import math
from datetime import date, timedelta

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from apps.core.models import User, Notification
from apps.core.utils import (
    get_week_range, get_month_range, create_notification,
    haversine, is_within_geofence,
)


# ── Existing tests ──────────────────────────────────────────────────────

class EmailBackendConfigTest(SimpleTestCase):
    @override_settings(EMAIL_BACKEND='apps.core.mail.backends.smtp.EmailBackend')
    def test_custom_smtp_backend_is_configured(self):
        self.assertEqual(settings.EMAIL_BACKEND, 'apps.core.mail.backends.smtp.EmailBackend')


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com',
            password='testpass123', first_name='Test', last_name='User',
            role='student',
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_role(self):
        self.assertEqual(self.user.role, 'student')
        self.assertTrue(self.user.is_student())
        self.assertFalse(self.user.is_admin())
        self.assertFalse(self.user.is_coordinator())


# ── haversine ───────────────────────────────────────────────────────────

class HaversineTest(SimpleTestCase):
    def test_same_point_returns_zero(self):
        self.assertEqual(haversine(14.5995, 120.9842, 14.5995, 120.9842), 0.0)

    def test_known_distance_roughly(self):
        # Manila (14.5995, 120.9842) → Quezon City (14.6760, 121.0437) ≈ 10 km
        dist = haversine(14.5995, 120.9842, 14.6760, 121.0437)
        self.assertAlmostEqual(dist / 1000, 10.0, delta=3.0)

    def test_antipodal_points(self):
        dist = haversine(0, 0, 0, 180)
        self.assertAlmostEqual(dist, 20015086.8, delta=1000.0)  # ~half earth circumference in meters


# ── is_within_geofence ──────────────────────────────────────────────────

class GeofenceTest(SimpleTestCase):
    def test_within_default_radius(self):
        # Same point → always within 100 m
        self.assertTrue(is_within_geofence(14.5995, 120.9842, 14.5995, 120.9842))

    def test_outside_default_radius(self):
        # ~10 km away
        self.assertFalse(is_within_geofence(14.5995, 120.9842, 14.6760, 121.0437))

    def test_custom_radius(self):
        # ~10 km away, generous radius
        self.assertTrue(is_within_geofence(14.5995, 120.9842, 14.6760, 121.0437, radius_m=15000))

    def test_none_coords_skip(self):
        self.assertTrue(is_within_geofence(None, None, 14.5995, 120.9842))
        self.assertTrue(is_within_geofence(14.5995, 120.9842, None, None))


# ── get_week_range ──────────────────────────────────────────────────────

class WeekRangeTest(SimpleTestCase):
    def test_known_monday(self):
        d = date(2025, 7, 7)  # Monday
        start, end = get_week_range(d)
        self.assertEqual(start, date(2025, 7, 7))
        self.assertEqual(end, date(2025, 7, 13))

    def test_mid_week(self):
        d = date(2025, 7, 10)  # Thursday
        start, end = get_week_range(d)
        self.assertEqual(start, date(2025, 7, 7))
        self.assertEqual(end, date(2025, 7, 13))

    def test_none_uses_today(self):
        start, end = get_week_range()
        today = date.today()
        self.assertLessEqual(start, today)
        self.assertGreaterEqual(end, today)


# ── get_month_range ─────────────────────────────────────────────────────

class MonthRangeTest(SimpleTestCase):
    def test_known_date(self):
        d = date(2025, 2, 15)
        start, end = get_month_range(d)
        self.assertEqual(start, date(2025, 2, 1))
        self.assertEqual(end, date(2025, 2, 28))

    def test_december_wraps(self):
        d = date(2025, 12, 25)
        start, end = get_month_range(d)
        self.assertEqual(start, date(2025, 12, 1))
        self.assertEqual(end, date(2025, 12, 31))

    def test_none_uses_today(self):
        start, end = get_month_range()
        today = date.today()
        self.assertEqual(start, today.replace(day=1))


# ── create_notification ─────────────────────────────────────────────────

class NotificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifuser', password='pass123', role='student',
        )

    def test_creates_notification(self):
        create_notification(self.user, 'Title', 'Body', type='general')
        self.assertEqual(Notification.objects.count(), 1)
        n = Notification.objects.first()
        self.assertEqual(n.title, 'Title')
        self.assertEqual(n.recipient, self.user)

    def test_multiple_notifications(self):
        create_notification(self.user, 'A', '1')
        create_notification(self.user, 'B', '2')
        self.assertEqual(Notification.objects.count(), 2)
