"""
TypedDict definitions for Temporal workflow context.

ScanContext is the primary data contract between workflow orchestrators and
activities. TypedDict is a zero-runtime-cost type annotation — it produces
no class at runtime beyond a plain dict.
"""
from typing import Any, Dict, List, Optional, TypedDict

try:
    from typing import Required
except ImportError:
    from typing_extensions import Required


class ScanContext(TypedDict, total=False):
    """Temporal workflow context for a full scan, subscan, or stress test.

    Fields marked Required[] must be present when the workflow starts.
    All other fields are optional.
    """
    # Required at workflow start
    scan_history_id: Required[int]
    engine_id: Required[int]
    domain_id: Required[int]

    # Set by TargetProfilingActivity
    domain_name: str
    results_dir: str
    yaml_configuration: Dict[str, Any]
    tasks: List[str]

    # Subscan / per-subdomain fields
    subdomain_id: Optional[int]
    subscan_id: Optional[int]
    subdomain_name: Optional[str]
    subdomain_http_url: Optional[str]

    # Scan configuration
    out_of_scope_subdomains: List[str]
    starting_point_path: str
    excluded_paths: List[str]
    imported_subdomains: List[str]

    # Activity tracking
    activity_id: Optional[int]
    track: bool

    # Stress test fields
    target_domain_name: Optional[str]
    stress_config: Optional[Dict[str, Any]]
    resolved_endpoints: Optional[List[str]]
    stress_result_id: Optional[int]
    current_endpoint: Optional[str]
    current_tool: Optional[str]

    # API discovery
    api_discovery_tools: Optional[List[str]]
    kr_wordlist: Optional[str]
