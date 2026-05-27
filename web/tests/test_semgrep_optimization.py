from django.test import TestCase
from reNgine.tasks import clean_and_validate_url

class SemgrepOptimizationTests(TestCase):
	"""Test suite for verifying Semgrep scan URL cleaning and domain scoping optimizations.
	"""

	def test_clean_and_validate_url_valid(self):
		"""Test clean_and_validate_url with valid, clean URLs.
		"""
		url = "https://sub.target.com/assets/main.js"
		result = clean_and_validate_url(url, base_domain="target.com")
		self.assertEqual(result, "https://sub.target.com/assets/main.js")

	def test_clean_and_validate_url_with_gospider_metadata(self):
		"""Test clean_and_validate_url with trailing metadata from gospider.
		"""
		url = "http://target.com/wp-includes/js/jquery/jquery.min.js?ver=3.7.1] - text/html"
		result = clean_and_validate_url(url, base_domain="target.com")
		self.assertEqual(result, "http://target.com/wp-includes/js/jquery/jquery.min.js?ver=3.7.1")

	def test_clean_and_validate_url_with_leading_metadata(self):
		"""Test clean_and_validate_url with leading metadata bracket structures.
		"""
		url = "[javascript] - http://target.com/assets/main.js"
		result = clean_and_validate_url(url, base_domain="target.com")
		self.assertEqual(result, "http://target.com/assets/main.js")

	def test_clean_and_validate_url_relative_path(self):
		"""Test clean_and_validate_url with a relative path.
		"""
		url = "/js/app.js"
		result = clean_and_validate_url(url, base_domain="target.com")
		self.assertEqual(result, "https://target.com/js/app.js")

	def test_clean_and_validate_url_external_domain(self):
		"""Test clean_and_validate_url with an out-of-scope third-party domain.
		"""
		url = "https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"
		result = clean_and_validate_url(url, base_domain="target.com")
		self.assertIsNone(result)

	def test_clean_and_validate_url_invalid(self):
		"""Test clean_and_validate_url with an entirely invalid URL string.
		"""
		url = "not_a_url_at_all"
		result = clean_and_validate_url(url, base_domain="target.com")
		# Returns https://target.com/not_a_url_at_all which is checked if it starts with http/https
		self.assertEqual(result, "https://target.com/not_a_url_at_all")
