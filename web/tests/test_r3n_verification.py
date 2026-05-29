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
