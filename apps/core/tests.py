"""
Tests for the core app
"""
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from apps.core.models import User


class EmailBackendConfigTest(SimpleTestCase):
    """Test cases for email backend configuration."""

    @override_settings(EMAIL_BACKEND='apps.core.mail.backends.smtp.EmailBackend')
    def test_custom_smtp_backend_is_configured(self):
        """The custom SMTP backend should be used so approval emails can be delivered reliably."""
        self.assertEqual(settings.EMAIL_BACKEND, 'apps.core.mail.backends.smtp.EmailBackend')


class UserModelTest(TestCase):
    """Test cases for User model."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='student'
        )
    
    def test_user_creation(self):
        """Test user creation."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_user_role(self):
        """Test user role assignment."""
        self.assertEqual(self.user.role, 'student')
        self.assertTrue(self.user.is_student())
        self.assertFalse(self.user.is_admin())
        self.assertFalse(self.user.is_coordinator())
