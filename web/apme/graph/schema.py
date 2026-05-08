"""
APME Configuration

Defines canonical node types and subtypes for the attack graph.
This maps directly to the graph schema used in both Neo4j and in-memory representations.
"""

NODE_TYPES = {
    "Asset": ["domain", "ip", "service", "host", "endpoint"],
    "Vulnerability": ["sqli", "xss", "rce", "ssrf", "lfi", "ssti", "misconfig", "xxe", "open_redirect", "generic"],
    "Credential": ["api_key", "password", "token", "certificate", "ssh_key"],
    "Identity": ["user", "admin", "service_account"],
    "Privilege": ["user", "admin", "domain_admin", "root"],
    "Network": ["internet", "external", "internal", "dmz"],
    "Capability": ["db_access", "data_exfil", "rce_execution", "authenticated_access", "pivot", "cloud_access"],
}

# Required edge types (MUST be kept in sync with models/edge.py EDGE_TYPES)
EDGE_TYPES = [
    "RESOLVES_TO",    # domain -> ip
    "HOSTS",          # ip -> service
    "EXPOSES",        # service -> vulnerability
    "LEADS_TO",       # vulnerability -> capability
    "AUTHENTICATES",  # credential -> service
    "ESCALATES_TO",   # identity -> privilege
    "TRUSTS",         # system -> system
    "CONNECTED_TO",   # network pivot
]
