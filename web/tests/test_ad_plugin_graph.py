# web/tests/test_ad_plugin_graph.py
import json
import os
import tempfile

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


class TestADGraphManager(TestCase):

    def _get_manager(self):
        try:
            from plugins_data.active_directory.backend.graph.manager import ADGraphManager
            return ADGraphManager
        except (ImportError, ModuleNotFoundError):
            self.skipTest("Plugin not installed")

    def test_manager_has_required_methods(self):
        Mgr = self._get_manager()
        required = [
            'ensure_schema', 'upsert_domain', 'upsert_user', 'upsert_group',
            'upsert_computer', 'upsert_exposure', 'upsert_finding',
            'create_trust_relationship', 'create_membership_relationship',
            'get_domain_graph', 'get_exposure_paths', 'get_trust_graph',
            'find_shortest_path',
        ]
        for method in required:
            self.assertTrue(
                hasattr(Mgr, method),
                f"ADGraphManager missing method: {method}")


class TestLDAPParser(TestCase):

    SAMPLE_USERS = [
        {
            "attributes": {
                "sAMAccountName": ["jdoe"],
                "displayName": ["John Doe"],
                "mail": ["jdoe@corp.example.com"],
                "userAccountControl": [512],
                "adminCount": [1],
                "objectSid": ["S-1-5-21-1234-5678-9012-1001"],
                "lastLogon": ["2026-01-01T00:00:00"],
            }
        }
    ]

    SAMPLE_GROUPS = [
        {
            "attributes": {
                "sAMAccountName": ["Domain Admins"],
                "objectSid": ["S-1-5-21-1234-5678-9012-512"],
                "member": ["CN=jdoe,DC=corp,DC=example,DC=com"],
            }
        }
    ]

    def _get_parser(self):
        try:
            from plugins_data.active_directory.backend.ingestion.ldap_parser import LDAPParser
            return LDAPParser
        except ImportError:
            self.skipTest("Plugin not installed")

    def test_parse_users_extracts_sam_account_name(self):
        Parser = self._get_parser()
        users = Parser.parse_users(self.SAMPLE_USERS)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['sam_account_name'], 'jdoe')

    def test_parse_users_detects_admin(self):
        Parser = self._get_parser()
        users = Parser.parse_users(self.SAMPLE_USERS)
        self.assertEqual(users[0]['admin_count'], 1)

    def test_parse_groups_extracts_name(self):
        Parser = self._get_parser()
        groups = Parser.parse_groups(self.SAMPLE_GROUPS)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['name'], 'Domain Admins')

    def test_parse_groups_detects_admin_group(self):
        Parser = self._get_parser()
        groups = Parser.parse_groups(self.SAMPLE_GROUPS)
        self.assertTrue(groups[0]['admin_group'])

    def test_ingest_from_directory_returns_summary(self):
        Parser = self._get_parser()
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'domain_users.json'), 'w') as f:
                json.dump(self.SAMPLE_USERS, f)
            with open(os.path.join(tmpdir, 'domain_groups.json'), 'w') as f:
                json.dump(self.SAMPLE_GROUPS, f)
            summary = Parser.ingest_from_directory(tmpdir, assessment_id=0, db_write=False)
            self.assertIn('users', summary)
            self.assertIn('groups', summary)
            self.assertEqual(summary['users'], 1)
            self.assertEqual(summary['groups'], 1)


class TestBloodHoundParser(TestCase):

    SAMPLE_BH_USERS = {
        "data": [
            {
                "Properties": {
                    "name": "JDOE@CORP.EXAMPLE.COM",
                    "domain": "CORP.EXAMPLE.COM",
                    "enabled": True,
                    "admincount": True,
                    "email": "jdoe@corp.example.com",
                    "lastlogon": 133000000000,
                    "objectid": "S-1-5-21-1234-5678-9012-1001",
                },
                "PrimaryGroupSid": "S-1-5-21-1234-5678-9012-513",
            }
        ],
        "meta": {"type": "users", "count": 1}
    }

    SAMPLE_BH_GROUPS = {
        "data": [
            {
                "Properties": {
                    "name": "DOMAIN ADMINS@CORP.EXAMPLE.COM",
                    "domain": "CORP.EXAMPLE.COM",
                    "objectid": "S-1-5-21-1234-5678-9012-512",
                    "admincount": True,
                },
                "Members": [
                    {"MemberId": "S-1-5-21-1234-5678-9012-1001",
                     "MemberType": "User"}
                ]
            }
        ],
        "meta": {"type": "groups", "count": 1}
    }

    def _get_parser(self):
        try:
            from plugins_data.active_directory.backend.ingestion.bloodhound_parser import BloodHoundParser
            return BloodHoundParser
        except ImportError:
            self.skipTest("Plugin not installed")

    def test_parse_users_returns_normalised_dict(self):
        Parser = self._get_parser()
        users = Parser.parse_users(self.SAMPLE_BH_USERS['data'])
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['sam_account_name'], 'JDOE')
        self.assertTrue(users[0]['admin_count'] > 0)

    def test_parse_groups_detects_admin_group(self):
        Parser = self._get_parser()
        groups = Parser.parse_groups(self.SAMPLE_BH_GROUPS['data'])
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]['admin_group'])

    def test_parse_groups_returns_member_edges(self):
        Parser = self._get_parser()
        groups = Parser.parse_groups(self.SAMPLE_BH_GROUPS['data'])
        self.assertIn('members', groups[0])
        self.assertEqual(len(groups[0]['members']), 1)


class TestExposureCorrelationEngine(TestCase):

    def _get_engine(self):
        try:
            from plugins_data.active_directory.backend.correlation.engine import ExposureCorrelationEngine
            return ExposureCorrelationEngine
        except ImportError:
            self.skipTest("Plugin not installed")

    def test_classify_exposure_type_adfs(self):
        Engine = self._get_engine()
        result = Engine.classify_hostname('adfs.corp.example.com')
        self.assertEqual(result, 'ADFS')

    def test_classify_exposure_type_owa(self):
        Engine = self._get_engine()
        result = Engine.classify_hostname('owa.corp.example.com')
        self.assertEqual(result, 'OWA')

    def test_classify_exposure_type_vpn(self):
        Engine = self._get_engine()
        result = Engine.classify_hostname('vpn.corp.example.com')
        self.assertEqual(result, 'VPN')

    def test_classify_returns_other_for_unknown(self):
        Engine = self._get_engine()
        result = Engine.classify_hostname('www.corp.example.com')
        self.assertEqual(result, 'OTHER')

    def test_score_exposure_adfs_is_high(self):
        Engine = self._get_engine()
        score = Engine.score_exposure('ADFS', is_internet_facing=True,
                                       has_domain_correlation=True)
        self.assertGreaterEqual(score, 70.0)

    def test_score_exposure_other_no_correlation_is_low(self):
        Engine = self._get_engine()
        score = Engine.score_exposure('OTHER', is_internet_facing=False,
                                       has_domain_correlation=False)
        self.assertLess(score, 30.0)
