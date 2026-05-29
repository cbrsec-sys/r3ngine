# .r3n Plugin Packaging & Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `.zip` plugin distribution with `.r3n` — a self-verifying package that embeds an SHA-256 content hash and optional Ed25519 signature, with trust-level badges surfaced on plugin cards and warnings in the install overlay.

**Architecture:** A `.r3n` file is an outer ZIP containing `plugin.zip` (all plugin content, unchanged structure) and `r3n_manifest.json` (hash + optional signature + author metadata). The build script computes SHA-256 of `plugin.zip`, optionally signs it with a developer Ed25519 key, and bundles both into the outer `.r3n`. The installer reads the manifest first, verifies the hash (always) and signature (if present), then extracts `plugin.zip` through the existing pipeline unchanged.

**Tech Stack:** Python `cryptography==46.0.5` (already in `web/requirements.txt`), Python `zipfile`/`hashlib`/`base64` stdlib, Django model migration, React + MUI Chip.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `r3ngine-plugins/build_plugins.py` | New .r3n build flow, signing |
| Create | `r3ngine-plugins/keygen.py` | One-time Ed25519 keypair generator |
| Modify | `r3ngine-plugins/*/manifest.yaml` (×3) | Add `author` field |
| Modify | `r3ngine-plugins/plugins.yaml` | Add `author` + `signed` per plugin |
| Create | `web/plugins/plugin_keys.py` | Hardcoded trusted public keys |
| Modify | `web/plugins/utils.py` | `verify_r3n()`, updated `install()` |
| Modify | `web/plugins/models.py` | `author` + `trust_level` fields |
| Create | `web/plugins/migrations/0003_plugin_author_trust_level.py` | Migration |
| Modify | `web/plugins/serializers.py` | Expose new fields |
| Create | `web/tests/test_r3n_verification.py` | Tests for `verify_r3n` |
| Modify | `frontend/src/features/plugins/api/pluginsApi.ts` | Updated types |
| Modify | `frontend/src/features/plugins/components/PluginCard.tsx` | Author + trust badge |
| Modify | `frontend/src/features/plugins/components/InstallProgressOverlay.tsx` | Warning banner + verify step |

---

## Task 1: Add `author` to manifest.yaml files and plugins.yaml

**Files:**
- Modify: `r3ngine-plugins/active_directory/manifest.yaml`
- Modify: `r3ngine-plugins/exploit_readiness_layer/manifest.yaml`
- Modify: `r3ngine-plugins/active_exploitation/manifest.yaml`
- Modify: `r3ngine-plugins/plugins.yaml`

- [ ] **Step 1: Add `author` to `active_directory/manifest.yaml`**

Add after `version: "1.0.0"`:
```yaml
author: "r3ngine Team"
```

Full updated header of `r3ngine-plugins/active_directory/manifest.yaml`:
```yaml
name: "Active Directory"
description: "Enterprise AD assessment, identity intelligence, and exposure management plugin for contracted penetration testing and consulting engagements."
version: "1.0.0"
author: "r3ngine Team"
```

- [ ] **Step 2: Add `author` to `exploit_readiness_layer/manifest.yaml`**

Add after `version: "1.0.0"`:
```yaml
author: "r3ngine Team"
```

- [ ] **Step 3: Add `author` to `active_exploitation/manifest.yaml`**

First read the file to confirm its version line, then add after `version`:
```yaml
author: "r3ngine Team"
```

- [ ] **Step 4: Update `plugins.yaml` — add `author` and `signed` to each entry**

Full replacement of `r3ngine-plugins/plugins.yaml`:
```yaml
marketplace:
  - slug: active_directory
    name: "Active Directory"
    version: "1.0.0"
    author: "r3ngine Team"
    description: "Enterprise AD assessment, identity intelligence, and exposure management plugin for contracted penetration testing and consulting engagements."
    category: "Intelligence"
    signed: true

  - slug: exploit_readiness_layer
    name: "Exploit Readiness Layer"
    version: "1.0.0"
    author: "r3ngine Team"
    description: "Validated vulnerability confirmation using sandboxed tools. Ported to Temporal workflow."
    category: "Exploitation"
    signed: true

  - slug: active_exploitation
    name: "Active Exploitation"
    version: "1.0.0"
    author: "r3ngine Team"
    description: "SQLMap and deep exploitation integration running via Temporal workflows."
    category: "Exploitation"
    signed: true
```

- [ ] **Step 5: Commit**

```bash
git add r3ngine-plugins/active_directory/manifest.yaml \
        r3ngine-plugins/exploit_readiness_layer/manifest.yaml \
        r3ngine-plugins/active_exploitation/manifest.yaml \
        r3ngine-plugins/plugins.yaml
git commit -m "feat(plugins): add author field to manifests and plugins.yaml"
```

---

## Task 2: Create `plugin_keys.py` stub in `web/plugins/`

**Files:**
- Create: `web/plugins/plugin_keys.py`

This stub allows the codebase to compile and tests to run before `keygen.py` is ever run. An empty list means all plugins are treated as `signed_unknown` or `unsigned` until a real key is added.

- [ ] **Step 1: Create `web/plugins/plugin_keys.py`**

```python
# Generated by r3ngine-plugins/keygen.py — commit this file, NEVER commit signing.key.
# Run keygen.py once, move the generated plugin_keys.py here, then rebuild plugins.
TRUSTED_PUBLIC_KEYS: list[bytes] = []
```

- [ ] **Step 2: Commit**

```bash
git add web/plugins/plugin_keys.py
git commit -m "feat(plugins): add plugin_keys.py stub for trusted Ed25519 public keys"
```

---

## Task 3: Create `keygen.py` in `r3ngine-plugins/`

**Files:**
- Create: `r3ngine-plugins/keygen.py`

This is a one-time developer tool. It is NOT part of the build pipeline. Run it once to create the signing keypair.

- [ ] **Step 1: Create `r3ngine-plugins/keygen.py`**

```python
#!/usr/bin/env python3
"""One-time Ed25519 keypair generator for .r3n plugin signing.

Run once:
    python keygen.py

Then:
    1. Move the generated plugin_keys.py to web/plugins/plugin_keys.py
    2. git add web/plugins/plugin_keys.py && git commit
    3. Keep ~/.r3n/signing.key secret — never commit it.
    4. Run build_plugins.py to produce signed .r3n files.
"""

import sys
from pathlib import Path


def main():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PrivateFormat, PublicFormat, NoEncryption,
        )
    except ImportError:
        print("[!] cryptography package required: pip install cryptography")
        sys.exit(1)

    key_dir = Path.home() / '.r3n'
    key_path = key_dir / 'signing.key'

    if key_path.exists():
        print(f"[!] Key already exists at {key_path}")
        print("    Delete it manually if you want to regenerate.")
        sys.exit(1)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    key_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    key_path.write_bytes(pem)
    try:
        key_path.chmod(0o600)
    except NotImplementedError:
        pass  # Windows — permissions handled via NTFS ACLs
    print(f"[+] Private key saved to {key_path}")

    pub_raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    output_path = Path(__file__).parent / 'plugin_keys.py'
    output_path.write_text(
        "# Generated by keygen.py — commit this file, NEVER commit signing.key\n"
        "TRUSTED_PUBLIC_KEYS: list[bytes] = [\n"
        f"    {pub_raw!r},\n"
        "]\n"
    )
    print(f"[+] plugin_keys.py written to {output_path}")
    print()
    print("Next steps:")
    print(f"  1. Move plugin_keys.py  →  web/plugins/plugin_keys.py")
    print(f"  2. git add web/plugins/plugin_keys.py && git commit")
    print(f"  3. Keep {key_path} secret — never commit it")
    print(f"  4. Run build_plugins.py to produce signed .r3n files")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Commit**

```bash
git add r3ngine-plugins/keygen.py
git commit -m "feat(plugins): add keygen.py for Ed25519 signing keypair generation"
```

---

## Task 4: Write failing tests for `PluginManager.verify_r3n` (TDD)

**Files:**
- Create: `web/tests/test_r3n_verification.py`

Write all tests before implementing `verify_r3n`. Tests use in-memory construction of `.r3n` files — no disk fixtures required except for the temp file passed to `verify_r3n`.

- [ ] **Step 1: Create `web/tests/test_r3n_verification.py`**

```python
import base64
import hashlib
import io
import json
import os
import tempfile
import zipfile
from unittest.mock import patch

from django.test import TestCase


def _make_inner_zip(files=None):
    """Build plugin.zip bytes in memory."""
    if files is None:
        files = {'manifest.yaml': 'name: Test Plugin\nversion: 1.0.0\nauthor: Test Author\n'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def _make_r3n(inner_zip_bytes, private_key=None, tamper_hash=False, bad_sig=False):
    """Build .r3n bytes in memory."""
    content_hash = hashlib.sha256(inner_zip_bytes).hexdigest()
    meta = {
        'format_version': '1',
        'plugin_slug': 'test_plugin',
        'plugin_version': '1.0.0',
        'author': 'Test Author',
        'build_time': '2026-05-29T10:00:00Z',
        'content_hash': 'TAMPERED000abc' if tamper_hash else content_hash,
    }
    if private_key is not None:
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        sig = private_key.sign(content_hash.encode())
        if bad_sig:
            sig = b'\x00' * 64
        pub_raw = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        meta['signature'] = base64.b64encode(sig).decode()
        meta['public_key'] = base64.b64encode(pub_raw).decode()
        meta['signed_by'] = 'test'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('plugin.zip', inner_zip_bytes)
        z.writestr('r3n_manifest.json', json.dumps(meta))
    return buf.getvalue()


class TestVerifyR3n(TestCase):

    def setUp(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        self.inner_zip = _make_inner_zip()
        self.private_key = Ed25519PrivateKey.generate()
        self.pub_raw = self.private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def _write_r3n(self, r3n_bytes):
        f = tempfile.NamedTemporaryFile(suffix='.r3n', delete=False)
        f.write(r3n_bytes)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_unsigned_returns_unsigned(self):
        from plugins.utils import PluginManager
        r3n_path = self._write_r3n(_make_r3n(self.inner_zip))
        plugin_zip_bytes, meta, result = PluginManager.verify_r3n(r3n_path)
        self.assertEqual(result, 'unsigned')
        self.assertEqual(meta['author'], 'Test Author')
        self.assertEqual(plugin_zip_bytes, self.inner_zip)

    def test_signed_with_trusted_key_returns_official(self):
        from plugins.utils import PluginManager
        r3n_path = self._write_r3n(_make_r3n(self.inner_zip, private_key=self.private_key))
        with patch('plugins.utils.TRUSTED_PUBLIC_KEYS', [self.pub_raw]):
            _, _, result = PluginManager.verify_r3n(r3n_path)
        self.assertEqual(result, 'official')

    def test_signed_with_untrusted_key_returns_signed_unknown(self):
        from plugins.utils import PluginManager
        r3n_path = self._write_r3n(_make_r3n(self.inner_zip, private_key=self.private_key))
        with patch('plugins.utils.TRUSTED_PUBLIC_KEYS', []):
            _, _, result = PluginManager.verify_r3n(r3n_path)
        self.assertEqual(result, 'signed_unknown')

    def test_tampered_hash_raises_value_error(self):
        from plugins.utils import PluginManager
        r3n_path = self._write_r3n(_make_r3n(self.inner_zip, tamper_hash=True))
        with self.assertRaises(ValueError) as ctx:
            PluginManager.verify_r3n(r3n_path)
        self.assertIn('hash mismatch', str(ctx.exception).lower())

    def test_bad_signature_raises_value_error(self):
        from plugins.utils import PluginManager
        r3n_path = self._write_r3n(_make_r3n(self.inner_zip, private_key=self.private_key, bad_sig=True))
        with self.assertRaises(ValueError):
            PluginManager.verify_r3n(r3n_path)

    def test_missing_manifest_raises_value_error(self):
        from plugins.utils import PluginManager
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('plugin.zip', self.inner_zip)
        r3n_path = self._write_r3n(buf.getvalue())
        with self.assertRaises(ValueError) as ctx:
            PluginManager.verify_r3n(r3n_path)
        self.assertIn('r3n_manifest.json', str(ctx.exception))

    def test_missing_plugin_zip_raises_value_error(self):
        from plugins.utils import PluginManager
        meta = {'format_version': '1', 'content_hash': 'abc'}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('r3n_manifest.json', json.dumps(meta))
        r3n_path = self._write_r3n(buf.getvalue())
        with self.assertRaises(ValueError) as ctx:
            PluginManager.verify_r3n(r3n_path)
        self.assertIn('plugin.zip', str(ctx.exception))
```

- [ ] **Step 2: Run tests — expect failures (method not yet defined)**

Run inside the container:
```bash
docker compose exec web python manage.py test tests.test_r3n_verification -v 2
```

Expected: `AttributeError: type object 'PluginManager' has no attribute 'verify_r3n'`

---

## Task 5: Implement `PluginManager.verify_r3n()` in `web/plugins/utils.py`

**Files:**
- Modify: `web/plugins/utils.py`

- [ ] **Step 1: Add `TRUSTED_PUBLIC_KEYS` import at the top of `web/plugins/utils.py`**

After the existing imports block (after `import logging`), add:

```python
try:
    from .plugin_keys import TRUSTED_PUBLIC_KEYS
except ImportError:
    TRUSTED_PUBLIC_KEYS: list[bytes] = []
```

- [ ] **Step 2: Add `verify_r3n` classmethod to `PluginManager`**

Add after the `delete_plugin_files` classmethod (before the `class AtomicInstaller` line):

```python
    @classmethod
    def verify_r3n(cls, r3n_path):
        """Open a .r3n file, verify content hash and optional Ed25519 signature.

        Returns (plugin_zip_bytes, meta_dict, verification_result) where
        verification_result is one of: 'official' | 'signed_unknown' | 'unsigned'.
        Raises ValueError on hash mismatch or invalid signature.
        """
        import hashlib
        import base64
        import json
        import io as _io
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature

        with open(r3n_path, 'rb') as f:
            r3n_bytes = f.read()

        with zipfile.ZipFile(_io.BytesIO(r3n_bytes), 'r') as r3n_zip:
            names = r3n_zip.namelist()
            if 'r3n_manifest.json' not in names:
                raise ValueError("Not a valid .r3n file: missing r3n_manifest.json")
            if 'plugin.zip' not in names:
                raise ValueError("Not a valid .r3n file: missing plugin.zip")
            meta = json.loads(r3n_zip.read('r3n_manifest.json'))
            plugin_zip_bytes = r3n_zip.read('plugin.zip')

        actual_hash = hashlib.sha256(plugin_zip_bytes).hexdigest()
        if actual_hash != meta.get('content_hash'):
            raise ValueError("Content hash mismatch — archive may be tampered")

        raw_sig = meta.get('signature')
        raw_pub = meta.get('public_key')

        if not raw_sig or not raw_pub:
            return plugin_zip_bytes, meta, 'unsigned'

        try:
            pub_key_bytes = base64.b64decode(raw_pub)
            sig_bytes = base64.b64decode(raw_sig)
            pub_key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)
            pub_key.verify(sig_bytes, actual_hash.encode())
        except InvalidSignature:
            raise ValueError("Invalid signature — archive may be tampered")
        except Exception as e:
            raise ValueError(f"Signature verification error: {e}")

        if pub_key_bytes in TRUSTED_PUBLIC_KEYS:
            return plugin_zip_bytes, meta, 'official'
        return plugin_zip_bytes, meta, 'signed_unknown'
```

- [ ] **Step 3: Run tests — expect all 7 to pass**

```bash
docker compose exec web python manage.py test tests.test_r3n_verification -v 2
```

Expected output: `Ran 7 tests in ...s  OK`

- [ ] **Step 4: Commit**

```bash
git add web/plugins/utils.py web/tests/test_r3n_verification.py
git commit -m "feat(plugins): implement PluginManager.verify_r3n with Ed25519 + SHA-256 verification"
```

---

## Task 6: Add `author` and `trust_level` to the `Plugin` model

**Files:**
- Modify: `web/plugins/models.py`
- Create: `web/plugins/migrations/0003_plugin_author_trust_level.py`

- [ ] **Step 1: Add fields to `web/plugins/models.py`**

Add the two new fields after the `icon_path` field:

```python
    author = models.CharField(max_length=255, blank=True, default='')
    trust_level = models.CharField(max_length=20, default='unsigned')
```

The full `Plugin` model fields list after the change:
```python
class Plugin(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    version = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_enabled = models.BooleanField(default=True)
    anchor_step = models.CharField(max_length=255, help_text="Core engine task name this plugin attaches to")
    RUNTIME_POSITION_CHOICES = [
        ('BEFORE', 'Before'),
        ('AFTER', 'After'),
    ]
    runtime_position = models.CharField(max_length=10, choices=RUNTIME_POSITION_CHOICES, default='AFTER')
    order_weight = models.IntegerField(default=0, help_text="Used for relative sorting within the same anchor/position")
    manifest = models.JSONField(default=dict)
    tools_config = models.JSONField(default=dict, help_text="Metadata from tools.yaml")
    installed_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    icon_path = models.CharField(max_length=255, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, default='')
    trust_level = models.CharField(max_length=20, default='unsigned')
```

- [ ] **Step 2: Create the migration file**

Create `web/plugins/migrations/0003_plugin_author_trust_level.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0002_plugin_tools_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='plugin',
            name='author',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='plugin',
            name='trust_level',
            field=models.CharField(default='unsigned', max_length=20),
        ),
    ]
```

- [ ] **Step 3: Apply the migration**

```bash
docker compose exec web python manage.py migrate plugins
```

Expected: `Applying plugins.0003_plugin_author_trust_level... OK`

- [ ] **Step 4: Commit**

```bash
git add web/plugins/models.py web/plugins/migrations/0003_plugin_author_trust_level.py
git commit -m "feat(plugins): add author and trust_level fields to Plugin model"
```

---

## Task 7: Update `PluginSerializer` to expose new fields

**Files:**
- Modify: `web/plugins/serializers.py`

- [ ] **Step 1: Add `author` and `trust_level` to the `fields` list and `read_only_fields`**

Replace the entire `serializers.py`:

```python
from rest_framework import serializers
from .models import Plugin


class PluginSerializer(serializers.ModelSerializer):
    needs_restart = serializers.SerializerMethodField()

    class Meta:
        model = Plugin
        fields = [
            'id', 'name', 'slug', 'version', 'description',
            'is_enabled', 'anchor_step', 'runtime_position',
            'order_weight', 'manifest', 'installed_at',
            'updated_at', 'icon_path', 'needs_restart',
            'author', 'trust_level',
        ]
        read_only_fields = [
            'id', 'slug', 'installed_at', 'updated_at',
            'manifest', 'author', 'trust_level',
        ]

    def get_needs_restart(self, obj):
        from django.core.cache import cache
        return cache.get(f"plugin_{obj.slug}_needs_restart", True)
```

- [ ] **Step 2: Run existing plugin tests to ensure nothing is broken**

```bash
docker compose exec web python manage.py test tests.test_r3n_verification -v 2
```

Expected: `Ran 7 tests in ...s  OK`

- [ ] **Step 3: Commit**

```bash
git add web/plugins/serializers.py
git commit -m "feat(plugins): expose author and trust_level in PluginSerializer"
```

---

## Task 8: Update `AtomicInstaller` to use `verify_r3n`

**Files:**
- Modify: `web/plugins/utils.py`

This task makes targeted edits to `AtomicInstaller` in `utils.py`. Do NOT rewrite the entire file — make the four specific changes described below.

- [ ] **Step 1: Add `'verify'` step to `AtomicInstaller.STEPS`**

Replace:
```python
    STEPS = [
        ('upload',      'Saving plugin archive'),
        ('extract',     'Extracting archive'),
        ('validate',    'Validating manifest'),
```
With:
```python
    STEPS = [
        ('upload',      'Saving plugin archive'),
        ('extract',     'Extracting archive'),
        ('verify',      'Verifying integrity'),
        ('validate',    'Validating manifest'),
```

- [ ] **Step 2: Add variables and `.r3n` branch at the top of `AtomicInstaller.install`**

Replace:
```python
        PluginManager.ensure_dirs()
        temp_dir = None
        backup_db_file = None
        backup_fs_dir = None
        plugin_slug = None

        try:
            cls._emit(install_id, 'extract', 'in_progress')
            temp_dir = PluginManager.extract_plugin(zip_path)
            cls._emit(install_id, 'extract', 'completed')
```
With:
```python
        PluginManager.ensure_dirs()
        temp_dir = None
        backup_db_file = None
        backup_fs_dir = None
        plugin_slug = None
        inner_zip_path = None
        verification_result = 'legacy'
        r3n_meta: dict = {}

        try:
            cls._emit(install_id, 'extract', 'in_progress')

            if zip_path.endswith('.r3n'):
                cls._emit(install_id, 'verify', 'in_progress')
                plugin_zip_bytes, r3n_meta, verification_result = PluginManager.verify_r3n(zip_path)
                inner_zip_path = zip_path.replace('.r3n', '_inner.zip')
                with open(inner_zip_path, 'wb') as _f:
                    _f.write(plugin_zip_bytes)
                actual_zip = inner_zip_path
                _trust_msg = {
                    'official':       'Verified — official r3ngine plugin',
                    'signed_unknown': 'Signed by unverified publisher',
                    'unsigned':       'Unsigned plugin',
                }.get(verification_result, '')
                cls._emit(install_id, 'verify', 'completed', _trust_msg)
            else:
                actual_zip = zip_path
                verification_result = 'legacy'
                cls._emit(install_id, 'verify', 'completed', 'Legacy .zip — unverified')

            temp_dir = PluginManager.extract_plugin(actual_zip)
            cls._emit(install_id, 'extract', 'completed')
```

- [ ] **Step 3: Populate `author` and `trust_level` in `Plugin.objects.update_or_create`**

Find the `Plugin.objects.update_or_create` call and add the two new fields to `defaults`:

Replace:
```python
                plugin, created = Plugin.objects.update_or_create(
                    slug=plugin_slug,
                    defaults={
                        'name': plugin_name,
                        'version': manifest['version'],
                        'description': manifest.get('description', ''),
                        'manifest': manifest,
                        'anchor_step': anchor,
                        'runtime_position': position,
                    }
                )
```
With:
```python
                plugin, created = Plugin.objects.update_or_create(
                    slug=plugin_slug,
                    defaults={
                        'name': plugin_name,
                        'version': manifest['version'],
                        'description': manifest.get('description', ''),
                        'manifest': manifest,
                        'anchor_step': anchor,
                        'runtime_position': position,
                        'author': r3n_meta.get('author', ''),
                        'trust_level': verification_result,
                    }
                )
```

- [ ] **Step 4: Add warning to cache and clean up `inner_zip_path`**

Find the success block just before `cls._emit(install_id, 'complete', 'completed')` and add the warning emission:

Replace:
```python
                cls._emit(install_id, 'complete', 'completed')
                if install_id:
                    data = cache.get(f'plugin:install:{install_id}') or {}
                    data['status'] = 'success'
                    cache.set(f'plugin:install:{install_id}', data, timeout=300)
```
With:
```python
                cls._emit(install_id, 'complete', 'completed')
                if install_id:
                    data = cache.get(f'plugin:install:{install_id}') or {}
                    data['status'] = 'success'
                    if verification_result in ('unsigned', 'signed_unknown', 'legacy'):
                        data['warning'] = verification_result
                    cache.set(f'plugin:install:{install_id}', data, timeout=300)
```

Also add `inner_zip_path` cleanup in the `except` block's finally-style cleanup at the bottom. Find:
```python
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
```
Replace with:
```python
            if inner_zip_path and os.path.exists(inner_zip_path):
                os.remove(inner_zip_path)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
```

- [ ] **Step 5: Run verification tests to ensure nothing broken**

```bash
docker compose exec web python manage.py test tests.test_r3n_verification -v 2
```

Expected: `Ran 7 tests in ...s  OK`

- [ ] **Step 6: Commit**

```bash
git add web/plugins/utils.py
git commit -m "feat(plugins): wire verify_r3n into AtomicInstaller — hash/sig check before extraction"
```

---

## Task 9: Update `build_plugins.py` to produce `.r3n` files

**Files:**
- Modify: `r3ngine-plugins/build_plugins.py`

Full replacement — the new script is a superset of the old one, same UI build logic, new packaging flow.

- [ ] **Step 1: Replace `r3ngine-plugins/build_plugins.py`**

```python
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone


def _load_signing_key():
    """Load Ed25519 private key from R3N_SIGNING_KEY env var or ~/.r3n/signing.key.
    Returns (private_key, raw_public_key_bytes) or (None, None) if no key found.
    """
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, load_pem_private_key,
    )

    pem_str = os.environ.get('R3N_SIGNING_KEY')
    if pem_str:
        key = load_pem_private_key(pem_str.encode(), password=None)
        return key, key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    key_path = os.path.expanduser('~/.r3n/signing.key')
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            key = load_pem_private_key(f.read(), password=None)
        return key, key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    return None, None


def build_plugin(plugin_slug):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = os.path.join(root_dir, plugin_slug)

    if not os.path.exists(plugin_dir):
        print(f"Error: Plugin directory '{plugin_slug}' not found.")
        return False

    print(f"--- Building plugin: {plugin_slug} ---")

    # Read manifest for version/author metadata
    manifest_path = os.path.join(plugin_dir, 'manifest.yaml')
    if not os.path.exists(manifest_path):
        print(f"[!] manifest.yaml not found — skipping {plugin_slug}")
        return False

    import yaml
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
    plugin_version = manifest.get('version', '0.0.0')
    plugin_author = manifest.get('author', 'Unknown')

    # 1. Build UI if present
    ui_dir = os.path.join(plugin_dir, 'ui')
    if os.path.exists(os.path.join(ui_dir, 'package.json')):
        print("[*] Building UI...")
        try:
            use_shell = sys.platform == 'win32'
            if not os.path.exists(os.path.join(ui_dir, 'node_modules')):
                print("[*] Running npm install...")
                subprocess.run(['npm', 'install'], cwd=ui_dir, check=True, shell=use_shell)
            print("[*] Running npm run build...")
            subprocess.run(['npm', 'run', 'build'], cwd=ui_dir, check=True, shell=use_shell)
        except subprocess.CalledProcessError as e:
            print(f"[!] UI build failed: {e}")
            return False

    dist_dir = os.path.join(root_dir, 'dist')
    os.makedirs(dist_dir, exist_ok=True)

    # 2. Package plugin content into inner plugin.zip
    inner_zip_path = os.path.join(dist_dir, f"{plugin_slug}_content.zip")
    print("[*] Packaging plugin content...")
    with zipfile.ZipFile(inner_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(manifest_path, 'manifest.yaml')

        backend_dir = os.path.join(plugin_dir, 'backend')
        if os.path.exists(backend_dir):
            for root, dirs, files in os.walk(backend_dir):
                for file in files:
                    if '__pycache__' in root:
                        continue
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, plugin_dir)
                    zipf.write(abs_path, rel_path)

        ui_dist_dir = os.path.join(ui_dir, 'dist')
        if os.path.exists(ui_dist_dir):
            for root, dirs, files in os.walk(ui_dist_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.join('ui', os.path.relpath(abs_path, ui_dist_dir))
                    zipf.write(abs_path, rel_path)

    # 3. Compute SHA-256 of inner zip
    with open(inner_zip_path, 'rb') as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"[*] Content hash: {content_hash[:16]}...")

    # 4. Build r3n_manifest.json, sign if key available
    priv_key, pub_key_bytes = _load_signing_key()
    r3n_meta = {
        'format_version': '1',
        'plugin_slug': plugin_slug,
        'plugin_version': plugin_version,
        'author': plugin_author,
        'build_time': datetime.now(timezone.utc).isoformat(),
        'content_hash': content_hash,
    }

    if priv_key is not None:
        sig_bytes = priv_key.sign(content_hash.encode())
        r3n_meta['signature'] = base64.b64encode(sig_bytes).decode()
        r3n_meta['public_key'] = base64.b64encode(pub_key_bytes).decode()
        r3n_meta['signed_by'] = 'r3ngine-official'
        print("[+] Signed with Ed25519")
    else:
        print("[!] No signing key found — building unsigned .r3n (install will show warning)")

    # 5. Create outer .r3n (plugin.zip + r3n_manifest.json)
    r3n_path = os.path.join(dist_dir, f"{plugin_slug}.r3n")
    print(f"[*] Creating {r3n_path}...")
    with zipfile.ZipFile(r3n_path, 'w', zipfile.ZIP_DEFLATED) as r3nf:
        r3nf.write(inner_zip_path, 'plugin.zip')
        r3nf.writestr('r3n_manifest.json', json.dumps(r3n_meta, indent=2))

    # 6. Remove intermediate inner zip
    os.remove(inner_zip_path)

    print(f"[+] Successfully built {r3n_path}")
    return True


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    plugins = sorted(
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d))
        and os.path.exists(os.path.join(root_dir, d, 'manifest.yaml'))
        and d != 'depreciated'
    )

    if not plugins:
        print("No plugins found to build.")
    else:
        for p in plugins:
            build_plugin(p)
```

- [ ] **Step 2: Run a test build (unsigned — no key required)**

```bash
cd r3ngine-plugins && python build_plugins.py
```

Expected output per plugin:
```
--- Building plugin: active_directory ---
[*] Packaging plugin content...
[*] Content hash: <16 hex chars>...
[!] No signing key found — building unsigned .r3n (install will show warning)
[*] Creating dist/active_directory.r3n...
[+] Successfully built dist/active_directory.r3n
```

Verify the `.r3n` contains the right structure:
```bash
python -c "
import zipfile
with zipfile.ZipFile('dist/active_directory.r3n') as z:
    print(z.namelist())
"
```
Expected: `['plugin.zip', 'r3n_manifest.json']`

- [ ] **Step 3: Commit**

```bash
git add r3ngine-plugins/build_plugins.py
git commit -m "feat(plugins): update build_plugins.py to produce signed/unsigned .r3n files"
```

---

## Task 10: Update `MarketplaceManager` download URL

**Files:**
- Modify: `web/plugins/utils.py`

- [ ] **Step 1: Update download URL from `.zip` to `.r3n`**

In `MarketplaceManager.download_plugin`, replace:
```python
        download_url = f"https://raw.githubusercontent.com/whiterabb17/r3ngine-plugins/main/{slug}/{slug}.zip"
        temp_zip_path = os.path.join(PluginManager.BASE_PLUGINS_DIR, f"download_{slug}.zip")
```
With:
```python
        download_url = f"https://raw.githubusercontent.com/whiterabb17/r3ngine-plugins/main/{slug}/{slug}.r3n"
        temp_zip_path = os.path.join(PluginManager.BASE_PLUGINS_DIR, f"download_{slug}.r3n")
```

- [ ] **Step 2: Commit**

```bash
git add web/plugins/utils.py
git commit -m "feat(plugins): update marketplace download URL from .zip to .r3n"
```

---

## Task 11: Update frontend types in `pluginsApi.ts`

**Files:**
- Modify: `frontend/src/features/plugins/api/pluginsApi.ts`

- [ ] **Step 1: Add `author` and `trust_level` to `Plugin` interface**

Replace:
```typescript
export interface Plugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  is_enabled: boolean;
  anchor_step: string;
  runtime_position: 'BEFORE' | 'AFTER';
  order_weight: number;
  manifest: any;
  needs_restart: boolean;
}
```
With:
```typescript
export interface Plugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  is_enabled: boolean;
  anchor_step: string;
  runtime_position: 'BEFORE' | 'AFTER';
  order_weight: number;
  manifest: any;
  needs_restart: boolean;
  author: string;
  trust_level: 'official' | 'signed_unknown' | 'unsigned' | 'legacy';
}
```

- [ ] **Step 2: Add `author` and `signed` to `MarketplacePlugin` interface**

Replace:
```typescript
export interface MarketplacePlugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  category?: string;
  is_installed: boolean;
}
```
With:
```typescript
export interface MarketplacePlugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  category?: string;
  is_installed: boolean;
  author: string;
  signed: boolean;
}
```

- [ ] **Step 3: Add `warning` to `InstallStatus` interface**

Replace:
```typescript
export interface InstallStatus {
  steps: InstallStep[];
  status: 'running' | 'success' | 'failed';
  plugin_name: string | null;
  error?: string;
}
```
With:
```typescript
export interface InstallStatus {
  steps: InstallStep[];
  status: 'running' | 'success' | 'failed';
  plugin_name: string | null;
  error?: string;
  warning?: 'unsigned' | 'signed_unknown' | 'legacy';
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/plugins/api/pluginsApi.ts
git commit -m "feat(plugins): add author, trust_level, signed, warning to API types"
```

---

## Task 12: Update `PluginCard` — author line + trust badge

**Files:**
- Modify: `frontend/src/features/plugins/components/PluginCard.tsx`

- [ ] **Step 1: Add `TRUST_STYLES` constant after the imports block**

Add before the `interface Props` declaration:

```typescript
const TRUST_STYLES = {
  official:       { label: 'VERIFIED',   color: '#00ffaa', bg: 'rgba(0,255,170,0.1)', border: 'rgba(0,255,170,0.2)' },
  signed_unknown: { label: 'SIGNED',     color: '#ff9800', bg: 'rgba(255,152,0,0.1)', border: 'rgba(255,152,0,0.2)' },
  unsigned:       { label: 'UNVERIFIED', color: 'rgba(255,255,255,0.3)', bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.1)' },
  legacy:         { label: 'UNVERIFIED', color: 'rgba(255,255,255,0.3)', bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.1)' },
} as const;
```

- [ ] **Step 2: Add author line below the version `<Typography>`**

Find:
```tsx
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>v{data.version}</Typography>
```
Replace with:
```tsx
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>v{data.version}</Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.6rem', display: 'block' }}>
                  by {data.author || 'Unknown'}
                </Typography>
```

- [ ] **Step 3: Add trust badge to the bottom row alongside the category chip**

Find:
```tsx
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Chip 
              label={plugin?.anchor_step || marketplacePlugin?.category || 'General'} 
              size="small" 
              variant="outlined" 
              sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', color: 'rgba(255,255,255,0.4)', fontSize: '10px' }} 
            />
```
Replace with:
```tsx
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', flexWrap: 'wrap' }}>
              <Chip 
                label={plugin?.anchor_step || marketplacePlugin?.category || 'General'} 
                size="small" 
                variant="outlined" 
                sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', color: 'rgba(255,255,255,0.4)', fontSize: '10px' }} 
              />
              {plugin && (() => {
                const s = TRUST_STYLES[plugin.trust_level] ?? TRUST_STYLES.unsigned;
                return (
                  <Chip
                    label={s.label}
                    size="small"
                    sx={{ bgcolor: s.bg, color: s.color, border: `1px solid ${s.border}`, fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}
                  />
                );
              })()}
              {isMarketplace && marketplacePlugin && (() => {
                const s = marketplacePlugin.signed ? TRUST_STYLES.official : TRUST_STYLES.unsigned;
                return (
                  <Chip
                    label={s.label}
                    size="small"
                    sx={{ bgcolor: s.bg, color: s.color, border: `1px solid ${s.border}`, fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}
                  />
                );
              })()}
            </Box>
```

Also close the new `<Box>` you opened — find the closing of the outer bottom row `<Box>` and ensure the structure is:
```tsx
          </Box>  {/* closes the inner flex Box wrapping chips */}
            {!isMarketplace && (
              ...action buttons...
            )}
          </Box>  {/* closes the outer justify-between Box */}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/plugins/components/PluginCard.tsx
git commit -m "feat(plugins): add author line and trust badge to PluginCard"
```

---

## Task 13: Update `InstallProgressOverlay` — verify step + warning banner

**Files:**
- Modify: `frontend/src/features/plugins/components/InstallProgressOverlay.tsx`

- [ ] **Step 1: Add `verify` to `ALL_STEPS`**

Replace:
```typescript
const ALL_STEPS: { key: string; label: string }[] = [
  { key: 'upload',     label: 'Saving plugin archive' },
  { key: 'extract',    label: 'Extracting archive' },
  { key: 'validate',   label: 'Validating manifest' },
```
With:
```typescript
const ALL_STEPS: { key: string; label: string }[] = [
  { key: 'upload',     label: 'Saving plugin archive' },
  { key: 'extract',    label: 'Extracting archive' },
  { key: 'verify',     label: 'Verifying integrity' },
  { key: 'validate',   label: 'Validating manifest' },
```

- [ ] **Step 2: Add `AlertTriangle` to the lucide-react imports**

Replace:
```typescript
import {
  CheckCircle,
  XCircle,
  Circle,
  Loader,
  PackageOpen,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
```
With:
```typescript
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Circle,
  Loader,
  PackageOpen,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
```

- [ ] **Step 3: Add warning banner between the step list and the error message**

Find:
```tsx
        {/* Error message */}
        {isFailed && data?.error && (
```
Insert before it:
```tsx
        {/* Warning banner — shown on success when plugin is unsigned or from unverified publisher */}
        {isSuccess && data?.warning && (
          <Box sx={{
            mt: 2, p: 1.5,
            bgcolor: 'rgba(255,152,0,0.07)',
            border: '1px solid rgba(255,152,0,0.25)',
            borderRadius: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}>
            <AlertTriangle size={14} color="#ff9800" />
            <Typography variant="caption" sx={{ color: '#ff9800', fontFamily: 'Orbitron', fontSize: '0.6rem', fontWeight: 700 }}>
              {data.warning === 'unsigned'
                ? 'UNSIGNED PLUGIN — install only if you trust the source'
                : 'UNVERIFIED PUBLISHER — this plugin is not from an official source'}
            </Typography>
          </Box>
        )}

        {/* Error message */}
        {isFailed && data?.error && (
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/plugins/components/InstallProgressOverlay.tsx
git commit -m "feat(plugins): add verify step and unsigned warning banner to InstallProgressOverlay"
```

---

## Self-Review Checklist

- [x] **Spec §1 (file format)**: Task 9 produces `plugin.zip` + `r3n_manifest.json` inside outer zip — covered
- [x] **Spec §2 (build flow)**: Task 9 (`build_plugins.py`) — covered; Task 3 (`keygen.py`) — covered
- [x] **Spec §2 (plugin_keys.py)**: Task 2 creates stub; keygen writes real file — covered
- [x] **Spec §3 (verify_r3n)**: Tasks 4+5 (TDD) — covered
- [x] **Spec §3 (verify step in STEPS)**: Task 8 step 1 — covered
- [x] **Spec §3 (author + trust_level on Plugin)**: Tasks 6+7+8 — covered
- [x] **Spec §3 (download URL)**: Task 10 — covered
- [x] **Spec §3 (legacy .zip backward-compat)**: Task 8 (else branch) — covered
- [x] **Spec §4 (warning banner)**: Task 13 — covered
- [x] **Spec §4 (author line on card)**: Task 12 step 2 — covered
- [x] **Spec §4 (trust badge on card)**: Task 12 step 3 — covered
- [x] **Spec §4 (marketplace signed badge)**: Task 12 step 3 (isMarketplace branch) — covered
- [x] **Type consistency**: `trust_level` values (`official | signed_unknown | unsigned | legacy`) used consistently across `utils.py`, `serializers.py`, `pluginsApi.ts`, `PluginCard.tsx`
- [x] **`TRUST_STYLES` keys** match all `trust_level` values from the backend including `legacy`
