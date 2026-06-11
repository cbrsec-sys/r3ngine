import os
import sys
import django
import requests

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from dashboard.models import AcunetixAPIKey

def test_acunetix(query_target_name=None):
    creds = AcunetixAPIKey.objects.first()
    if not creds:
        print("[-] No Acunetix API key found in the database.")
        return
    
    server_url = creds.server_url.rstrip('/')
    api_key = creds.api_key
    print(f"[+] Acunetix Server URL: {server_url}")
    print(f"[+] API Key configured: {'Yes (ends with ' + api_key[-4:] + ')' if api_key else 'No'}")
    
    headers = {
        'X-Auth': api_key,
        'Content-Type': 'application/json'
    }
    
    _acunetix_verify = os.environ.get('ACUNETIX_CA_BUNDLE', False)
    
    print("\n[1] Fetching targets list from Acunetix (paginated)...")
    try:
        targets = []
        c = 0
        while True:
            url = f"{server_url}/api/v1/targets"
            if c:
                url += f"?c={c}"
            targets_resp = requests.get(url, headers=headers, verify=_acunetix_verify)
            if targets_resp.status_code != 200:
                print(f"    Error fetching page cursor {c}: {targets_resp.text}")
                break
            
            targets_data = targets_resp.json()
            page_targets = targets_data.get('targets', [])
            targets.extend(page_targets)
            
            cursor = targets_data.get('pagination', {}).get('cursor')
            if not cursor or not page_targets:
                break
            c = cursor
            
        print(f"    Found {len(targets)} total targets in Acunetix.")
        
        matching_targets = []
        for t in targets:
            if not query_target_name or query_target_name.lower() in t.get('address', '').lower():
                matching_targets.append(t)
        
        if query_target_name:
            print(f"\n[2] Searching for targets matching '{query_target_name}'...")
        else:
            print("\n[2] Listing all targets (no target filter specified)...")
            
        if not matching_targets:
            print("    No matching targets found.")
            if targets:
                print("    Here are the first 10 targets in Acunetix for comparison:")
                for t in targets[:10]:
                    print(f"      - {t.get('address')} (ID: {t.get('target_id')}) (Desc: {t.get('description')})")
            return
            
        for t in matching_targets:
            t_id = t.get('target_id')
            address = t.get('address')
            description = t.get('description')
            print(f"    - Target ID: {t_id}")
            print(f"      Address: {address}")
            print(f"      Description: {description}")
            
            # Fetch scans for this target
            print(f"\n    [3] Fetching scans for Target ID {t_id}...")
            scans_resp = requests.get(f"{server_url}/api/v1/scans?q=target_id:{t_id}", headers=headers, verify=_acunetix_verify)
            print(f"        Status: {scans_resp.status_code}")
            if scans_resp.status_code == 200:
                scans_data = scans_resp.json()
                scans = scans_data.get('scans', [])
                print(f"        Found {len(scans)} scans.")
                
                for scan in scans:
                    scan_id = scan.get('scan_id')
                    session = scan.get('current_session', {})
                    status = session.get('status')
                    print(f"        * Scan ID: {scan_id}")
                    print(f"          Status: {status}")
                    
                    # Test various vulnerability endpoints
                    endpoints = [
                        {
                            "name": "Scan vulnerabilities subresource (/api/v1/scans/{scan_id}/vulnerabilities)",
                            "url": f"{server_url}/api/v1/scans/{scan_id}/vulnerabilities"
                        },
                        {
                            "name": "Global vulnerabilities queried by scan_id (/api/v1/vulnerabilities?q=scan_id:{scan_id})",
                            "url": f"{server_url}/api/v1/vulnerabilities?q=scan_id:{scan_id}"
                        },
                        {
                            "name": "Global vulnerabilities queried by target_id (/api/v1/vulnerabilities?q=target_id:{t_id})",
                            "url": f"{server_url}/api/v1/vulnerabilities?q=target_id:{t_id}"
                        }
                    ]
                    
                    for ep in endpoints:
                        print(f"\n          Testing Endpoint: {ep['name']}")
                        print(f"          URL: {ep['url']}")
                        try:
                            v_resp = requests.get(ep['url'], headers=headers, verify=_acunetix_verify)
                            print(f"          Response Code: {v_resp.status_code}")
                            if v_resp.status_code == 200:
                                v_data = v_resp.json()
                                vulns = v_data.get('vulnerabilities', [])
                                print(f"          Found {len(vulns)} vulnerabilities.")
                                if vulns:
                                    # Print first vulnerability details as sample
                                    sample = vulns[0]
                                    print(f"          Sample Vulnerability:")
                                    print(f"            Vuln ID: {sample.get('vuln_id')}")
                                    print(f"            Name: {sample.get('vt_name')}")
                                    print(f"            Severity: {sample.get('severity')}")
                                    print(f"            Affects: {sample.get('affects_url')}")
                            else:
                                print(f"          Error Response: {v_resp.text[:200]}")
                        except Exception as ve:
                            print(f"          Request failed: {ve}")
            else:
                print(f"        Error: {scans_resp.text}")
                
    except Exception as e:
        print(f"[-] Error querying Acunetix API: {e}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else None
    test_acunetix(q)
