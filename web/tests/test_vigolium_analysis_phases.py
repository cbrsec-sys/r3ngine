"""Tier 5 vigolium analysis must not redo what Tier 2 already did.

`discovery` over the subdomain roots is exactly the pass `vigolium_discovery`
runs in Tier 2, and `external-harvest` is skipped by vigolium itself under
`--stateless`, which every r3ngine invocation uses.
"""
from unittest import TestCase

from reNgine.tasks.vigolium import _analysis_phases


class AnalysisPhaseSelectionTests(TestCase):

    def test_discovery_is_dropped_when_tier2_ran_it(self) -> None:
        self.assertEqual(
            _analysis_phases(skip_spidering=False, discovery_already_ran=True),
            'spidering,known-issue-scan,dynamic-assessment',
        )

    def test_discovery_is_kept_when_tier2_is_disabled(self) -> None:
        """A scan configured without the Tier 2 pass must lose no coverage."""
        self.assertEqual(
            _analysis_phases(skip_spidering=False, discovery_already_ran=False),
            'spidering,discovery,known-issue-scan,dynamic-assessment',
        )

    def test_skip_spidering_removes_only_the_browser_crawl(self) -> None:
        self.assertEqual(
            _analysis_phases(skip_spidering=True, discovery_already_ran=True),
            'known-issue-scan,dynamic-assessment',
        )
        self.assertEqual(
            _analysis_phases(skip_spidering=True, discovery_already_ran=False),
            'discovery,known-issue-scan,dynamic-assessment',
        )

    def test_external_harvest_is_never_requested(self) -> None:
        """It is a no-op under --stateless — see the helper's docstring."""
        for skip in (True, False):
            for ran in (True, False):
                self.assertNotIn(
                    'external-harvest',
                    _analysis_phases(skip_spidering=skip, discovery_already_ran=ran),
                )

    def test_assessment_phases_always_run(self) -> None:
        for skip in (True, False):
            for ran in (True, False):
                phases = _analysis_phases(skip_spidering=skip, discovery_already_ran=ran)
                self.assertIn('known-issue-scan', phases)
                self.assertIn('dynamic-assessment', phases)
