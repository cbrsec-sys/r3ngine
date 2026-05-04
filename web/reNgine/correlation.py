import logging
from django.db.models import Q
from startScan.models import Vulnerability, Subdomain, EndPoint


logger = logging.getLogger(__name__)

class VulnerabilityCorrelationEngine:
    """
    Orchestrates vulnerability correlation across multiple tools (Nuclei, Semgrep, Trivy, Retire.js).
    """
    
    def __init__(self, scan_history=None):
        self.scan_history = scan_history
        self.weights = {
            'severity': 0.4,
            'multi_tool_match': 0.3,
            'exploitability': 0.2,
            'asset_criticality': 0.1
        }

    def correlate_findings(self, subdomain_id=None):
        """
        Groups vulnerabilities by asset and CVE/type to calculate correlation scores.
        """
        query = Q()
        if subdomain_id:
            query &= Q(subdomain_id=subdomain_id)
        if self.scan_history:
            query &= Q(subdomain__scan_history=self.scan_history)
            
        vulns = Vulnerability.objects.filter(query).prefetch_related('cve_ids', 'cwe_ids')
        
        for vuln in vulns:
            self._process_single_vuln(vuln)

    def _process_single_vuln(self, vuln):
        """
        Calculates the correlation score for a single vulnerability based on multi-tool evidence.
        """
        score = 0.0
        
        # 1. Base Severity Score (0-1)
        severity_score = (vuln.severity or 1) / 4.0
        score += severity_score * self.weights['severity']
        
        # 2. Multi-Tool Match (SCA vs DAST vs SAST)
        match_boost, tools = self._calculate_tool_match_boost(vuln)
        score += match_boost * self.weights['multi_tool_match']
        
        # 3. Exploitability
        exploit_score = 1.0 if vuln.exploit_url else 0.5
        score += exploit_score * self.weights['exploitability']
        
        # 4. Asset Criticality
        crit_score = (vuln.subdomain.criticality_level or 1) / 5.0
        score += crit_score * self.weights['asset_criticality']
        
        vuln.correlation_score = round(score * 100, 2)
        
        # If score is very high, auto-verify if possible
        if vuln.correlation_score > 85 and vuln.validation_status == 'unverified':
            vuln.validation_status = 'verified'
            
        vuln.save()
        
        # Generate Potential Attack Chain
        self._generate_attack_chain(vuln, tools)

    def _calculate_tool_match_boost(self, vuln):
        """
        Checks if other tools confirmed this finding.
        Returns (boost_score, list_of_tools)
        """
        tools = ['Nuclei'] # Default
        boost = 0.5
        cve_ids = list(vuln.cve_ids.values_list('name', flat=True))
        
        # Find other vulnerabilities on the same asset with same identifiers
        other_findings = Vulnerability.objects.filter(
            subdomain=vuln.subdomain,
            cve_ids__name__in=cve_ids
        ).exclude(id=vuln.id)
        
        for other in other_findings:
            tool_name = self._infer_tool_name(other)
            if tool_name not in tools:
                tools.append(tool_name)
        
        if len(tools) > 1:
            boost = 1.0 # High confidence
            
        return boost, tools

    def _infer_tool_name(self, vuln):
        """Heuristic to determine tool name from vulnerability type/name."""
        name = vuln.name.lower()
        if 'gitleaks' in name: return 'Gitleaks'
        if 'trivy' in name: return 'Trivy'
        if 'semgrep' in name: return 'Semgrep'
        if 'retire' in name: return 'Retire.js'
        if 'nuclei' in name: return 'Nuclei'
        return 'Other'

    def _generate_attack_chain(self, vuln, tools):
        """
        Populates the potential_attack_chain in ImpactAssessment.
        """
        from startScan.models import ImpactAssessment
        
        chain = {
            'steps': [
                {'phase': 'Discovery', 'description': f"Identified via {', '.join(tools)}"},
            ],
            'confidence': 'High' if len(tools) > 1 else 'Medium'
        }
        
        # Heuristic steps based on vuln type
        if vuln.type == 'SCA':
            chain['steps'].append({'phase': 'Exploitation', 'description': "Leverage known CVE in public-facing dependency"})
        elif vuln.type == 'SAST':
            chain['steps'].append({'phase': 'Exploitation', 'description': "Exploit insecure code pattern (e.g. Injection)"})
        elif 'leak' in vuln.name.lower() or 'secret' in vuln.name.lower():
            chain['steps'].append({'phase': 'Exploitation', 'description': "Use exposed credentials/keys to access unauthorized services"})
        
        chain['steps'].append({'phase': 'Post-Exploitation', 'description': "Pivot to internal network or access sensitive data"})
        
        ImpactAssessment.objects.update_or_create(
            vulnerability=vuln,
            defaults={
                'potential_attack_chain': chain,
                'scan_history': self.scan_history,
                'subdomain': vuln.subdomain
            }
        )

    def run_trivy_scan(self, target_path):
        """
        Wrapper to run Trivy on a specific directory and return findings.
        """
        import subprocess
        import json
        import os
        
        output_file = "/tmp/trivy_results.json"
        cmd = f"trivy fs --format json --output {output_file} {target_path}"
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Trivy scan failed: {e}")
            
        return None
