from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from rolepermissions.checkers import has_permission, has_role
from reNgine.definitions import *

class HasPermission(BasePermission):
	"""
		This is a custom permission class for DRF that checks if the user 
		has the required permission.
		Usage in drf views:
		permission_classes = [HasPermission]
		permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS
	"""

	def has_permission(self, request, view):
		if not request.user or not request.user.is_authenticated:
			return False

		permission_code = getattr(view, 'permission_required', None)
		if not permission_code:
			raise PermissionDenied(detail="Permission is not specified for this view.")

		if not has_permission(request.user, permission_code):
			raise PermissionDenied(detail="This user does not have enough permissions")
		return True

class IsSysAdmin(BasePermission):
	"""
	Allows access only to SysAdmin users.
	Role: sys_admin — can see and manage everything.
	"""
	def has_permission(self, request, view):
		return request.user and request.user.is_authenticated and (
			request.user.is_superuser or has_role(request.user, 'sys_admin')
		)

class IsPenetrationTester(BasePermission):
	"""
	Allows access to SysAdmin and PenetrationTester users.
	Role: penetration_tester — can configure engines and initiate/view scans.
	"""
	def has_permission(self, request, view):
		if not request.user or not request.user.is_authenticated:
			return False
		return (
			request.user.is_superuser or 
			has_role(request.user, ['sys_admin', 'penetration_tester'])
		)

class IsAuditor(BasePermission):
	"""
	Allows read-only access to users with Auditor role (or higher).
	Role: auditor — read-only access to scan configs and scan results.
	Write operations (POST, PUT, PATCH, DELETE) are denied for pure Auditors.
	"""
	def has_permission(self, request, view):
		if not request.user or not request.user.is_authenticated:
			return False
		# SysAdmins and PenetrationTesters also pass this check
		if (request.user.is_superuser or
			has_role(request.user, ['sys_admin', 'penetration_tester', 'auditor'])):
			# Auditors are read-only — reject any write methods
			if has_role(request.user, 'auditor') and not request.user.is_superuser and \
				not has_role(request.user, ['sys_admin', 'penetration_tester']):
				if request.method not in SAFE_METHODS:
					raise PermissionDenied(detail="Auditors have read-only access.")
			return True
		return False