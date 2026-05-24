# web/tests/test_ad_plugin_graph.py
from django.test import TestCase


class TestADGraphSchema(TestCase):

    def _import_schema(self):
        try:
            from plugins_data.active_directory.backend.graph import schema
            return schema
        except (ImportError, ModuleNotFoundError):
            self.skipTest("Plugin not installed")

    def test_all_node_labels_defined(self):
        schema = self._import_schema()
        expected = [
            'ADDomainNode', 'ADForestNode', 'ADOUNode', 'ADUserNode',
            'ADGroupNode', 'ADComputerNode', 'ADServiceNode',
            'ADCertificateNode', 'ADTrustNode', 'ADSubnetNode',
            'ADSiteNode', 'ADPolicyNode', 'ADExposureNode', 'ADFindingNode',
            'ADIdentityProviderNode', 'ADVPNGatewayNode', 'ADAuthServiceNode',
        ]
        for label in expected:
            self.assertIn(label, dir(schema), f"Missing node label: {label}")

    def test_all_relationships_defined(self):
        schema = self._import_schema()
        expected = [
            'AD_MEMBER_OF', 'AD_TRUSTS', 'AD_CONNECTED_TO', 'AD_LOCATED_IN',
            'AD_AUTHENTICATES_TO', 'AD_EXPOSES', 'AD_LINKED_TO',
            'AD_BELONGS_TO', 'AD_PROTECTED_BY', 'AD_ROUTES_THROUGH',
        ]
        for rel in expected:
            self.assertIn(rel, dir(schema), f"Missing relationship: {rel}")

    def test_constraint_statements_are_valid_cypher_strings(self):
        schema = self._import_schema()
        constraints = schema.CONSTRAINT_STATEMENTS
        self.assertIsInstance(constraints, list)
        self.assertGreater(len(constraints), 0)
        for stmt in constraints:
            self.assertIn('CREATE CONSTRAINT', stmt)
