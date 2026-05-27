# web/tests/test_ad_plugin_permissions.py
from unittest import skipUnless
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    from plugins_data.active_directory.backend.models import ADAssessment
    from plugins_data.active_directory.backend.permissions import IsAssessmentOwnerOrAdmin
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADPermissions(TestCase):
    """Test permission checks for AD Assessment model and ViewSet."""

    def setUp(self):
        """Create test users and assessment."""
        self.owner = User.objects.create_user(username='ad_owner', password='pass')
        self.other = User.objects.create_user(username='ad_other', password='pass')
        self.admin = User.objects.create_user(
            username='ad_admin', password='pass', is_staff=True
        )
        self.assessment = ADAssessment.objects.create(
            name='Perm Test',
            target_domain='corp.local',
            created_by=self.owner,
        )

    def tearDown(self):
        """Clean up test data."""
        self.assessment.delete()
        self.owner.delete()
        self.other.delete()
        self.admin.delete()

    def _make_request(self, user):
        """Helper: Create a mock request with user."""
        req = RequestFactory().post('/')
        req.user = user
        return req

    def test_owner_has_object_permission(self):
        """Assessment owner should have object permission."""
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.owner)
        self.assertTrue(perm.has_object_permission(req, None, self.assessment))

    def test_other_user_denied_object_permission(self):
        """Non-owner, non-admin user should be denied object permission."""
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.other)
        self.assertFalse(perm.has_object_permission(req, None, self.assessment))

    def test_admin_has_object_permission(self):
        """Admin/staff user should have object permission regardless of ownership."""
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.admin)
        self.assertTrue(perm.has_object_permission(req, None, self.assessment))

    def test_null_created_by_is_accessible_to_anyone(self):
        """Assessment with no owner (created_by=None) should be accessible to any authenticated user."""
        anon_assessment = ADAssessment.objects.create(
            name='Anon Assessment',
            target_domain='anon.local',
            created_by=None,
        )
        try:
            perm = IsAssessmentOwnerOrAdmin()
            req = self._make_request(self.other)
            self.assertTrue(perm.has_object_permission(req, None, anon_assessment))
        finally:
            anon_assessment.delete()

    def test_get_queryset_filters_for_non_owner(self):
        """ViewSet.get_queryset() should exclude assessments owned by other users."""
        try:
            from plugins_data.active_directory.backend.api import ADAssessmentViewSet
        except (ImportError, ModuleNotFoundError):
            self.skipTest("ADAssessmentViewSet not available")

        req = RequestFactory().get('/')
        req.user = self.other
        view = ADAssessmentViewSet()
        view.request = req
        view.action = 'list'
        qs = view.get_queryset()
        self.assertNotIn(self.assessment, qs)

    def test_get_queryset_returns_all_for_staff(self):
        """ViewSet.get_queryset() should return all assessments for staff/admin users."""
        try:
            from plugins_data.active_directory.backend.api import ADAssessmentViewSet
        except (ImportError, ModuleNotFoundError):
            self.skipTest("ADAssessmentViewSet not available")

        req = RequestFactory().get('/')
        req.user = self.admin
        view = ADAssessmentViewSet()
        view.request = req
        view.action = 'list'
        qs = view.get_queryset()
        self.assertIn(self.assessment, qs)
