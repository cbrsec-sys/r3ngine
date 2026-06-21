import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

_WORKFLOW_META = {
    'user-hunt':       ('User Hunt',            'Enumerate users across social platforms and data sources', ['target', 'target_type']),
    'url-bypass':      ('URL Bypass',           'Attempt WAF/auth bypass against target URLs',              ['urls']),
    'wordpress':       ('WordPress Recon',      'Deep reconnaissance of WordPress installations',           ['urls']),
    'host-recon':      ('Host Recon',           'Full host-level recon including ports and services',       ['target', 'target_type']),
    'cidr-recon':      ('CIDR Recon',           'Recon across an entire CIDR network block',                ['cidr']),
    'code-scan':       ('Code Scan',            'Static analysis via Vigolium scanner',                     ['target', 'target_type']),
    'domain-recon':    ('Domain Recon',         'Full domain reconnaissance (subdomains, DNS, OSINT)',      ['domain']),
    'subdomain-recon': ('Subdomain Recon',      'Subdomain enumeration and takeover checks',                ['domain']),
    'url-crawl':       ('URL Crawl',            'Deep crawl of target URLs collecting endpoints',           ['urls']),
    'url-dirsearch':   ('Directory Search',     'Directory and file fuzzing against target URLs',           ['urls']),
    'url-fuzz':        ('URL Fuzz',             'Parameter fuzzing against target URLs',                    ['urls']),
    'url-params-fuzz': ('URL Params Fuzz',      'CPDE-powered injectable parameter discovery',              ['urls']),
    'url-vuln':        ('Vulnerability Scan',   'Nuclei-powered vulnerability scan against target URLs',    ['urls']),
}


class WorkflowMobileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workflows = [
            {
                'slug': slug,
                'name': name,
                'description': desc,
                'required_fields': required_fields,
            }
            for slug, (name, desc, required_fields) in _WORKFLOW_META.items()
        ]
        return Response({'workflows': workflows})
