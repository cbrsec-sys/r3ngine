import hashlib
import hmac
import secrets

MCP_KEY_PREFIX = 'r3n_mcp_'


def generate_mcp_secret() -> str:
    return MCP_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_mcp_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode('utf-8')).hexdigest()


def display_prefix(secret: str) -> str:
    return secret[:16]


def secrets_match(secret: str, key_hash: str) -> bool:
    digest = hash_mcp_secret(secret)
    return hmac.compare_digest(digest, key_hash)
