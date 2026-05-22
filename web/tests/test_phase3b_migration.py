"""Phase 3B migration tests — verify Celery scan entry points have been replaced with Temporal."""
import os
from unittest import TestCase

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relative_path):
    """Read a file from web/ root and return its contents."""
    with open(os.path.join(WEB_DIR, relative_path), 'r', encoding='utf-8') as f:
        return f.read()


class TestPhase3B1OrgScanTrigger(TestCase):
    """3B-1: start_organization_scan must use initiate_scan_temporal, not initiate_scan.apply_async."""

    def test_org_scan_view_does_not_use_apply_async(self):
        """startScan/views.py must not contain initiate_scan.apply_async anywhere."""
        source = _read('startScan/views.py')
        self.assertNotIn(
            'initiate_scan.apply_async(',
            source,
            "start_organization_scan must call initiate_scan_temporal — not initiate_scan.apply_async"
        )

    def test_org_scan_view_calls_initiate_scan_temporal(self):
        """The start_organization_scan view body must contain initiate_scan_temporal(**kwargs)."""
        source = _read('startScan/views.py')
        # Slice out the start_organization_scan function body
        start = source.find('def start_organization_scan(')
        self.assertNotEqual(start, -1, "start_organization_scan function not found")
        # Find the next top-level decorator or function
        next_marker = source.find('\n@has_permission_decorator', start + 1)
        if next_marker == -1:
            next_marker = source.find('\ndef ', start + len('def start_organization_scan('))
        body = source[start:next_marker if next_marker != -1 else len(source)]
        self.assertIn(
            'initiate_scan_temporal(**kwargs)',
            body,
            "start_organization_scan must call initiate_scan_temporal(**kwargs)"
        )
