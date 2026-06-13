"""Phase 1 APME enhancement tests."""
from django.test import TestCase
from apme.utils.mitre import lookup, TECHNIQUE_CATALOG, TACTIC_COLOR


class MitreLookupTests(TestCase):

    def test_known_technique_returns_full_dict(self):
        result = lookup("T1190")
        self.assertEqual(result["technique_id"], "T1190")
        self.assertEqual(result["technique_name"], "Exploit Public-Facing Application")
        self.assertEqual(result["tactic_slug"], "initial-access")
        self.assertEqual(result["tactic_display"], "Initial Access")
        self.assertEqual(result["tactic_color"], "#ff4444")

    def test_unknown_technique_returns_safe_fallback(self):
        result = lookup("T9999")
        self.assertEqual(result["technique_id"], "T9999")
        self.assertEqual(result["tactic_slug"], "unknown")
        self.assertEqual(result["tactic_color"], "#888888")

    def test_all_catalog_entries_have_tactic_colors(self):
        for tid, (name, tactic_slug, tactic_display) in TECHNIQUE_CATALOG.items():
            self.assertIn(
                tactic_slug, TACTIC_COLOR,
                f"Technique {tid} tactic '{tactic_slug}' has no color entry",
            )

    def test_subtechnique_lookup(self):
        result = lookup("T1059.004")
        self.assertEqual(result["tactic_slug"], "execution")

    def test_lookup_returns_all_required_keys(self):
        for key in ("technique_id", "technique_name", "tactic_slug", "tactic_display", "tactic_color"):
            self.assertIn(key, lookup("T1190"))
            self.assertIn(key, lookup("T9999"))
