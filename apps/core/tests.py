"""
Tests for the core app
"""
from django.test import TestCase
from apps.core.models import User


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
