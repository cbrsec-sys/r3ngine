"""Reconcile InstalledExternalTool rows against binaries on this host.

Only probes a curated allowlist derived from fixture/catalog names — never
auto-registers arbitrary PATH binaries.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from typing import Any, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)

# Known PATH locations used by the web image.
_EXTRA_PATH_DIRS = (
    '/usr/local/bin',
    '/usr/bin',
    '/go/bin',
    '/root/go/bin',
    '/home/rengine/go/bin',
)

# name (lowercase) -> candidate binary names on disk
_BINARY_ALIASES: dict[str, list[str]] = {
    'nuclei': ['nuclei'],
    'httpx': ['httpx'],
    'naabu': ['naabu'],
    'nmap': ['nmap'],
    'subfinder': ['subfinder'],
    'ffuf': ['ffuf'],
    'katana': ['katana'],
    'gau': ['gau'],
    'hakrawler': ['hakrawler'],
    'gospider': ['gospider'],
    'amass': ['amass'],
    'dalfox': ['dalfox'],
    'wafw00f': ['wafw00f'],
    'tlsx': ['tlsx'],
    'dnsx': ['dnsx'],
    'chaos': ['chaos'],
    'kiterunner': ['kr', 'kiterunner'],
    'arjun': ['arjun'],
    'linkfinder': ['linkfinder'],
    'paramspider': ['paramspider'],
    'semgrep': ['semgrep'],
    'gitleaks': ['gitleaks'],
    'trufflehog': ['trufflehog'],
    'wpscan': ['wpscan'],
    'sqlmap': ['sqlmap'],
    'testssl.sh': ['testssl.sh', 'testssl'],
    'dirsearch': ['dirsearch'],
    'baddns': ['baddns'],
    'gosearch': ['gosearch'],
    'betterleaks': ['betterleaks'],
    'username-anarchy': ['username-anarchy'],
    'vulnx': ['vulnx'],
    'gowitness': ['gowitness'],
    'crlfuzz': ['crlfuzz'],
    'whatweb': ['whatweb'],
}


def _candidate_binaries(tool_name: str) -> list[str]:
    key = (tool_name or '').strip().lower()
    if key in _BINARY_ALIASES:
        return list(_BINARY_ALIASES[key])
    # Nuclei fixture uses title case "Nuclei"
    if key == 'nuclei':
        return ['nuclei']
    return [key.replace(' ', '-'), key]


def resolve_binary_path(tool_name: str, github_clone_path: Optional[str] = None) -> Optional[str]:
    """Return absolute path to the primary binary if present, else None."""
    search_path = os.pathsep.join(
        [*(d for d in _EXTRA_PATH_DIRS if os.path.isdir(d)), os.environ.get('PATH', '')]
    )
    for candidate in _candidate_binaries(tool_name):
        found = shutil.which(candidate, path=search_path)
        if found and os.path.isfile(found) and os.access(found, os.X_OK):
            return found
        for d in _EXTRA_PATH_DIRS:
            p = os.path.join(d, candidate)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    if github_clone_path and os.path.isdir(github_clone_path):
        # Cloned repos without a PATH binary still count as present for inventory.
        return github_clone_path
    return None


def _run_argv(argv: list[str], *, timeout: float = 8.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env={**os.environ, 'PATH': os.pathsep.join([*_EXTRA_PATH_DIRS, os.environ.get('PATH', '')])},
        )
        return proc.returncode, proc.stdout or '', proc.stderr or ''
    except FileNotFoundError:
        return 127, '', 'not found'
    except subprocess.TimeoutExpired:
        return 124, '', 'timeout'
    except Exception as exc:
        return 1, '', str(exc)[:200]


def probe_version(
    *,
    resolved_path: str,
    version_lookup_command: Optional[str],
    version_match_regex: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Return (version_string, error). Uses argv-only execution."""
    argv: list[str]
    if version_lookup_command:
        # Split conservatively; never use shell=True.
        parts = version_lookup_command.strip().split()
        if not parts:
            argv = [resolved_path, '--version']
        else:
            # Prefer resolved path for the first token if it looks like the binary name.
            first = parts[0]
            base = os.path.basename(resolved_path.rstrip('/'))
            if os.path.isfile(resolved_path) and (
                first == base or first.endswith('/' + base) or os.path.basename(first) == base
            ):
                argv = [resolved_path, *parts[1:]]
            elif os.path.isabs(first) and os.path.isfile(first):
                argv = parts
            else:
                argv = [resolved_path if os.path.isfile(resolved_path) else first, *parts[1:]]
    else:
        if not os.path.isfile(resolved_path):
            return None, None
        argv = [resolved_path, '--version']

    code, out, err = _run_argv(argv)
    text = (out + '\n' + err).strip()
    if not text:
        return None, f'empty version output (exit {code})' if code else None
    pattern = version_match_regex or r'[vV]?\d+\.\d+(?:\.\d+)?'
    try:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    except re.error:
        m = re.search(r'[vV]?\d+\.\d+(?:\.\d+)?', text)
    if m:
        return m.group(0), None
    # Fall back to first non-empty line truncated
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), None)
    return (line[:180] if line else None), None


def sync_installed_tools(*, probe_versions: bool = True) -> dict[str, Any]:
    """Upsert presence/version on all InstalledExternalTool rows.

    Does not create tools from arbitrary PATH entries — only updates existing
    catalog rows (fixture / migrations / operator-added).
    """
    from scanEngine.models import InstalledExternalTool

    now = timezone.now()
    present = 0
    missing = 0
    errors = 0
    for tool in InstalledExternalTool.objects.all().order_by('id'):
        try:
            path = resolve_binary_path(tool.name, tool.github_clone_path)
            if not path:
                tool.is_present = False
                tool.resolved_path = None
                tool.detected_version = None
                tool.last_sync_error = 'binary not found on host'
                tool.save(update_fields=[
                    'is_present', 'resolved_path', 'detected_version', 'last_sync_error',
                ])
                missing += 1
                continue

            version = None
            sync_err = None
            if probe_versions and os.path.isfile(path):
                version, sync_err = probe_version(
                    resolved_path=path,
                    version_lookup_command=tool.version_lookup_command,
                    version_match_regex=tool.version_match_regex,
                )
            tool.is_present = True
            tool.resolved_path = path
            tool.detected_version = version
            tool.last_seen_at = now
            tool.last_sync_error = sync_err
            tool.save(update_fields=[
                'is_present', 'resolved_path', 'detected_version',
                'last_seen_at', 'last_sync_error',
            ])
            present += 1
        except Exception as exc:
            logger.exception('sync failed for tool %s', tool.name)
            tool.last_sync_error = str(exc)[:500]
            tool.save(update_fields=['last_sync_error'])
            errors += 1

    return {
        'present': present,
        'missing': missing,
        'errors': errors,
        'total': present + missing,
        'synced_at': now.isoformat(),
    }


def ensure_catalog_from_fixture_names(extra_names: Optional[list[dict]] = None) -> int:
    """Create missing default rows for known platform tools not yet in DB.

    `extra_names` is a list of dicts with at least `name` and `install_command`.
    Used to backfill migration-only tools without relying on loaddata alone.
    """
    from scanEngine.models import InstalledExternalTool

    created = 0
    for entry in extra_names or []:
        name = entry.get('name')
        if not name:
            continue
        _, was_created = InstalledExternalTool.objects.get_or_create(
            name=name,
            defaults={
                'description': entry.get('description') or name,
                'github_url': entry.get('github_url') or '',
                'install_command': entry.get('install_command') or f'which {name}',
                'version_lookup_command': entry.get('version_lookup_command'),
                'update_command': entry.get('update_command'),
                'is_default': entry.get('is_default', True),
                'is_subdomain_gathering': entry.get('is_subdomain_gathering', False),
                'is_github_cloned': entry.get('is_github_cloned', False),
                'github_clone_path': entry.get('github_clone_path'),
                'subdomain_gathering_command': entry.get('subdomain_gathering_command'),
            },
        )
        if was_created:
            created += 1
    return created
