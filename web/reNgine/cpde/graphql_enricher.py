"""
graphql_enricher.py — GraphQL Variable Persistence from InQL Output

InQL is already integrated in web_api_discovery and discovers GraphQL
operations (queries, mutations, subscriptions). However, it saves endpoints
only — it does not call save_parameter() for the operation variables.

This module reads the InQL output directory structure and extracts variable
definitions, then persists them as Parameter records tagged with:
  - param_location = 'graphql_var'
  - observed_in_graphql = True
  - confidence = 85
  - type = 'InQL (GraphQL Variable)'

InQL Output Structure
---------------------
InQL writes one directory per target host:

    {results_dir}/inql_{subdomain}/
        query/
            {OperationName}.graphql      ← query operation
        mutation/
            {OperationName}.graphql      ← mutation operation
        subscription/
            {OperationName}.graphql      ← subscription operation

Each .graphql file contains the full operation text with variable definitions
in the form:  query OperationName($varName: VarType!) { ... }
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Regex to extract variable definitions from a GraphQL operation header.
# Matches: ($variableName: TypeName, $otherVar: OtherType!)
_RE_GQL_VARS = re.compile(
    r'\$([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_![\]]*)',
)

# Mapping from GraphQL scalar type names to CPDE data_type values
_GQL_TYPE_MAP = {
    'String': 'string',
    'Int': 'number',
    'Float': 'number',
    'Boolean': 'boolean',
    'ID': 'string',
}


def _parse_graphql_file(filepath: str) -> list[dict]:
    """Parse a single .graphql file and return variable findings.

    Args:
        filepath (str): Absolute path to the .graphql operation file.

    Returns:
        list[dict]: Variable findings with name, data_type, and context.
    """
    findings = []
    try:
        with open(filepath, encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        for m in _RE_GQL_VARS.finditer(content):
            var_name = m.group(1)
            gql_type_raw = m.group(2).rstrip('!').strip('[]').rstrip('!')
            data_type = _GQL_TYPE_MAP.get(gql_type_raw, 'string')

            findings.append({
                'name': var_name,
                'data_type': data_type,
                'context': os.path.basename(filepath),
            })

    except OSError as exc:
        logger.warning('[CPDE:graphql] Failed to read %s: %s', filepath, exc)

    return findings


def enrich_graphql_params(
    inql_output_dir: str,
    endpoint_url: str,
    subdomain,
    ctx: dict,
) -> int:
    """Parse InQL output directory and persist GraphQL variables as Parameters.

    Called immediately after InQL runs in web_api_discovery. Reads all
    .graphql files, extracts variable definitions, and calls save_parameter()
    for each variable.

    Args:
        inql_output_dir (str): Path to the InQL output directory for this subdomain
                               (e.g. {results_dir}/inql_{subdomain_name}).
        endpoint_url (str): The GraphQL endpoint URL (used to resolve/create endpoint).
        subdomain: Subdomain Django model instance.
        ctx (dict): Scan context dict (scan_history_id, domain_id, etc.).

    Returns:
        int: Number of new Parameter records created.
    """
    if not os.path.isdir(inql_output_dir):
        logger.debug(
            '[CPDE:graphql] InQL output directory not found: %s', inql_output_dir
        )
        return 0

    # Lazy imports — avoids Django ORM at module import time
    from reNgine.utils.task import save_endpoint, save_parameter

    # Ensure the GraphQL endpoint is registered in the DB
    endpoint, _ = save_endpoint(
        endpoint_url,
        ctx=ctx,
        subdomain=subdomain,
        source='InQL (GraphQL Found)',
    )
    if not endpoint:
        logger.warning(
            '[CPDE:graphql] Could not resolve endpoint for %s — skipping variable persistence',
            endpoint_url,
        )
        return 0

    scan_history_id = ctx.get('scan_history_id')
    created_count = 0

    # Walk through query/, mutation/, subscription/ subdirectories
    for op_type in ('query', 'mutation', 'subscription'):
        op_dir = os.path.join(inql_output_dir, op_type)
        if not os.path.isdir(op_dir):
            continue

        for filename in os.listdir(op_dir):
            if not filename.endswith('.graphql'):
                continue

            filepath = os.path.join(op_dir, filename)
            variable_findings = _parse_graphql_file(filepath)

            for finding in variable_findings:
                _, created = save_parameter(
                    endpoint=endpoint,
                    name=finding['name'],
                    param_type='InQL (GraphQL Variable)',
                    confidence=85,
                    sources=['inql', 'graphql'],
                    param_location='graphql_var',
                    data_type=finding.get('data_type'),
                    observed_in_graphql=True,
                    scan_history_id=scan_history_id,
                )
                if created:
                    created_count += 1

    logger.info(
        '[CPDE:graphql] Persisted %d new GraphQL variable parameters from %s',
        created_count, inql_output_dir,
    )
    return created_count
