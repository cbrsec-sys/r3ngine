# Active Directory Intelligence Plugin — Phase 2: Graph Intelligence

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full Neo4j identity graph schema, data ingestion pipelines (LDAP exports, BloodHound JSON), and the exposure correlation engine — turning raw discovery data into a queryable identity intelligence graph.

**Architecture:** All AD node types and relationships are managed through a dedicated `ADGraphManager` that wraps `Neo4jManager`. Ingestion pipelines normalize raw tool output into semantic graph entities (never raw data directly into Neo4j). The exposure correlation engine links external attack surface data to internal identity infrastructure via shared DNS/IP indicators.

**Prerequisites:** Phase 1 complete. Plugin installed in `web/plugins_data/active_directory/`.

**Tech Stack:** Python 3.11, neo4j 5.23.1, Django 3.2, temporalio 1.6.0

**Spec coverage:** agint.md Phases 2, 4, 5 (graph architecture, ingestion pipelines, exposure correlation)

---

## File Map

| File | Action |
|---|---|
| `r3ngine-plugins/active_directory/backend/graph/__init__.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/graph/schema.py` | **Create** — node/relationship definitions |
| `r3ngine-plugins/active_directory/backend/graph/manager.py` | **Create** — ADGraphManager |
| `r3ngine-plugins/active_directory/backend/ingestion/__init__.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/ingestion/ldap_parser.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/ingestion/bloodhound_parser.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/ingestion/cert_parser.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/correlation/engine.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/temporal_exports.py` | **Modify** — add 4 ingestion activities |
| `r3ngine-plugins/active_directory/backend/api.py` | **Modify** — wire ingest endpoint to parsers |
| `web/tests/test_ad_plugin_graph.py` | **Create** |

---

## Task 1: Neo4j graph schema definitions

**Context:** All AD entities use dedicated node labels prefixed with `AD` to avoid collision with the existing scan graph (`Domain`, `Subdomain`, etc.). Relationships use the `AD_` prefix. The schema module defines label constants, property maps, and constraint Cypher statements.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/graph/__init__.py`
- Create: `r3ngine-plugins/active_directory/backend/graph/schema.py`

- [ ] **Step 1.1: Write schema tests**

```python
# web/tests/test_ad_plugin_graph.py
from django.test import TestCase


class TestADGraphSchema(TestCase):

    def _import_schema(self):
        try:
            from plugins_data.active_directory.backend.graph import schema
            return schema
        except ImportError:
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
```

- [ ] **Step 1.2: Run tests (expected: SKIP)**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestADGraphSchema -v 2
```

- [ ] **Step 1.3: Create graph/__init__.py**

```python
# r3ngine-plugins/active_directory/backend/graph/__init__.py
```

- [ ] **Step 1.4: Create graph/schema.py**

```python
# r3ngine-plugins/active_directory/backend/graph/schema.py
"""
Neo4j graph schema for Active Directory Intelligence.

All node labels use the AD prefix to avoid collision with the core r3ngine
graph (which uses Domain, Subdomain, IP, etc.). Relationships use AD_ prefix.
"""

# ---------------------------------------------------------------------------
# Node Labels
# ---------------------------------------------------------------------------

ADDomainNode = 'ADDomain'
ADForestNode = 'ADForest'
ADOUNode = 'ADOU'
ADUserNode = 'ADUser'
ADGroupNode = 'ADGroup'
ADComputerNode = 'ADComputer'
ADServiceNode = 'ADService'
ADCertificateNode = 'ADCertificate'
ADTrustNode = 'ADTrust'
ADSubnetNode = 'ADSubnet'
ADSiteNode = 'ADSite'
ADPolicyNode = 'ADPolicy'
ADExposureNode = 'ADExposure'
ADFindingNode = 'ADFinding'
ADIdentityProviderNode = 'ADIdentityProvider'
ADVPNGatewayNode = 'ADVPNGateway'
ADAuthServiceNode = 'ADAuthService'

# ---------------------------------------------------------------------------
# Relationship Types
# ---------------------------------------------------------------------------

AD_MEMBER_OF = 'AD_MEMBER_OF'
AD_TRUSTS = 'AD_TRUSTS'
AD_CONNECTED_TO = 'AD_CONNECTED_TO'
AD_LOCATED_IN = 'AD_LOCATED_IN'
AD_AUTHENTICATES_TO = 'AD_AUTHENTICATES_TO'
AD_EXPOSES = 'AD_EXPOSES'
AD_LINKED_TO = 'AD_LINKED_TO'
AD_BELONGS_TO = 'AD_BELONGS_TO'
AD_PROTECTED_BY = 'AD_PROTECTED_BY'
AD_ROUTES_THROUGH = 'AD_ROUTES_THROUGH'

# ---------------------------------------------------------------------------
# Node property maps — define canonical properties per node type
# ---------------------------------------------------------------------------

DOMAIN_PROPERTIES = {
    'fqdn': str,
    'name': str,
    'sid': str,
    'forest_root': bool,
    'functional_level': str,
    'dc_count': int,
    'user_count': int,
    'group_count': int,
    'computer_count': int,
    'assessment_id': int,
}

USER_PROPERTIES = {
    'sam_account_name': str,
    'display_name': str,
    'email': str,
    'enabled': bool,
    'admin_count': int,
    'password_never_expires': bool,
    'last_logon': str,
    'sid': str,
    'assessment_id': int,
}

GROUP_PROPERTIES = {
    'name': str,
    'sam_account_name': str,
    'sid': str,
    'admin_group': bool,
    'member_count': int,
    'assessment_id': int,
}

COMPUTER_PROPERTIES = {
    'name': str,
    'fqdn': str,
    'os': str,
    'os_version': str,
    'enabled': bool,
    'last_logon': str,
    'sid': str,
    'assessment_id': int,
}

TRUST_PROPERTIES = {
    'source_domain': str,
    'target_domain': str,
    'direction': str,
    'trust_type': str,
    'is_transitive': bool,
    'is_selective_auth': bool,
    'risk_score': float,
    'assessment_id': int,
}

EXPOSURE_PROPERTIES = {
    'hostname': str,
    'ip_address': str,
    'port': int,
    'exposure_type': str,
    'risk_score': float,
    'assessment_id': int,
}

# ---------------------------------------------------------------------------
# Constraint and index statements
# ---------------------------------------------------------------------------

CONSTRAINT_STATEMENTS = [
    "CREATE CONSTRAINT ad_domain_fqdn_unique IF NOT EXISTS "
    "FOR (n:ADDomain) REQUIRE (n.fqdn, n.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_user_sid_unique IF NOT EXISTS "
    "FOR (n:ADUser) REQUIRE (n.sid, n.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_group_sid_unique IF NOT EXISTS "
    "FOR (n:ADGroup) REQUIRE (n.sid, n.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_computer_sid_unique IF NOT EXISTS "
    "FOR (n:ADComputer) REQUIRE (n.sid, n.assessment_id) IS UNIQUE",

    "CREATE INDEX ad_domain_assessment_idx IF NOT EXISTS "
    "FOR (n:ADDomain) ON (n.assessment_id)",

    "CREATE INDEX ad_exposure_type_idx IF NOT EXISTS "
    "FOR (n:ADExposure) ON (n.exposure_type, n.assessment_id)",

    "CREATE INDEX ad_finding_severity_idx IF NOT EXISTS "
    "FOR (n:ADFinding) ON (n.severity, n.assessment_id)",
]
```

- [ ] **Step 1.5: Run tests (expected: PASS if plugin is installed)**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestADGraphSchema -v 2
```

- [ ] **Step 1.6: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/graph/
git commit -m "feat(ad-plugin): add Neo4j graph schema (17 node labels, 10 relationships, constraints)"
```

---

## Task 2: ADGraphManager

**Context:** Wraps `Neo4jManager` with AD-specific CRUD, relationship creation, pathfinding, and schema initialisation. All graph operations go through this manager — no raw Cypher outside this file.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/graph/manager.py`

- [ ] **Step 2.1: Write manager tests**

Add to `web/tests/test_ad_plugin_graph.py`:

```python
class TestADGraphManager(TestCase):

    def _get_manager(self):
        try:
            from plugins_data.active_directory.backend.graph.manager import ADGraphManager
            return ADGraphManager
        except ImportError:
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
```

- [ ] **Step 2.2: Create graph/manager.py**

```python
# r3ngine-plugins/active_directory/backend/graph/manager.py
import logging
from typing import Any, Dict, List, Optional

from . import schema as s

logger = logging.getLogger(__name__)


class ADGraphManager:
    """
    AD-specific Neo4j graph operations.

    Wraps reNgine's Neo4jManager driver. All Cypher is isolated here.
    Callers never write Cypher directly.
    """

    def __init__(self):
        from reNgine.graph_utils import Neo4jManager
        self._core = Neo4jManager()
        self._driver = self._core.driver

    def close(self):
        try:
            self._driver.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Apply constraints and indexes. Safe to call repeatedly (IF NOT EXISTS)."""
        with self._driver.session() as session:
            for stmt in s.CONSTRAINT_STATEMENTS:
                try:
                    session.run(stmt)
                except Exception as exc:
                    logger.warning(f"[ADGraph] Schema statement skipped: {exc}")

    # ------------------------------------------------------------------
    # Node upserts
    # ------------------------------------------------------------------

    def upsert_domain(self, props: Dict[str, Any]) -> Optional[int]:
        """MERGE ADDomain on (fqdn, assessment_id). Returns Neo4j internal id."""
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADDomainNode} {{fqdn: $fqdn, assessment_id: $assessment_id}})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                fqdn=props['fqdn'],
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    def upsert_user(self, props: Dict[str, Any]) -> Optional[int]:
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADUserNode} {{sid: $sid, assessment_id: $assessment_id}})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                sid=props.get('sid', props.get('sam_account_name', 'unknown')),
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    def upsert_group(self, props: Dict[str, Any]) -> Optional[int]:
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADGroupNode} {{sid: $sid, assessment_id: $assessment_id}})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                sid=props.get('sid', props.get('name', 'unknown')),
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    def upsert_computer(self, props: Dict[str, Any]) -> Optional[int]:
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADComputerNode} {{sid: $sid, assessment_id: $assessment_id}})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                sid=props.get('sid', props.get('name', 'unknown')),
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    def upsert_exposure(self, props: Dict[str, Any]) -> Optional[int]:
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADExposureNode} {{
                    hostname: $hostname, assessment_id: $assessment_id
                }})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                hostname=props['hostname'],
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    def upsert_finding(self, props: Dict[str, Any]) -> Optional[int]:
        with self._driver.session() as session:
            result = session.run(
                f"""
                MERGE (n:{s.ADFindingNode} {{
                    title: $title, assessment_id: $assessment_id
                }})
                SET n += $props
                RETURN id(n) AS node_id
                """,
                title=props['title'],
                assessment_id=props['assessment_id'],
                props=props,
            )
            record = result.single()
            return record['node_id'] if record else None

    # ------------------------------------------------------------------
    # Relationship creation
    # ------------------------------------------------------------------

    def create_trust_relationship(
            self, source_fqdn: str, target_fqdn: str,
            assessment_id: int, props: Optional[Dict] = None) -> None:
        """Create AD_TRUSTS between two ADDomain nodes."""
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (a:{s.ADDomainNode} {{fqdn: $src, assessment_id: $aid}})
                MATCH (b:{s.ADDomainNode} {{fqdn: $tgt, assessment_id: $aid}})
                MERGE (a)-[r:{s.AD_TRUSTS}]->(b)
                SET r += $props
                """,
                src=source_fqdn,
                tgt=target_fqdn,
                aid=assessment_id,
                props=props or {},
            )

    def create_membership_relationship(
            self, member_sid: str, member_label: str,
            group_sid: str, assessment_id: int) -> None:
        """Create AD_MEMBER_OF from a user/computer to a group."""
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (m:{member_label} {{sid: $msid, assessment_id: $aid}})
                MATCH (g:{s.ADGroupNode} {{sid: $gsid, assessment_id: $aid}})
                MERGE (m)-[:{s.AD_MEMBER_OF}]->(g)
                """,
                msid=member_sid,
                gsid=group_sid,
                aid=assessment_id,
            )

    def create_exposure_link(
            self, exposure_hostname: str, domain_fqdn: str,
            assessment_id: int) -> None:
        """Create AD_EXPOSES between ADDomain and ADExposure."""
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (d:{s.ADDomainNode} {{fqdn: $fqdn, assessment_id: $aid}})
                MATCH (e:{s.ADExposureNode} {{hostname: $hostname, assessment_id: $aid}})
                MERGE (e)-[:{s.AD_EXPOSES}]->(d)
                """,
                fqdn=domain_fqdn,
                hostname=exposure_hostname,
                aid=assessment_id,
            )

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    def get_domain_graph(self, assessment_id: int) -> Dict:
        """Return all ADDomain nodes and AD_TRUSTS edges for Cytoscape."""
        with self._driver.session() as session:
            nodes_result = session.run(
                f"MATCH (n:{s.ADDomainNode} {{assessment_id: $aid}}) "
                "RETURN id(n) AS id, n.fqdn AS fqdn, n.name AS name, "
                "n.forest_root AS forest_root, n.dc_count AS dc_count",
                aid=assessment_id,
            )
            edges_result = session.run(
                f"""
                MATCH (a:{s.ADDomainNode} {{assessment_id: $aid}})
                      -[r:{s.AD_TRUSTS}]->
                      (b:{s.ADDomainNode} {{assessment_id: $aid}})
                RETURN id(a) AS source, id(b) AS target,
                       r.direction AS direction, r.trust_type AS trust_type,
                       r.risk_score AS risk_score
                """,
                aid=assessment_id,
            )
            nodes = [
                {'data': {'id': str(r['id']), 'label': r['fqdn'] or r['name'],
                          'forest_root': r['forest_root'],
                          'dc_count': r['dc_count'], 'type': 'domain'}}
                for r in nodes_result
            ]
            edges = [
                {'data': {'id': f"e-{r['source']}-{r['target']}",
                          'source': str(r['source']), 'target': str(r['target']),
                          'direction': r['direction'],
                          'trust_type': r['trust_type'],
                          'risk_score': r['risk_score']}}
                for r in edges_result
            ]
            return {'nodes': nodes, 'edges': edges}

    def get_exposure_paths(self, assessment_id: int) -> Dict:
        """Return exposure nodes and their links to identity infrastructure."""
        with self._driver.session() as session:
            result = session.run(
                f"""
                MATCH (e:{s.ADExposureNode} {{assessment_id: $aid}})
                OPTIONAL MATCH (e)-[r:{s.AD_EXPOSES}]->(d:{s.ADDomainNode})
                RETURN id(e) AS eid, e.hostname AS hostname,
                       e.exposure_type AS etype, e.risk_score AS risk_score,
                       id(d) AS did, d.fqdn AS domain_fqdn
                """,
                aid=assessment_id,
            )
            nodes, edges = [], []
            domain_ids = set()
            for r in result:
                eid = str(r['eid'])
                if not any(n['data']['id'] == eid for n in nodes):
                    nodes.append({'data': {
                        'id': eid, 'label': r['hostname'],
                        'type': 'exposure', 'exposure_type': r['etype'],
                        'risk_score': r['risk_score'],
                    }})
                if r['did'] is not None:
                    did = str(r['did'])
                    if did not in domain_ids:
                        domain_ids.add(did)
                        nodes.append({'data': {
                            'id': did, 'label': r['domain_fqdn'], 'type': 'domain',
                        }})
                    edges.append({'data': {
                        'id': f"ep-{eid}-{did}",
                        'source': eid, 'target': did,
                    }})
            return {'nodes': nodes, 'edges': edges}

    def get_trust_graph(self, assessment_id: int) -> Dict:
        """Alias for get_domain_graph — returns trust topology."""
        return self.get_domain_graph(assessment_id)

    def find_shortest_path(
            self, source_fqdn: str, target_fqdn: str,
            assessment_id: int) -> List[Dict]:
        """Return the shortest path between two AD nodes via any relationship."""
        with self._driver.session() as session:
            result = session.run(
                f"""
                MATCH p = shortestPath(
                    (a:{s.ADDomainNode} {{fqdn: $src, assessment_id: $aid}})-[*]->
                    (b:{s.ADDomainNode} {{fqdn: $tgt, assessment_id: $aid}})
                )
                RETURN [n in nodes(p) | {{id: id(n), label: coalesce(n.fqdn, n.name, n.hostname)}}]
                    AS path_nodes
                LIMIT 1
                """,
                src=source_fqdn,
                tgt=target_fqdn,
                aid=assessment_id,
            )
            record = result.single()
            return record['path_nodes'] if record else []
```

- [ ] **Step 2.3: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestADGraphManager -v 2
```

- [ ] **Step 2.4: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/graph/manager.py
git commit -m "feat(ad-plugin): add ADGraphManager with upserts, relationship creation, and graph queries"
```

---

## Task 3: LDAP export parser

**Context:** `ldapdomaindump` produces JSON files (`domain_users.json`, `domain_groups.json`, `domain_computers.json`, `domain_trusts.json`). The parser normalizes these into Django model + Neo4j node upserts.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/ingestion/__init__.py`
- Create: `r3ngine-plugins/active_directory/backend/ingestion/ldap_parser.py`

- [ ] **Step 3.1: Write LDAP parser tests**

Add to `web/tests/test_ad_plugin_graph.py`:

```python
import json
import tempfile
import os


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
            # assessment_id=0 is a no-op for DB writes in this test
            summary = Parser.ingest_from_directory(tmpdir, assessment_id=0,
                                                    db_write=False)
            self.assertIn('users', summary)
            self.assertIn('groups', summary)
            self.assertEqual(summary['users'], 1)
            self.assertEqual(summary['groups'], 1)
```

- [ ] **Step 3.2: Run tests (expected: SKIP)**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestLDAPParser -v 2
```

- [ ] **Step 3.3: Create ingestion/__init__.py**

```python
# r3ngine-plugins/active_directory/backend/ingestion/__init__.py
```

- [ ] **Step 3.4: Create ingestion/ldap_parser.py**

```python
# r3ngine-plugins/active_directory/backend/ingestion/ldap_parser.py
import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_ADMIN_GROUP_SIDS = {
    '512',   # Domain Admins
    '519',   # Enterprise Admins
    '544',   # Administrators
    '518',   # Schema Admins
}

_ADMIN_GROUP_NAMES = {
    'domain admins', 'enterprise admins', 'schema admins',
    'administrators', 'account operators', 'backup operators',
}


class LDAPParser:
    """
    Parses ldapdomaindump JSON output into normalised entity dicts.

    ldapdomaindump produces:
      domain_users.json     — list of user attribute dicts
      domain_groups.json    — list of group attribute dicts
      domain_computers.json — list of computer attribute dicts
      domain_trusts.json    — list of trust attribute dicts
    """

    # ------------------------------------------------------------------
    # Static parse methods (no DB access)
    # ------------------------------------------------------------------

    @staticmethod
    def _attr(entry: dict, key: str, default=None):
        """Extract first value from ldapdomaindump attribute list."""
        vals = entry.get('attributes', {}).get(key, [])
        if isinstance(vals, list) and vals:
            return vals[0]
        return vals if vals else default

    @classmethod
    def parse_users(cls, raw_users: List[dict]) -> List[dict]:
        results = []
        for entry in raw_users:
            try:
                uac = cls._attr(entry, 'userAccountControl', 512)
                enabled = bool(int(uac) & 2 == 0) if uac else True
                pwd_never = bool(int(uac) & 65536) if uac else False
                results.append({
                    'sam_account_name': cls._attr(entry, 'sAMAccountName', ''),
                    'display_name': cls._attr(entry, 'displayName', ''),
                    'email': cls._attr(entry, 'mail', ''),
                    'enabled': enabled,
                    'admin_count': int(cls._attr(entry, 'adminCount', 0) or 0),
                    'password_never_expires': pwd_never,
                    'last_logon': str(cls._attr(entry, 'lastLogon', '')),
                    'sid': cls._attr(entry, 'objectSid', ''),
                })
            except Exception as exc:
                logger.warning(f"[LDAP] Failed to parse user entry: {exc}")
        return results

    @classmethod
    def parse_groups(cls, raw_groups: List[dict]) -> List[dict]:
        results = []
        for entry in raw_groups:
            try:
                name = cls._attr(entry, 'sAMAccountName', '')
                sid = cls._attr(entry, 'objectSid', '')
                sid_rid = sid.split('-')[-1] if sid else ''
                members_raw = entry.get('attributes', {}).get('member', [])
                members = members_raw if isinstance(members_raw, list) else [members_raw]
                is_admin = (
                    sid_rid in _ADMIN_GROUP_SIDS
                    or name.lower() in _ADMIN_GROUP_NAMES
                )
                results.append({
                    'name': name,
                    'sam_account_name': name,
                    'sid': sid,
                    'admin_group': is_admin,
                    'member_count': len(members),
                    'raw_members': members,
                })
            except Exception as exc:
                logger.warning(f"[LDAP] Failed to parse group entry: {exc}")
        return results

    @classmethod
    def parse_computers(cls, raw_computers: List[dict]) -> List[dict]:
        results = []
        for entry in raw_computers:
            try:
                uac = cls._attr(entry, 'userAccountControl', 0)
                enabled = bool(int(uac) & 2 == 0) if uac else True
                results.append({
                    'name': cls._attr(entry, 'sAMAccountName', '').rstrip('$'),
                    'fqdn': cls._attr(entry, 'dNSHostName', ''),
                    'os': cls._attr(entry, 'operatingSystem', ''),
                    'os_version': cls._attr(entry, 'operatingSystemVersion', ''),
                    'enabled': enabled,
                    'last_logon': str(cls._attr(entry, 'lastLogon', '')),
                    'sid': cls._attr(entry, 'objectSid', ''),
                })
            except Exception as exc:
                logger.warning(f"[LDAP] Failed to parse computer entry: {exc}")
        return results

    @classmethod
    def parse_trusts(cls, raw_trusts: List[dict]) -> List[dict]:
        _direction_map = {0: 'DISABLED', 1: 'INBOUND', 2: 'OUTBOUND', 3: 'BIDIRECTIONAL'}
        _type_map = {1: 'CROSS_LINK', 2: 'FOREST', 3: 'EXTERNAL',
                     4: 'REALM', 5: 'FOREST', 6: 'EXTERNAL'}
        results = []
        for entry in raw_trusts:
            try:
                direction_val = int(cls._attr(entry, 'trustDirection', 3))
                type_val = int(cls._attr(entry, 'trustType', 3))
                trust_attrs = int(cls._attr(entry, 'trustAttributes', 0) or 0)
                results.append({
                    'target_domain': cls._attr(entry, 'trustPartner', ''),
                    'direction': _direction_map.get(direction_val, 'BIDIRECTIONAL'),
                    'trust_type': _type_map.get(type_val, 'EXTERNAL'),
                    'is_transitive': bool(trust_attrs & 0x8),
                    'is_selective_auth': bool(trust_attrs & 0x80),
                })
            except Exception as exc:
                logger.warning(f"[LDAP] Failed to parse trust entry: {exc}")
        return results

    # ------------------------------------------------------------------
    # Full ingestion from a directory of JSON files
    # ------------------------------------------------------------------

    @classmethod
    def ingest_from_directory(
            cls, directory: str, assessment_id: int,
            db_write: bool = True) -> Dict:
        """
        Parse all ldapdomaindump JSON files in `directory` and optionally
        write entities to Django models + Neo4j.

        Returns a summary dict with counts of each entity type.
        """
        summary = {'users': 0, 'groups': 0, 'computers': 0, 'trusts': 0}
        file_map = {
            'domain_users.json': ('users', cls.parse_users),
            'domain_groups.json': ('groups', cls.parse_groups),
            'domain_computers.json': ('computers', cls.parse_computers),
            'domain_trusts.json': ('trusts', cls.parse_trusts),
        }

        parsed = {}
        for filename, (key, parser_fn) in file_map.items():
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        raw = json.load(f)
                    parsed[key] = parser_fn(raw)
                    summary[key] = len(parsed[key])
                except Exception as exc:
                    logger.error(f"[LDAP] Failed to parse {filename}: {exc}")
            else:
                parsed[key] = []

        if db_write and assessment_id:
            cls._write_to_db(assessment_id, parsed)
            cls._write_to_graph(assessment_id, parsed)

        return summary

    @classmethod
    def _write_to_db(cls, assessment_id: int, parsed: dict) -> None:
        """Write parsed entities to Django models (ADDomain is pre-existing from DNS phase)."""
        from ..models import ADDomain, ADFinding, ADAssessment

        try:
            assessment = ADAssessment.objects.get(pk=assessment_id)
        except ADAssessment.DoesNotExist:
            logger.error(f"[LDAP] Assessment {assessment_id} not found")
            return

        # Check for high-value findings
        for user in parsed.get('users', []):
            if user.get('admin_count', 0) > 0 and not user.get('enabled', True):
                ADFinding.objects.get_or_create(
                    assessment=assessment,
                    title=f"Disabled admin account: {user['sam_account_name']}",
                    defaults={
                        'description': (
                            f"Admin account {user['sam_account_name']} is disabled "
                            f"but has adminCount=1. Verify it cannot be re-enabled."),
                        'severity': 'LOW',
                        'finding_type': 'identity_risk',
                        'affected_object': user['sam_account_name'],
                        'evidence': user,
                    }
                )

    @classmethod
    def _write_to_graph(cls, assessment_id: int, parsed: dict) -> None:
        """Write parsed entities to Neo4j via ADGraphManager."""
        try:
            from ..graph.manager import ADGraphManager
            mgr = ADGraphManager()

            for user in parsed.get('users', []):
                mgr.upsert_user({**user, 'assessment_id': assessment_id})

            for group in parsed.get('groups', []):
                mgr.upsert_group({**group, 'assessment_id': assessment_id})

            for computer in parsed.get('computers', []):
                mgr.upsert_computer({**computer, 'assessment_id': assessment_id})

            mgr.close()
        except Exception as exc:
            logger.error(f"[LDAP] Graph write failed: {exc}")
```

- [ ] **Step 3.5: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestLDAPParser -v 2
```

Expected: All 5 tests PASS.

- [ ] **Step 3.6: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/ingestion/
git commit -m "feat(ad-plugin): add LDAPParser (users, groups, computers, trusts)"
```

---

## Task 4: BloodHound JSON parser

**Context:** BloodHound exports 5 JSON file types: `computers.json`, `users.json`, `groups.json`, `domains.json`, `gpos.json`. The parser normalises BloodHound's nested ACL/session format into the same entity dicts as the LDAP parser and builds membership edges.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/ingestion/bloodhound_parser.py`

- [ ] **Step 4.1: Write BloodHound parser tests**

Add to `web/tests/test_ad_plugin_graph.py`:

```python
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
```

- [ ] **Step 4.2: Create ingestion/bloodhound_parser.py**

```python
# r3ngine-plugins/active_directory/backend/ingestion/bloodhound_parser.py
import json
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

_BH_TYPE_MAP = {
    'computers.json': 'computers',
    'users.json': 'users',
    'groups.json': 'groups',
    'domains.json': 'domains',
    'gpos.json': 'gpos',
}


class BloodHoundParser:
    """
    Parses BloodHound v4/v5 JSON export files into normalised entity dicts.

    BloodHound wraps data in {"data": [...], "meta": {...}}. Each entry has
    a "Properties" dict and type-specific relationship arrays (Members, Sessions, etc.)
    """

    @staticmethod
    def _props(entry: dict) -> dict:
        return entry.get('Properties', {})

    @classmethod
    def parse_users(cls, raw_users: List[dict]) -> List[dict]:
        results = []
        for entry in raw_users:
            try:
                props = cls._props(entry)
                name = props.get('name', '')
                sam = name.split('@')[0] if '@' in name else name
                results.append({
                    'sam_account_name': sam,
                    'display_name': props.get('displayname', sam),
                    'email': props.get('email', ''),
                    'enabled': props.get('enabled', True),
                    'admin_count': 1 if props.get('admincount') else 0,
                    'password_never_expires': props.get('pwdneverexpires', False),
                    'last_logon': str(props.get('lastlogon', '')),
                    'sid': props.get('objectid', ''),
                    'domain': props.get('domain', ''),
                    'primary_group_sid': entry.get('PrimaryGroupSid', ''),
                })
            except Exception as exc:
                logger.warning(f"[BH] Failed to parse user: {exc}")
        return results

    @classmethod
    def parse_groups(cls, raw_groups: List[dict]) -> List[dict]:
        results = []
        for entry in raw_groups:
            try:
                props = cls._props(entry)
                name = props.get('name', '').split('@')[0]
                sid = props.get('objectid', '')
                sid_rid = sid.split('-')[-1] if sid else ''
                admin_rids = {'512', '519', '544', '518'}
                admin_names = {
                    'domain admins', 'enterprise admins', 'schema admins',
                    'administrators',
                }
                is_admin = (
                    sid_rid in admin_rids
                    or name.lower() in admin_names
                    or props.get('admincount', False)
                )
                members = [
                    {'sid': m.get('MemberId'), 'type': m.get('MemberType')}
                    for m in entry.get('Members', [])
                ]
                results.append({
                    'name': name,
                    'sam_account_name': name,
                    'sid': sid,
                    'domain': props.get('domain', ''),
                    'admin_group': is_admin,
                    'member_count': len(members),
                    'members': members,
                })
            except Exception as exc:
                logger.warning(f"[BH] Failed to parse group: {exc}")
        return results

    @classmethod
    def parse_computers(cls, raw_computers: List[dict]) -> List[dict]:
        results = []
        for entry in raw_computers:
            try:
                props = cls._props(entry)
                name = props.get('name', '').split('.')[0].upper()
                results.append({
                    'name': name,
                    'fqdn': props.get('name', ''),
                    'os': props.get('operatingsystem', ''),
                    'os_version': '',
                    'enabled': props.get('enabled', True),
                    'last_logon': str(props.get('lastlogontimestamp', '')),
                    'sid': props.get('objectid', ''),
                    'domain': props.get('domain', ''),
                })
            except Exception as exc:
                logger.warning(f"[BH] Failed to parse computer: {exc}")
        return results

    @classmethod
    def parse_domains(cls, raw_domains: List[dict]) -> List[dict]:
        results = []
        for entry in raw_domains:
            try:
                props = cls._props(entry)
                results.append({
                    'fqdn': props.get('name', ''),
                    'name': props.get('name', '').split('.')[0],
                    'sid': props.get('objectid', ''),
                    'forest_root': props.get('isdeleted', False) is False,
                    'functional_level': str(props.get('functionallevel', '')),
                    'trusts': entry.get('Trusts', []),
                })
            except Exception as exc:
                logger.warning(f"[BH] Failed to parse domain: {exc}")
        return results

    # ------------------------------------------------------------------
    # Full ingestion from a directory of BH JSON files
    # ------------------------------------------------------------------

    @classmethod
    def ingest_from_directory(
            cls, directory: str, assessment_id: int,
            db_write: bool = True) -> Dict:
        summary = {'users': 0, 'groups': 0, 'computers': 0, 'domains': 0}

        parser_map = {
            'users.json': ('users', cls.parse_users),
            'groups.json': ('groups', cls.parse_groups),
            'computers.json': ('computers', cls.parse_computers),
            'domains.json': ('domains', cls.parse_domains),
        }

        parsed = {}
        for filename, (key, parser_fn) in parser_map.items():
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        raw = json.load(f)
                    entries = raw.get('data', raw) if isinstance(raw, dict) else raw
                    parsed[key] = parser_fn(entries)
                    summary[key] = len(parsed[key])
                except Exception as exc:
                    logger.error(f"[BH] Failed to parse {filename}: {exc}")
            else:
                parsed[key] = []

        if db_write and assessment_id:
            cls._write_to_graph(assessment_id, parsed)

        return summary

    @classmethod
    def _write_to_graph(cls, assessment_id: int, parsed: dict) -> None:
        try:
            from ..graph.manager import ADGraphManager
            mgr = ADGraphManager()

            for domain in parsed.get('domains', []):
                mgr.upsert_domain({**domain, 'assessment_id': assessment_id})

            for user in parsed.get('users', []):
                mgr.upsert_user({**user, 'assessment_id': assessment_id})

            for group in parsed.get('groups', []):
                mgr.upsert_group({**group, 'assessment_id': assessment_id})
                for member in group.get('members', []):
                    if member['sid'] and member['type']:
                        label_map = {'User': 'ADUser', 'Computer': 'ADComputer',
                                     'Group': 'ADGroup'}
                        label = label_map.get(member['type'])
                        if label:
                            try:
                                mgr.create_membership_relationship(
                                    member['sid'], label,
                                    group['sid'], assessment_id)
                            except Exception:
                                pass

            for computer in parsed.get('computers', []):
                mgr.upsert_computer({**computer, 'assessment_id': assessment_id})

            mgr.close()
        except Exception as exc:
            logger.error(f"[BH] Graph write failed: {exc}")
```

- [ ] **Step 4.3: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestBloodHoundParser -v 2
```

Expected: All 3 tests PASS.

- [ ] **Step 4.4: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/ingestion/bloodhound_parser.py
git commit -m "feat(ad-plugin): add BloodHoundParser (users, groups, computers, domains + member edges)"
```

---

## Task 5: Exposure correlation engine

**Context:** Correlates internet-facing services (from Phase 1 cert/DNS discovery, plus SubScan data if available) with internal identity infrastructure using domain suffix matching, IP resolution, and service fingerprinting.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/correlation/__init__.py`
- Create: `r3ngine-plugins/active_directory/backend/correlation/engine.py`

- [ ] **Step 5.1: Write correlation engine tests**

Add to `web/tests/test_ad_plugin_graph.py`:

```python
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
```

- [ ] **Step 5.2: Create correlation/__init__.py**

```python
# r3ngine-plugins/active_directory/backend/correlation/__init__.py
```

- [ ] **Step 5.3: Create correlation/engine.py**

```python
# r3ngine-plugins/active_directory/backend/correlation/engine.py
import logging
import socket
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_HOSTNAME_PATTERN_MAP = {
    'adfs': 'ADFS',
    'sts': 'ADFS',
    'federation': 'ADFS',
    'owa': 'OWA',
    'webmail': 'OWA',
    'exchange': 'EXCHANGE',
    'mail': 'EXCHANGE',
    'autodiscover': 'EXCHANGE',
    'vpn': 'VPN',
    'remote': 'VPN',
    'sslvpn': 'VPN',
    'rdweb': 'RDP',
    'rdgateway': 'RDP',
    'rds': 'RDP',
    'winrm': 'WINRM',
    'wsman': 'WINRM',
    'ldap': 'LDAP',
    'kerberos': 'KERBEROS',
    'krb': 'KERBEROS',
}

_BASE_SCORES = {
    'ADFS': 85.0,
    'OWA': 75.0,
    'EXCHANGE': 70.0,
    'VPN': 80.0,
    'WINRM': 65.0,
    'SMB': 60.0,
    'LDAP': 55.0,
    'KERBEROS': 70.0,
    'RDP': 60.0,
    'OTHER': 20.0,
}


class ExposureCorrelationEngine:
    """
    Classifies hostnames as identity-infrastructure service types and
    scores their risk based on exposure context.
    """

    @staticmethod
    def classify_hostname(hostname: str) -> str:
        """Return the exposure type for a given hostname."""
        lower = hostname.lower()
        for keyword, etype in _HOSTNAME_PATTERN_MAP.items():
            if keyword in lower:
                return etype
        return 'OTHER'

    @staticmethod
    def score_exposure(
            exposure_type: str,
            is_internet_facing: bool,
            has_domain_correlation: bool,
            port: Optional[int] = None) -> float:
        """
        Compute a risk score 0–100 for an exposed service.

        Factors:
          - Base score by service type
          - +10 if internet-facing
          - +10 if correlated to internal AD domain
          - +5 if running on default port (443, 80, 389, 445, etc.)
        """
        score = _BASE_SCORES.get(exposure_type, 20.0)
        if is_internet_facing:
            score += 10.0
        if has_domain_correlation:
            score += 10.0
        default_ports = {443, 80, 389, 636, 445, 88, 5985, 5986, 3389}
        if port and port in default_ports:
            score += 5.0
        return min(score, 100.0)

    @classmethod
    def correlate_hostname_to_domain(
            cls, hostname: str, domains: List[str]) -> Optional[str]:
        """
        Find the best matching AD domain for a hostname via suffix match.

        Returns the FQDN of the matched domain or None.
        """
        lower_host = hostname.lower()
        best = None
        best_len = 0
        for domain in domains:
            domain_lower = domain.lower()
            if lower_host.endswith('.' + domain_lower) or lower_host == domain_lower:
                if len(domain_lower) > best_len:
                    best = domain
                    best_len = len(domain_lower)
        return best

    @classmethod
    def resolve_ip(cls, hostname: str) -> Optional[str]:
        """Attempt to resolve a hostname to an IP address."""
        try:
            return socket.gethostbyname(hostname)
        except (socket.gaierror, socket.herror):
            return None

    @classmethod
    def run_full_correlation(
            cls, assessment_id: int,
            hostnames: List[str]) -> Dict:
        """
        Run full correlation pass for a list of hostnames against an assessment's
        known domains. Creates/updates ADExposure records and Neo4j exposure nodes.
        """
        from ..models import ADAssessment, ADDomain, ADExposure

        try:
            assessment = ADAssessment.objects.get(pk=assessment_id)
        except ADAssessment.DoesNotExist:
            return {'error': f'Assessment {assessment_id} not found'}

        known_domains = list(
            ADDomain.objects.filter(assessment=assessment)
            .values_list('fqdn', flat=True)
        )

        results = []
        for hostname in hostnames:
            etype = cls.classify_hostname(hostname)
            correlated_fqdn = cls.correlate_hostname_to_domain(
                hostname, known_domains)
            ip = cls.resolve_ip(hostname)
            score = cls.score_exposure(
                etype,
                is_internet_facing=True,
                has_domain_correlation=correlated_fqdn is not None,
            )

            correlated_domain = None
            if correlated_fqdn:
                correlated_domain = ADDomain.objects.filter(
                    assessment=assessment, fqdn=correlated_fqdn).first()

            exposure, created = ADExposure.objects.update_or_create(
                assessment=assessment,
                hostname=hostname,
                exposure_type=etype,
                defaults={
                    'ip_address': ip,
                    'correlated_domain': correlated_domain,
                    'risk_score': score,
                    'evidence': {
                        'source': 'correlation_engine',
                        'classified_type': etype,
                        'correlated_domain': correlated_fqdn,
                    },
                }
            )

            # Create Neo4j exposure node and link
            try:
                from ..graph.manager import ADGraphManager
                mgr = ADGraphManager()
                mgr.upsert_exposure({
                    'hostname': hostname,
                    'ip_address': ip or '',
                    'exposure_type': etype,
                    'risk_score': score,
                    'assessment_id': assessment_id,
                })
                if correlated_fqdn:
                    mgr.create_exposure_link(hostname, correlated_fqdn, assessment_id)
                mgr.close()
            except Exception as exc:
                logger.warning(f"[Correlation] Graph write failed for {hostname}: {exc}")

            results.append({
                'hostname': hostname,
                'type': etype,
                'score': score,
                'correlated_domain': correlated_fqdn,
                'created': created,
            })

        return {'results': results, 'count': len(results)}
```

- [ ] **Step 5.4: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph.TestExposureCorrelationEngine -v 2
```

Expected: All 6 tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/correlation/
git commit -m "feat(ad-plugin): add ExposureCorrelationEngine (hostname classification, risk scoring, domain correlation)"
```

---

## Task 6: Wire ingestion into the ingest API endpoint

**Context:** Phase 1 created a stub `ingest` endpoint that accepted files but didn't process them. Now wire LDAP and BloodHound parsers based on `type` parameter.

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/api.py`

- [ ] **Step 6.1: Update the ingest action in api.py**

Replace the `ingest` action body (the part after `tmp_path = tmp.name`) with:

```python
            tmp_path = tmp.name

        try:
            summary = cls._run_ingestion(ingest_type, tmp_path, assessment.id)
        except Exception as exc:
            logger.error(f"[AD Ingest] Failed: {exc}")
            summary = {'error': str(exc)}
        finally:
            import os as _os
            if _os.path.exists(tmp_path):
                _os.remove(tmp_path)

        return Response({
            'status': 'completed',
            'file': uploaded.name,
            'type': ingest_type,
            'summary': summary,
        })
```

Add the static method to `ADAssessmentViewSet`:

```python
    @staticmethod
    def _run_ingestion(ingest_type: str, file_path: str, assessment_id: int) -> dict:
        import zipfile
        import tempfile
        import shutil

        ingest_type = ingest_type.lower()

        if file_path.endswith('.zip'):
            # Unzip and determine type from contents
            extract_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(extract_dir)
                return ADAssessmentViewSet._run_ingestion(
                    ingest_type, extract_dir, assessment_id)
            finally:
                shutil.rmtree(extract_dir, ignore_errors=True)

        if os.path.isdir(file_path):
            files = os.listdir(file_path)
            if any(f in files for f in
                   ['domain_users.json', 'domain_groups.json', 'domain_computers.json']):
                ingest_type = 'ldap'
            elif any(f in files for f in
                     ['users.json', 'groups.json', 'computers.json']):
                ingest_type = 'bloodhound'

        if ingest_type in ('ldap', 'ldapdomaindump'):
            from ..ingestion.ldap_parser import LDAPParser
            directory = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            return LDAPParser.ingest_from_directory(directory, assessment_id)

        if ingest_type in ('bloodhound', 'bh'):
            from ..ingestion.bloodhound_parser import BloodHoundParser
            directory = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            return BloodHoundParser.ingest_from_directory(directory, assessment_id)

        return {'warning': f'Unknown ingest type: {ingest_type}. Supported: ldap, bloodhound'}
```

- [ ] **Step 6.2: Update the ingest Temporal activity in temporal_exports.py**

Add a new activity that triggers post-ingestion neo4j sync:

```python
# Add to temporal_exports.py

@activity.defn
def run_ingestion_activity(params: dict) -> dict:
    """
    Process a previously uploaded ingestion file and sync results to Neo4j.
    Called as a child step when files are uploaded via the /ingest/ endpoint.
    """
    assessment_id = params['assessment_id']
    file_path = params['file_path']
    ingest_type = params.get('ingest_type', 'auto')

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'data_ingestion',
        'message': f'Processing {ingest_type} data file',
    })

    from .api import ADAssessmentViewSet
    summary = ADAssessmentViewSet._run_ingestion(ingest_type, file_path, assessment_id)

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'data_ingestion',
        'summary': summary,
        'message': 'Data ingestion complete',
    })

    return summary
```

Also add `run_ingestion_activity` to `manifest.yaml` temporal.activities list.

- [ ] **Step 6.3: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/api.py \
        r3ngine-plugins/active_directory/backend/temporal_exports.py \
        r3ngine-plugins/active_directory/manifest.yaml
git commit -m "feat(ad-plugin): wire LDAP/BloodHound ingestion into /ingest/ endpoint and Temporal activity"
```

---

## Task 7: Full graph API endpoint + sync activity update

**Context:** Expose the `ADGraphManager` graph data via REST so the frontend can load Cytoscape-compatible payloads without Neo4j queries from the browser.

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/api.py`

- [ ] **Step 7.1: Add graph endpoints to ADAssessmentViewSet**

Add to `ADAssessmentViewSet`:

```python
    @action(detail=True, methods=['get'], url_path='graph/domains')
    def graph_domains(self, request, pk=None):
        """Cytoscape-compatible domain + trust graph."""
        assessment = self.get_object()
        try:
            from .graph.manager import ADGraphManager
            mgr = ADGraphManager()
            data = mgr.get_domain_graph(assessment.id)
            mgr.close()
            return Response(data)
        except Exception as exc:
            return Response({'nodes': [], 'edges': [], 'error': str(exc)})

    @action(detail=True, methods=['get'], url_path='graph/exposures')
    def graph_exposures(self, request, pk=None):
        """Cytoscape-compatible exposure path graph."""
        assessment = self.get_object()
        try:
            from .graph.manager import ADGraphManager
            mgr = ADGraphManager()
            data = mgr.get_exposure_paths(assessment.id)
            mgr.close()
            return Response(data)
        except Exception as exc:
            return Response({'nodes': [], 'edges': [], 'error': str(exc)})

    @action(detail=True, methods=['get'], url_path='graph/path')
    def graph_path(self, request, pk=None):
        """Shortest path between two AD domain nodes."""
        assessment = self.get_object()
        source = request.query_params.get('source')
        target = request.query_params.get('target')
        if not source or not target:
            return Response({'error': 'source and target query params required'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from .graph.manager import ADGraphManager
            mgr = ADGraphManager()
            path = mgr.find_shortest_path(source, target, assessment.id)
            mgr.close()
            return Response({'path': path})
        except Exception as exc:
            return Response({'path': [], 'error': str(exc)})
```

- [ ] **Step 7.2: Run all Phase 2 tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_graph -v 2
```

Expected: All tests PASS.

- [ ] **Step 7.3: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/api.py
git commit -m "feat(ad-plugin): add graph/domains, graph/exposures, graph/path API endpoints"
```

---

## Phase 2 Complete

The plugin now has:
- Full Neo4j graph schema (17 node labels, 10 relationship types, constraints + indexes)
- `ADGraphManager` — all graph CRUD isolated in one place
- `LDAPParser` — parses `ldapdomaindump` JSON exports
- `BloodHoundParser` — parses BloodHound v4/v5 JSON exports with member edges
- `ExposureCorrelationEngine` — classifies and scores exposed services
- REST endpoints: `/graph/domains/`, `/graph/exposures/`, `/graph/path/`, `/ingest/`

**Next:** Phase 3 — Frontend & Visualization (`2026-05-24-ad-plugin-phase3-frontend.md`)
- React feature directory in `frontend/src/features/active_directory/`
- TanStack Router routes added to `router.tsx`
- Zustand store, TanStack Query API hooks
- Assessment list + detail pages
- Cytoscape.js graph explorer with semantic layouts
- Real-time WebSocket integration
- Trust analytics and exposure dashboard
