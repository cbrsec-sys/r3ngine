import os
import markdown
import logging
from datetime import datetime
from django.core.files.base import ContentFile
from django.template.loader import get_template
from django.db.models import Count, Case, When, IntegerField
from weasyprint import HTML, CSS
from django.utils import timezone

from reNgine.celery import app
from reNgine.definitions import *
from reNgine.llm import LLMReportGenerator
from reNgine.charts import (
    generate_subdomain_chart_by_http_status,
    generate_vulnerability_chart_by_severity,
    generate_attack_surface_map
)
from reNgine.graph_utils import Neo4jManager
from reNgine.common_func import get_interesting_subdomains
from startScan.models import ScanHistory, Subdomain, Vulnerability, IpAddress, ScanReport
from scanEngine.models import VulnerabilityReportSetting

logger = logging.getLogger('reNgine.tasks')

@app.task(name='generate_report_task', bind=True, queue='report_queue')
def generate_report_task(self, report_id):
    try:
        report_obj = ScanReport.objects.get(id=report_id)
        report_obj.status = 1 # Running
        report_obj.save()

        scan = report_obj.scan_history
        report_type = report_obj.report_type
        report_template = report_obj.report_template
        params = report_obj.params
        is_ignore_info_vuln = params.get('ignore_info_vuln', False)
        include_attack_surface_map = params.get('include_attack_surface_map', False)

        show_recon = True
        show_vuln = True
        report_name = 'Full Scan Report'

        if report_type == 'vulnerability':
            show_recon = False
            report_name = 'Vulnerability Report'

        vulns = (
            Vulnerability.objects
            .filter(scan_history=scan)
            .order_by('-severity')
        ) if not is_ignore_info_vuln else (
            Vulnerability.objects
            .filter(scan_history=scan)
            .exclude(severity=0)
            .order_by('-severity')
        )

        unique_vulns = (
            Vulnerability.objects
            .filter(scan_history=scan)
            .values("name", "severity")
            .annotate(count=Count('name'))
            .order_by('-severity', '-count')
        ) if not is_ignore_info_vuln else (
            Vulnerability.objects
            .filter(scan_history=scan)
            .exclude(severity=0)
            .values("name", "severity")
            .annotate(count=Count('name'))
            .order_by('-severity', '-count')
        )

        subdomains = (
            Subdomain.objects
            .filter(scan_history=scan)
            .order_by('-content_length')
        )
        subdomain_alive_count = (
            Subdomain.objects
            .filter(scan_history=scan)
            .values('name')
            .distinct()
            .filter(http_status__exact=200)
            .count()
        )
        
        interesting_subdomains = get_interesting_subdomains(scan_history=scan.id)
        interesting_subdomains = interesting_subdomains.annotate(
            sort_order=Case(
                When(http_status__gte=200, http_status__lt=300, then=1),
                When(http_status__gte=300, http_status__lt=400, then=2),
                When(http_status__gte=400, http_status__lt=500, then=3),
                default=4,
                output_field=IntegerField(),
            )
        ).order_by('sort_order', 'http_status')

        subdomains = subdomains.annotate(
            sort_order=Case(
                When(http_status__gte=200, http_status__lt=300, then=1),
                When(http_status__gte=300, http_status__lt=400, then=2),
                When(http_status__gte=400, http_status__lt=500, then=3),
                default=4,
                output_field=IntegerField(),
            )
        ).order_by('sort_order', 'http_status')

        ip_addresses = (
            IpAddress.objects
            .filter(ip_addresses__in=subdomains)
            .distinct()
        )

        attack_surface_map_image = None
        if report_template == 'enterprise' and include_attack_surface_map:
            try:
                neo4j_manager = Neo4jManager()
                graph_data = neo4j_manager.get_cytoscape_json(scan.id)
                if graph_data and graph_data.get('nodes'):
                    attack_surface_map_image = generate_attack_surface_map(graph_data)
                neo4j_manager.close()
            except Exception as e:
                logger.error(f"Error generating Attack Surface Map for report: {e}")

        data = {
            'scan_object': scan,
            'unique_vulnerabilities': unique_vulns,
            'all_vulnerabilities': vulns,
            'all_vulnerabilities_count': vulns.count(),
            'subdomain_alive_count': subdomain_alive_count,
            'interesting_subdomains': interesting_subdomains,
            'subdomains': subdomains,
            'ip_addresses': ip_addresses,
            'show_recon': show_recon,
            'show_vuln': show_vuln,
            'report_name': report_name,
            'is_ignore_info_vuln': is_ignore_info_vuln,
            'attack_surface_map_image': attack_surface_map_image,
        }

        # Get report related config
        primary_color = '#00f3ff'
        secondary_color = '#0d0c14'
        
        vuln_report_query = VulnerabilityReportSetting.objects.all()
        if vuln_report_query.exists():
            report_setting = vuln_report_query[0]
            data['company_name'] = report_setting.company_name
            data['company_address'] = report_setting.company_address
            data['company_email'] = report_setting.company_email
            data['company_website'] = report_setting.company_website
            data['show_rengine_banner'] = report_setting.show_rengine_banner
            data['show_footer'] = report_setting.show_footer
            data['footer_text'] = report_setting.footer_text
            data['show_executive_summary'] = report_setting.show_executive_summary

            # Replace executive_summary_description with template syntax
            description = report_setting.executive_summary_description
            description = description.replace('{scan_date}', scan.start_scan_date.strftime('%d %B, %Y'))
            description = description.replace('{company_name}', report_setting.company_name)
            description = description.replace('{target_name}', scan.domain.name)
            description = description.replace('{subdomain_count}', str(subdomains.count()))
            description = description.replace('{vulnerability_count}', str(vulns.count()))
            description = description.replace('{critical_count}', str(vulns.filter(severity=4).count()))
            description = description.replace('{high_count}', str(vulns.filter(severity=3).count()))
            description = description.replace('{medium_count}', str(vulns.filter(severity=2).count()))
            description = description.replace('{low_count}', str(vulns.filter(severity=1).count()))
            description = description.replace('{info_count}', str(vulns.filter(severity=0).count()))
            description = description.replace('{unknown_count}', str(vulns.filter(severity=-1).count()))
            if scan.domain.description:
                description = description.replace('{target_description}', scan.domain.description)

            data['executive_summary_description'] = markdown.markdown(description)

            # LLM Generated Sections
            if report_setting.enable_llm_report_generation:
                llm_gen = LLMReportGenerator(logger=logger)
                
                llm_context = f"Target: {scan.domain.name}\n"
                if scan.domain.description:
                    llm_context += f"Target Description: {scan.domain.description}\n"
                llm_context += f"Scan Date: {scan.start_scan_date.strftime('%d %B, %Y')}\n"
                llm_context += f"Subdomains discovered: {subdomains.count()}\n"
                llm_context += f"Vulnerabilities identified: {vulns.count()}\n"
                llm_context += f"- Critical: {vulns.filter(severity=4).count()}\n"
                llm_context += f"- High: {vulns.filter(severity=3).count()}\n"
                llm_context += f"- Medium: {vulns.filter(severity=2).count()}\n"
                llm_context += f"- Low: {vulns.filter(severity=1).count()}\n"
                llm_context += f"- Info: {vulns.filter(severity=0).count()}\n"
                
                if vulns.exists():
                    llm_context += "Top Vulnerabilities:\n"
                    for v in unique_vulns[:10]:
                        llm_context += f"- {v['name']} ({v['count']})\n"

                data['llm_overview'] = markdown.markdown(llm_gen.generate_overview(llm_context))
                data['llm_executive_brief'] = markdown.markdown(llm_gen.generate_executive_brief(llm_context))
                data['llm_conclusion'] = markdown.markdown(llm_gen.generate_conclusion(llm_context))
                data['enable_llm_report_generation'] = True

            primary_color = report_setting.primary_color
            secondary_color = report_setting.secondary_color

        data['primary_color'] = primary_color
        data['secondary_color'] = secondary_color

        data['subdomain_http_status_chart'] = generate_subdomain_chart_by_http_status(subdomains)
        data['vulns_severity_chart'] = generate_vulnerability_chart_by_severity(vulns) if vulns else ''

        if report_template == 'enterprise':
            template = get_template('report/enterprise.html')
        elif report_template == 'modern':
            template = get_template('report/modern.html')
        else:
            template = get_template('report/default.html')

        html = template.render(data)
        pdf = HTML(string=html).write_pdf()

        target_name = scan.domain.name
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{target_name}_Report_{date_str}.pdf"

        # Save to FileField
        report_obj.report_file.save(filename, ContentFile(pdf))
        report_obj.status = 2 # Success
        report_obj.completed_at = timezone.now()
        report_obj.save()

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        report_obj = ScanReport.objects.get(id=report_id)
        report_obj.status = 0 # Failed
        report_obj.error_message = str(e)
        report_obj.save()
