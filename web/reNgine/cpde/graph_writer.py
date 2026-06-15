"""
graph_writer.py — Neo4j Graph Enrichment for CPDE

Writes CPDE-specific nodes and relationships to Neo4j that are not covered
by the existing SyncGraphActivity (which handles base Parameter nodes).

New node types
--------------
(:JSFile)        — Represents a JS file that was AST-analysed.
(:OpenAPISpec)   — Represents a discovered OpenAPI/Swagger spec.

New relationship types
----------------------
(:Parameter)-[:OBSERVED_IN]->(:JSFile)
(:Endpoint)-[:DISCOVERED_FROM]->(:OpenAPISpec)

This module is designed to be called from the CPDE task after parameters
have been persisted to PostgreSQL, supplementing (not replacing) the main
graph sync that runs via SyncGraphActivity.
"""

import logging

logger = logging.getLogger(__name__)


def write_js_sources(
    driver,
    scan_id: int,
    parameter_js_map: list[dict],
) -> None:
    """Write JSFile nodes and OBSERVED_IN relationships to Neo4j.

    Args:
        driver: Neo4j driver instance.
        scan_id (int): ScanHistory ID for scoping graph nodes.
        parameter_js_map (list[dict]): Each entry has:
            - endpoint_url (str)
            - param_name (str)
            - js_url (str)

    Example Cypher:
        MERGE (:JSFile {url: $js_url, scan_id: $scan_id})
        MERGE (:Parameter {name: $param_name, endpoint_url: $endpoint_url})
            -[:OBSERVED_IN]->(:JSFile {url: $js_url})
    """
    if not driver or not parameter_js_map:
        return

    query = """
    UNWIND $rows AS row
    MERGE (jf:JSFile {url: row.js_url, scan_id: row.scan_id})
    WITH jf, row
    MATCH (p:Parameter {name: row.param_name})
          -[:HAS_PARAMETER]-(e:Endpoint {url: row.endpoint_url, scan_id: row.scan_id})
    MERGE (p)-[:OBSERVED_IN]->(jf)
    """
    rows = [
        {
            'scan_id': scan_id,
            'js_url': entry['js_url'],
            'param_name': entry['param_name'],
            'endpoint_url': entry['endpoint_url'],
        }
        for entry in parameter_js_map
    ]

    try:
        with driver.session() as session:
            session.run(query, rows=rows)
        logger.info(
            '[CPDE:graph] Wrote %d JSFile OBSERVED_IN relationships for scan %d',
            len(rows), scan_id,
        )
    except Exception as exc:
        logger.error('[CPDE:graph] Failed to write JS source relationships: %s', exc)


def write_openapi_sources(
    driver,
    scan_id: int,
    endpoint_spec_map: list[dict],
) -> None:
    """Write OpenAPISpec nodes and DISCOVERED_FROM relationships to Neo4j.

    Args:
        driver: Neo4j driver instance.
        scan_id (int): ScanHistory ID for scoping graph nodes.
        endpoint_spec_map (list[dict]): Each entry has:
            - endpoint_url (str)
            - spec_url (str)
            - spec_title (str, optional)

    Example Cypher:
        MERGE (:OpenAPISpec {url: $spec_url, scan_id: $scan_id})
        MATCH (:Endpoint {url: $endpoint_url, scan_id: $scan_id})
        MERGE (:Endpoint)-[:DISCOVERED_FROM]->(:OpenAPISpec)
    """
    if not driver or not endpoint_spec_map:
        return

    query = """
    UNWIND $rows AS row
    MERGE (spec:OpenAPISpec {url: row.spec_url, scan_id: row.scan_id})
    ON CREATE SET spec.title = row.spec_title
    WITH spec, row
    MATCH (e:Endpoint {url: row.endpoint_url, scan_id: row.scan_id})
    MERGE (e)-[:DISCOVERED_FROM]->(spec)
    """
    rows = [
        {
            'scan_id': scan_id,
            'spec_url': entry['spec_url'],
            'spec_title': entry.get('spec_title', ''),
            'endpoint_url': entry['endpoint_url'],
        }
        for entry in endpoint_spec_map
    ]

    try:
        with driver.session() as session:
            session.run(query, rows=rows)
        logger.info(
            '[CPDE:graph] Wrote %d OpenAPISpec DISCOVERED_FROM relationships for scan %d',
            len(rows), scan_id,
        )
    except Exception as exc:
        logger.error('[CPDE:graph] Failed to write OpenAPI source relationships: %s', exc)


def enrich_parameter_nodes(
    driver,
    scan_id: int,
    parameters: list[dict],
) -> None:
    """Update existing Parameter nodes in Neo4j with CPDE intelligence properties.

    This is run after the main SyncGraphActivity has already created base
    Parameter nodes. It adds confidence, param_location, and is_auth_related
    properties to existing nodes.

    Args:
        driver: Neo4j driver instance.
        scan_id (int): ScanHistory ID for node matching.
        parameters (list[dict]): Each entry has:
            - name (str)
            - endpoint_url (str)
            - confidence (int)
            - param_location (str)
            - is_auth_related (bool)
    """
    if not driver or not parameters:
        return

    query = """
    UNWIND $rows AS row
    MATCH (p:Parameter {name: row.name})
          -[:HAS_PARAMETER]-(e:Endpoint {url: row.endpoint_url, scan_id: row.scan_id})
    SET p.confidence = row.confidence,
        p.param_location = row.param_location,
        p.is_auth_related = row.is_auth_related
    """
    rows = [
        {
            'scan_id': scan_id,
            'name': p['name'],
            'endpoint_url': p.get('endpoint_url', ''),
            'confidence': p.get('confidence', 0),
            'param_location': p.get('param_location', ''),
            'is_auth_related': p.get('is_auth_related', False),
        }
        for p in parameters
    ]

    try:
        with driver.session() as session:
            session.run(query, rows=rows)
        logger.info(
            '[CPDE:graph] Enriched %d Parameter nodes with CPDE properties for scan %d',
            len(rows), scan_id,
        )
    except Exception as exc:
        logger.error('[CPDE:graph] Failed to enrich Parameter nodes: %s', exc)
