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
        
        # In-memory prefetch optimization for duplicate findings search (L90)
        subdomain_ids = {v.subdomain_id for v in vulns if v.subdomain_id}
        subdomain_cve_map = {}
        if subdomain_ids:
            all_subdomain_vulns = Vulnerability.objects.filter(
                subdomain_id__in=subdomain_ids
            ).prefetch_related('cve_ids')
            for v in all_subdomain_vulns:
                if not v.subdomain_id:
                    continue
                for cve in v.cve_ids.all():
                    key = (v.subdomain_id, cve.name)
                    if key not in subdomain_cve_map:
                        subdomain_cve_map[key] = []
                    subdomain_cve_map[key].append(v)

        # In-memory prefetch optimization for ImpactAssessment records
        vuln_ids = [v.id for v in vulns]
        from startScan.models import ImpactAssessment
        existing_assessments = ImpactAssessment.objects.filter(vulnerability_id__in=vuln_ids)
        
        assessments_by_vuln = {}
        for assessment in existing_assessments:
            if assessment.vulnerability_id not in assessments_by_vuln:
                assessments_by_vuln[assessment.vulnerability_id] = []
            assessments_by_vuln[assessment.vulnerability_id].append(assessment)

        # Batch accumulators to minimize write database hits
        vulns_to_update = []
        assessments_to_create = []
        assessments_to_update = []
        assessment_ids_to_delete = []
        
        for vuln in vulns:
            self._process_single_vuln(
                vuln,
                subdomain_cve_map=subdomain_cve_map,
                assessments_by_vuln=assessments_by_vuln,
                vulns_to_update=vulns_to_update,
                assessments_to_create=assessments_to_create,
                assessments_to_update=assessments_to_update,
                assessment_ids_to_delete=assessment_ids_to_delete
            )

        # Perform bulk write operations
        if vulns_to_update:
            Vulnerability.objects.bulk_update(vulns_to_update, ['correlation_score', 'validation_status'])
            
        if assessment_ids_to_delete:
            ImpactAssessment.objects.filter(id__in=assessment_ids_to_delete).delete()
            
        if assessments_to_create:
            ImpactAssessment.objects.bulk_create(assessments_to_create)
            
        if assessments_to_update:
            ImpactAssessment.objects.bulk_update(assessments_to_update, ['potential_attack_chain', 'scan_history', 'subdomain'])

    def _process_single_vuln(self, vuln, subdomain_cve_map, assessments_by_vuln, vulns_to_update, assessments_to_create, assessments_to_update, assessment_ids_to_delete):
        """
        Calculates the correlation score for a single vulnerability based on multi-tool evidence.
        """
        score = 0.0
        
        # 1. Base Severity Score (0-1)
        severity_score = (vuln.severity or 1) / 4.0
        score += severity_score * self.weights['severity']
        
        # 2. Multi-Tool Match (SCA vs DAST vs SAST)
        match_boost, tools = self._calculate_tool_match_boost(vuln, subdomain_cve_map)
        score += match_boost * self.weights['multi_tool_match']
        
        # 3. Exploitability (Check CISA KEV - Optimized using in-memory list instead of filter)
        exploit_score = 0.5
        if vuln.exploit_url:
            exploit_score = 1.0
        elif any(cve.is_cisa_kev for cve in vuln.cve_ids.all()):
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
            
        vulns_to_update.append(vuln)
        
        # Generate Potential Attack Chain
        self._generate_attack_chain(
            vuln,
            tools,
            assessments_by_vuln=assessments_by_vuln,
            assessments_to_create=assessments_to_create,
            assessments_to_update=assessments_to_update,
            assessment_ids_to_delete=assessment_ids_to_delete
        )

    def _calculate_tool_match_boost(self, vuln, subdomain_cve_map):
        """
        Checks if other tools confirmed this finding (Optimized using in-memory map instead of query loop).
        Returns (boost_score, list_of_tools)
        """
        tools = ['Nuclei'] # Default
        boost = 0.5
        cve_ids = list(vuln.cve_ids.values_list('name', flat=True))
        
        other_findings = []
        if vuln.subdomain_id:
            seen_ids = set()
            for name in cve_ids:
                key = (vuln.subdomain_id, name)
                for other in subdomain_cve_map.get(key, []):
                    if other.id != vuln.id and other.id not in seen_ids:
                        other_findings.append(other)
                        seen_ids.add(other.id)
        
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

    def _generate_attack_chain(self, vuln, tools, assessments_by_vuln, assessments_to_create, assessments_to_update, assessment_ids_to_delete):
        """
        Populates the potential_attack_chain in ImpactAssessment (Optimized using in-memory batch maps).
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
        
        existing_list = assessments_by_vuln.get(vuln.id, [])
        if existing_list:
            existing_list.sort(key=lambda x: x.updated_at or x.id, reverse=True)
        existing = existing_list[0] if existing_list else None
        
        if existing and existing.potential_attack_chain and 'apme_path_id' in existing.potential_attack_chain:
            logger.info(f"Correlation: Skipping heuristic chain for vuln {vuln.id}, APME path already exists.")
            return

        # Deduplicate
        if len(existing_list) > 1:
            logger.warning(
                f"Correlation: Found {len(existing_list)} ImpactAssessment rows for vuln {vuln.id}. "
                f"Deduplicating — keeping most recent record."
            )
            assessment_ids_to_delete.extend([x.id for x in existing_list[1:]])

        # Safely perform updates/creates via batch lists
        if existing:
            existing.potential_attack_chain = chain
            existing.scan_history = self.scan_history
            existing.subdomain = vuln.subdomain
            assessments_to_update.append(existing)
        else:
            assessment = ImpactAssessment(
                vulnerability=vuln,
                potential_attack_chain=chain,
                scan_history=self.scan_history,
                subdomain=vuln.subdomain
            )
            assessments_to_create.append(assessment)
