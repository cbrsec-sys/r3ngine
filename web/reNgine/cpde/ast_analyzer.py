"""
ast_analyzer.py — JavaScript AST Analysis

Parses downloaded JS files to extract evidence of HTTP parameter usage:
  - fetch() / axios() call argument objects (JSON body shapes)
  - URLSearchParams / FormData key insertions
  - XHR open() calls with URL + query params
  - React/Vue component prop names used in API calls
  - TypeScript-style interface-like object literals passed to fetch

Strategy
--------
1. Try esprima-python for clean AST parsing (handles modern ES6+, decorators).
2. Fall back to regex heuristics for minified/obfuscated bundles that esprima
   cannot parse (syntax errors are common in heavily minified code).

Output format per finding
-------------------------
{
    "name":       "userId",          # parameter name
    "location":   "json_body",       # param_location value
    "data_type":  "string",          # inferred JS type or None
    "source_url": "https://cdn/app.js",
    "confidence": 70,                # base confidence from JS source
    "context":    "fetch('/api'...)" # short code snippet for debugging
}
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Auth-related parameter name patterns ──────────────────────────────────────
_AUTH_PATTERNS = re.compile(
    r'(?i)(token|auth|session|apikey|api[-_]?key|secret|password|passwd|'
    r'credential|bearer|jwt|x[-_]?api[-_]?key|x[-_]?auth|x[-_]?token|'
    r'authorization|access[-_]?token|refresh[-_]?token)',
)

# ── Regex fallback patterns (for minified code) ───────────────────────────────

# fetch('/api/path', { body: JSON.stringify({ key: val }) })
_RE_FETCH_BODY_KEYS = re.compile(
    r'fetch\s*\([^)]+\)\s*\.\s*then|fetch\s*\(["\'][^"\']+["\']',
    re.DOTALL,
)
# Object keys in JSON.stringify({ key: val, ... })
_RE_JSON_STRINGIFY_KEYS = re.compile(
    r'JSON\.stringify\s*\(\s*\{([^}]{0,500})\}',
)
# new URLSearchParams({ key: val }) or params.append('key', val)
_RE_URLSEARCHPARAMS_APPEND = re.compile(
    r'(?:params|searchParams|qs)\.(?:append|set)\s*\(\s*["\']([^"\']+)["\']',
)
_RE_URLSEARCHPARAMS_OBJ = re.compile(
    r'new\s+URLSearchParams\s*\(\s*\{([^}]{0,400})\}',
)
# formData.append('key', val)
_RE_FORMDATA_APPEND = re.compile(
    r'(?:formData|fd|form|data)\.append\s*\(\s*["\']([^"\']+)["\']',
)
# axios({ data: { key: val } }) or axios.get('/path', { params: { key: val } })
_RE_AXIOS_OBJ_KEYS = re.compile(
    r'axios(?:\.[a-z]+)?\s*\(\s*\{[^}]*(?:data|params)\s*:\s*\{([^}]{0,400})\}',
    re.DOTALL,
)
# Simple object literal key names: { userId: ..., role: ... }
_RE_OBJ_KEYS = re.compile(r'["\']?([a-zA-Z_$][a-zA-Z0-9_$]*)["\']?\s*:')


def _is_auth_related(name: str) -> bool:
    """Return True when the parameter name matches known auth patterns."""
    return bool(_AUTH_PATTERNS.search(name))


def _extract_keys_from_obj_literal(obj_text: str) -> list[str]:
    """Extract property keys from a JS object literal substring.

    Args:
        obj_text (str): Raw text of an object literal body (between { and }).

    Returns:
        list[str]: Extracted key names.
    """
    keys = []
    for m in _RE_OBJ_KEYS.finditer(obj_text):
        key = m.group(1)
        # Filter out JS keywords and very short/numeric names
        if len(key) < 2 or key in {
            'if', 'in', 'of', 'do', 'for', 'let', 'var', 'new', 'try',
            'return', 'const', 'class', 'function', 'this', 'true', 'false',
            'null', 'undefined', 'else', 'case', 'break', 'continue',
        }:
            continue
        keys.append(key)
    return keys


def _analyze_with_esprima(content: str, source_url: str) -> list[dict]:
    """Parse JS content with esprima-python and walk the AST.

    Args:
        content (str): JS file content.
        source_url (str): URL of the JS file (for provenance).

    Returns:
        list[dict]: Parameter findings from AST analysis.
    """
    try:
        import esprima  # type: ignore
    except ImportError:
        return []

    findings = []

    try:
        tree = esprima.parseScript(content, tolerant=True, jsx=False)
    except Exception:
        try:
            tree = esprima.parseModule(content, tolerant=True, jsx=False)
        except Exception as exc:
            logger.debug('[CPDE:ast] esprima parse failed for %s: %s', source_url, exc)
            return []

    def _walk(node):
        """Recursively walk AST nodes looking for relevant call expressions."""
        if not hasattr(node, 'type'):
            return

        if node.type == 'CallExpression':
            callee = node.callee
            callee_name = ''

            # Detect fetch('url', { ... })
            if hasattr(callee, 'name'):
                callee_name = callee.name
            elif hasattr(callee, 'property') and hasattr(callee.property, 'name'):
                callee_name = callee.property.name

            if callee_name in ('fetch', 'axios', 'get', 'post', 'put', 'patch', 'delete', 'request'):
                for arg in (node.arguments or []):
                    if hasattr(arg, 'type') and arg.type == 'ObjectExpression':
                        _extract_from_object_expression(arg, source_url, findings)

        # Recurse into children
        for attr in vars(node).values():
            if hasattr(attr, 'type'):
                _walk(attr)
            elif isinstance(attr, list):
                for item in attr:
                    if hasattr(item, 'type'):
                        _walk(item)

    def _extract_from_object_expression(obj_node, src_url, out):
        """Extract keys from an ObjectExpression AST node."""
        for prop in (obj_node.properties or []):
            if not hasattr(prop, 'key'):
                continue
            key = prop.key
            key_name = getattr(key, 'name', None) or getattr(key, 'value', None)
            if not key_name or not isinstance(key_name, str):
                continue
            if len(key_name) < 2:
                continue

            # Infer data type from value node
            value_node = getattr(prop, 'value', None)
            data_type = None
            if value_node:
                vtype = getattr(value_node, 'type', '')
                if vtype == 'Literal':
                    val = getattr(value_node, 'value', None)
                    if isinstance(val, bool):
                        data_type = 'boolean'
                    elif isinstance(val, (int, float)):
                        data_type = 'number'
                    elif isinstance(val, str):
                        data_type = 'string'
                elif vtype == 'ArrayExpression':
                    data_type = 'array'
                elif vtype == 'ObjectExpression':
                    data_type = 'object'

            out.append({
                'name': key_name,
                'location': 'json_body',
                'data_type': data_type,
                'source_url': src_url,
                'confidence': 70,
                'is_auth_related': _is_auth_related(key_name),
                'context': f'AST:ObjectExpression@{src_url}',
            })

    try:
        _walk(tree)
    except Exception as exc:
        logger.warning('[CPDE:ast] Error walking AST for %s: %s', source_url, exc)

    return findings


def _analyze_with_regex(content: str, source_url: str) -> list[dict]:
    """Extract parameter evidence using regex patterns (minified code fallback).

    Args:
        content (str): JS file content.
        source_url (str): URL of the JS file (for provenance).

    Returns:
        list[dict]: Parameter findings from regex analysis.
    """
    findings = []

    def _emit(name, location, data_type=None, confidence=55):
        if not name or len(name) < 2:
            return
        findings.append({
            'name': name,
            'location': location,
            'data_type': data_type,
            'source_url': source_url,
            'confidence': confidence,
            'is_auth_related': _is_auth_related(name),
            'context': f'regex:{location}@{source_url}',
        })

    # JSON.stringify({ key: val })
    for m in _RE_JSON_STRINGIFY_KEYS.finditer(content):
        for key in _extract_keys_from_obj_literal(m.group(1)):
            _emit(key, 'json_body', confidence=60)

    # URLSearchParams object literal
    for m in _RE_URLSEARCHPARAMS_OBJ.finditer(content):
        for key in _extract_keys_from_obj_literal(m.group(1)):
            _emit(key, 'query_string', confidence=65)

    # params.append('key', ...) / searchParams.append('key', ...)
    for m in _RE_URLSEARCHPARAMS_APPEND.finditer(content):
        _emit(m.group(1), 'query_string', confidence=70)

    # formData.append('key', ...)
    for m in _RE_FORMDATA_APPEND.finditer(content):
        _emit(m.group(1), 'form_data', confidence=70)

    # axios data/params objects
    for m in _RE_AXIOS_OBJ_KEYS.finditer(content):
        for key in _extract_keys_from_obj_literal(m.group(1)):
            _emit(key, 'json_body', confidence=60)

    return findings


def extract_from_js_files(js_files: list[dict]) -> list[dict]:
    """Analyse a list of downloaded JS files and return all parameter findings.

    Tries esprima AST parsing first; falls back to regex for files that fail
    AST parsing (common for heavily minified bundles).

    Args:
        js_files (list[dict]): Output of js_collector.download_js_files().

    Returns:
        list[dict]: All parameter findings across all files.
    """
    all_findings: list[dict] = []

    for js_file in js_files:
        url = js_file.get('url', '')
        content = js_file.get('content', '')
        if not content:
            continue

        ast_results = _analyze_with_esprima(content, url)
        if ast_results:
            logger.info(
                '[CPDE:ast] %s — esprima found %d params', url, len(ast_results)
            )
            all_findings.extend(ast_results)
        else:
            # esprima failed or found nothing — try regex fallback
            regex_results = _analyze_with_regex(content, url)
            logger.info(
                '[CPDE:ast] %s — regex fallback found %d params', url, len(regex_results)
            )
            all_findings.extend(regex_results)

    logger.info('[CPDE:ast] Total AST findings across all JS files: %d', len(all_findings))
    return all_findings
