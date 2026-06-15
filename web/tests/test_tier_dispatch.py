# web/tests/test_tier_dispatch.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from plugins.models import Plugin


class TestGetEnabledPluginsForTierActivity(TestCase):
    """Tests for GetEnabledPluginsForTierActivity anchor_step matching."""

    def setUp(self):
        Plugin.objects.create(
            slug='test_plugin_t1',
            name='Test T1',
            version='1.0.0',
            anchor_step='tier_1',
            runtime_position='AFTER',
            is_enabled=True,
            manifest={'temporal': {'workflows': ['backend.temporal_exports.TestWorkflow']}},
            trust_level='official',
        )
        Plugin.objects.create(
            slug='test_plugin_t7',
            name='Test T7',
            version='1.0.0',
            anchor_step='tier_7',
            runtime_position='AFTER',
            is_enabled=True,
            manifest={'temporal': {'workflows': ['backend.temporal_exports.TestWorkflow']}},
            trust_level='official',
        )
        Plugin.objects.create(
            slug='test_plugin_disabled',
            name='Test Disabled',
            version='1.0.0',
            anchor_step='tier_1',
            runtime_position='AFTER',
            is_enabled=False,
            manifest={'temporal': {'workflows': ['backend.temporal_exports.TestWorkflow']}},
            trust_level='official',
        )

    def test_returns_plugins_matching_tier(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_1',
            'selected_plugin_slugs': ['test_plugin_t1'],
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['slug'], 'test_plugin_t1')
        self.assertEqual(result[0]['workflow_name'], 'TestWorkflow')

    def test_returns_empty_for_unselected_slug(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_1',
            'selected_plugin_slugs': ['some_other_slug'],
        })
        self.assertEqual(result, [])

    def test_disabled_plugin_excluded(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_1',
            'selected_plugin_slugs': ['test_plugin_disabled'],
        })
        self.assertEqual(result, [])

    def test_tier_7_returns_correct_plugin(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_7',
            'selected_plugin_slugs': ['test_plugin_t7'],
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['slug'], 'test_plugin_t7')

    def test_empty_selected_slugs_returns_empty(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_1',
            'selected_plugin_slugs': [],
        })
        self.assertEqual(result, [])

    def test_wrong_tier_returns_empty(self):
        from reNgine.temporal_activities import get_enabled_plugins_for_tier_activity
        result = get_enabled_plugins_for_tier_activity({
            'tier': 'tier_6',
            'selected_plugin_slugs': ['test_plugin_t1'],
        })
        self.assertEqual(result, [])
