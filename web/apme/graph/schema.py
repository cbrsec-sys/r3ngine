"""
APME Configuration

Defines canonical node types and subtypes for the attack graph.
"""

NODE_TYPES = {
    "Asset": ["domain", "ip", "service", "host", "endpoint"],
    "Vulnerability": [
        # Injection
        "sqli", "command_injection", "code_injection", "nosql_injection",
        "xpath_injection", "ldap_injection", "log_injection",
        # Template / Server
        "rce", "ssti", "ssrf", "xxe",
        # File
        "lfi", "path_traversal", "file_upload",
        # Deserialization
        "deserialization",
        # Auth / Identity
        "misconfig", "jwt_abuse", "oauth_misconfig", "idor",
        "crlf_injection", "host_header",
        # Client-side
        "xss", "open_redirect", "clickjacking", "csrf",
        # Info
        "cors", "graphql_injection", "prototype_pollution",
        # Cloud / Supply chain
        "s3_misconfig", "subdomain_takeover", "dns_rebinding",
        "dependency_confusion",
        # Fallbacks
        "generic", "generic_high", "generic_critical",
    ],
    "Credential": [
        "api_key", "password", "token", "certificate", "ssh_key",
        "cloud_api_key", "jwt_token", "github_token", "db_password",
        "generic_secret",
    ],
    "Identity":  ["user", "admin", "service_account"],
    "Privilege": ["user", "admin", "domain_admin", "root"],
    "Network":   ["internet", "external", "internal", "dmz"],
    "Technology": [
        "wordpress", "php", "java", "python", "nodejs",
        "nginx", "apache", "spring", "jenkins", "generic",
    ],
    "Capability": [
        # Original
        "db_access", "data_exfil", "rce_execution", "authenticated_access",
        "pivot", "cloud_access", "internal_discovery",
        # New
        "account_takeover", "session_hijacking", "phishing_amplification",
        "persistence", "code_exfiltration", "credential_harvesting",
        "lateral_movement", "metadata_access", "hvt_compromise",
        "supply_chain_compromise", "dos_capability",
    ],
}

EDGE_TYPES = [
    "RESOLVES_TO",    # domain -> ip
    "HOSTS",          # ip -> service
    "EXPOSES",        # service/asset -> vulnerability
    "LEADS_TO",       # vulnerability/capability -> capability
    "AUTHENTICATES",  # credential -> service
    "ESCALATES_TO",   # identity -> privilege
    "TRUSTS",         # system -> system
    "CONNECTED_TO",   # network pivot
    "USES_TECH",      # asset -> technology
]
