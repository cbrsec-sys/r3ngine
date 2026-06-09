"""
Routes a target (value + type) to the appropriate Temporal workflow name
and builds the initial context dict for that workflow.

This is the central dispatch table for all 11 target types. When a new
scan is created via the API, initiate_scan_temporal() calls this module
to determine which workflow to start instead of always using MasterScanWorkflow.
"""
import ipaddress
import re
from typing import Tuple, Dict, Any, Optional

from reNgine.definitions import (
    TARGET_TYPE_DOMAIN,
    TARGET_TYPE_HOST,
    TARGET_TYPE_SUBDOMAIN,
    TARGET_TYPE_URL,
    TARGET_TYPE_IP,
    TARGET_TYPE_CIDR,
    TARGET_TYPE_EMAIL,
    TARGET_TYPE_USERNAME,
    TARGET_TYPE_PHONE,
    TARGET_TYPE_CRYPTO_ADDRESS,
    TARGET_TYPE_CODE_PATH,
)

# Maps target_type → (workflow_name, context_key_for_target)
_ROUTING_TABLE: Dict[str, Tuple[str, str]] = {
    TARGET_TYPE_DOMAIN:         ('MasterScanWorkflow',      'domain'),
    TARGET_TYPE_HOST:           ('HostReconWorkflow',        'target'),
    TARGET_TYPE_SUBDOMAIN:      ('SubdomainReconWorkflow',   'domain'),
    TARGET_TYPE_URL:            ('URLCrawlWorkflow',         'urls'),
    TARGET_TYPE_IP:             ('HostReconWorkflow',        'target'),
    TARGET_TYPE_CIDR:           ('CIDRReconWorkflow',        'cidr'),
    TARGET_TYPE_EMAIL:          ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_USERNAME:       ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_PHONE:          ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_CRYPTO_ADDRESS: ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_CODE_PATH:      ('CodeScanWorkflow',         'target'),
}


def infer_target_type(value: str) -> str:
    """Auto-detect target type from value string.

    Used when target_type is not explicitly provided.
    Preference order: cidr → ip → url → email → domain (fallback).
    """
    value = value.strip()
    if not value:
        return TARGET_TYPE_DOMAIN

    # CIDR range (before IP check)
    if '/' in value:
        try:
            ipaddress.ip_network(value, strict=False)
            return TARGET_TYPE_CIDR
        except ValueError:
            pass

    # Single IP address
    try:
        ipaddress.ip_address(value)
        return TARGET_TYPE_IP
    except ValueError:
        pass

    # Code path / git URL — checked before generic URL so repo.git takes priority
    if value.endswith('.git') or value.startswith('/') or value.startswith('git@'):
        return TARGET_TYPE_CODE_PATH

    # URL
    if value.startswith(('http://', 'https://')):
        return TARGET_TYPE_URL

    # Email address
    if re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', value):
        return TARGET_TYPE_EMAIL

    # Crypto address heuristics (long hex/base58, no dots)
    if len(value) >= 26 and '.' not in value and re.match(r'^[a-zA-Z0-9]+$', value):
        return TARGET_TYPE_CRYPTO_ADDRESS

    # Default: domain name
    return TARGET_TYPE_DOMAIN


def route_target_to_workflow(
    target_value: str,
    target_type: Optional[str] = None,
    scan_history_id: Optional[int] = None,
    yaml_configuration: Optional[dict] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Determine which Temporal workflow handles this target type.

    Args:
        target_value: The raw target string (domain name, CIDR, email, etc.)
        target_type: One of the TARGET_TYPE_* constants. Auto-inferred if None.
        scan_history_id: Optional ScanHistory PK to embed in context.
        yaml_configuration: Optional YAML scan config dict.

    Returns:
        (workflow_name, ctx) tuple. workflow_name is the @workflow.defn name.
        ctx is a ready-to-pass dict for workflow.run(ctx).
    """
    effective_type = target_type or infer_target_type(target_value)

    if effective_type not in _ROUTING_TABLE:
        effective_type = TARGET_TYPE_DOMAIN

    workflow_name, ctx_key = _ROUTING_TABLE[effective_type]

    ctx: Dict[str, Any] = {
        'scan_history_id': scan_history_id,
        'target_type': effective_type,
        'yaml_configuration': yaml_configuration or {},
    }

    if ctx_key == 'urls':
        ctx['urls'] = [target_value]
    else:
        ctx[ctx_key] = target_value

    return workflow_name, ctx
