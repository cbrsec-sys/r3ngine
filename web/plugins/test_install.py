import os
import sys
import django
sys.path.append('/usr/src/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from plugins.utils import AtomicInstaller
import zipfile

try:
    print("Testing install...")
    AtomicInstaller.install('/usr/src/app/plugins_data/credential_intelligence.r3n')
except Exception as e:
    print(f"Exception: {e}")
