import logging
from django.db import IntegrityError
from django.db.models import Q
from startScan.models import Vulnerability, Subdomain, EndPoint


logger = logging.getLogger(__name__)

class VulnerabilityCorrelationEngine:
    """
    Orchestrates vulnerability correlation across multiple tools (Nuclei, Semgrep, Retire.js).
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
        
        # 3. Exploitability (Check CISA KEV)
        exploit_score = 0.5
        if vuln.exploit_url:
            exploit_score = 1.0
        elif vuln.cve_ids.filter(is_cisa_kev=True).exists():
            exploit_score = 1.0
            logger.info(f"Vulnerability {vuln.id} ({vuln.name}) boosted due to CISA KEV status.")
        
        score += exploit_score * self.weights['exploitability']
        
        # 4. Asset Criticality
        criticality = 1
        if vuln.subdomain and vuln.subdomain.criticality_level:
            criticality = vuln.subdomain.criticality_level
        crit_score = criticality / 5.0
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
        
        # Check if an APME path already exists to avoid overwriting it with a generic heuristic.
        # Use filter() instead of get() to safely handle the case where multiple ImpactAssessment
        # rows exist for the same vulnerability (can occur when APME and correlation both create rows).
        existing_qs = ImpactAssessment.objects.filter(vulnerability=vuln)
        existing = existing_qs.order_by('-updated_at').first()
        if existing and existing.potential_attack_chain and 'apme_path_id' in existing.potential_attack_chain:
            logger.info(f"Correlation: Skipping heuristic chain for vuln {vuln.id}, APME path already exists.")
            return

        # Deduplicate: if more than one row exists for this vulnerability, delete the extras
        # keeping only the most recent. This handles pre-existing duplicates without crashing.
        if existing_qs.count() > 1:
            logger.warning(
                f"Correlation: Found {existing_qs.count()} ImpactAssessment rows for vuln {vuln.id}. "
                f"Deduplicating — keeping most recent record."
            )
            # Keep the most recent record, delete all others
            ids_to_delete = existing_qs.order_by('-updated_at').values_list('id', flat=True)[1:]
            ImpactAssessment.objects.filter(id__in=list(ids_to_delete)).delete()

        # Now safely perform an update-or-create using the single canonical record
        if existing:
            existing.potential_attack_chain = chain
            existing.scan_history = self.scan_history
            existing.subdomain = vuln.subdomain
            existing.save()
        else:
            try:
                ImpactAssessment.objects.create(
                    vulnerability=vuln,
                    potential_attack_chain=chain,
                    scan_history=self.scan_history,
                    subdomain=vuln.subdomain
                )
            except IntegrityError:
                # Handle concurrent creation by another task to prevent unique violation IntegrityError
                logger.warning(f"Correlation: ImpactAssessment for vuln {vuln.id} was created concurrently. Updating instead.")
                ImpactAssessment.objects.filter(vulnerability=vuln).update(
                    potential_attack_chain=chain,
                    scan_history=self.scan_history,
                    subdomain=vuln.subdomain
                )

