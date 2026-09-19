from django.db import connection
from rest_framework.response import Response

from dashboard.models import Project
from mcp.pagination import page_queryset, parse_limit_offset, page_payload
from mcp.views.base import McpDataView
from scanEngine.models import EngineType
from startScan.models import (
    EndPoint,
    Exposure,
    ScanHistory,
    Subdomain,
    SubScan,
    Vulnerability,
)
from targetApp.models import Domain


def _dt(value):
    return value.isoformat() if value else None


def serialize_project(row):
    return {'id': row.id, 'name': row.name, 'slug': row.slug}


def serialize_target(row):
    return {
        'id': row.id,
        'name': row.name,
        'project_slug': row.project.slug if row.project_id else None,
        'target_type': row.target_type,
        'insert_date': _dt(row.insert_date),
    }


def serialize_scan(row):
    return {
        'id': row.id,
        'domain_id': row.domain_id,
        'domain_name': row.domain.name if row.domain_id else None,
        'engine_id': row.scan_type_id,
        'scan_status': row.scan_status,
        'start_scan_date': _dt(row.start_scan_date),
        'stop_scan_date': _dt(row.stop_scan_date),
    }


def serialize_subscan(row):
    return {
        'id': row.id,
        'scan_id': row.scan_history_id,
        'subdomain_id': row.subdomain_id,
        'type': row.type,
        'status': row.status,
        'start_scan_date': _dt(row.start_scan_date),
        'stop_scan_date': _dt(row.stop_scan_date),
    }


def serialize_subdomain(row):
    return {
        'id': row.id,
        'name': row.name,
        'scan_id': row.scan_history_id,
        'http_status': row.http_status,
    }


def serialize_endpoint(row):
    return {
        'id': row.id,
        'http_url': row.http_url,
        'scan_id': row.scan_history_id,
        'http_status': row.http_status,
    }


def serialize_vulnerability(row):
    return {
        'id': row.id,
        'name': row.name,
        'severity': row.severity,
        'scan_id': row.scan_history_id,
        'subdomain': row.subdomain.name if row.subdomain_id else None,
        'http_url': row.http_url,
    }


def serialize_exposure(row):
    return {
        'id': row.id,
        'type': row.type,
        'status': row.status,
        'scan_id': row.scan_history_id,
        'target_id': row.target_domain_id,
        'risk_score': row.risk_score,
    }


def serialize_email(row):
    return {
        'id': row.id,
        'address': row.address,
        'source': row.source,
    }


def serialize_employee(row):
    return {
        'id': row.id,
        'name': row.name,
        'designation': row.designation,
    }


def serialize_engine(row):
    return {'id': row.id, 'engine_name': row.engine_name}


class McpListProjectsView(McpDataView):
    def get(self, request):
        qs = Project.objects.all().order_by('name')
        return Response(page_queryset(qs, request, serialize_project))


class McpListTargetsView(McpDataView):
    def get(self, request):
        slug = request.query_params.get('project_slug')
        if not slug:
            return Response({'error': 'project_slug is required'}, status=400)
        qs = Domain.objects.filter(project__slug=slug).select_related('project').order_by('name')
        query = request.query_params.get('query')
        if query:
            qs = qs.filter(name__icontains=query)
        return Response(page_queryset(qs, request, serialize_target))


class McpGetTargetView(McpDataView):
    def get(self, request, pk):
        row = Domain.objects.select_related('project').filter(pk=pk).first()
        if not row:
            return Response({'error': 'Not found'}, status=404)
        return Response(serialize_target(row))


class McpListScansView(McpDataView):
    def get(self, request):
        slug = request.query_params.get('project_slug')
        if not slug:
            return Response({'error': 'project_slug is required'}, status=400)
        qs = ScanHistory.objects.filter(domain__project__slug=slug).select_related('domain').order_by('-id')
        target_id = request.query_params.get('target_id')
        if target_id:
            qs = qs.filter(domain_id=target_id)
        status_filter = request.query_params.get('status')
        if status_filter not in (None, ''):
            try:
                qs = qs.filter(scan_status=int(status_filter))
            except (TypeError, ValueError):
                return Response({'error': 'status must be an integer'}, status=400)
        return Response(page_queryset(qs, request, serialize_scan))


class McpGetScanView(McpDataView):
    def get(self, request, pk):
        row = ScanHistory.objects.select_related('domain').filter(pk=pk).first()
        if not row:
            return Response({'error': 'Not found'}, status=404)
        return Response(serialize_scan(row))


class McpScanStatusView(McpDataView):
    def get(self, request):
        slug = request.query_params.get('project_slug')
        if not slug:
            return Response({'error': 'project_slug is required'}, status=400)
        qs = ScanHistory.objects.filter(domain__project__slug=slug).select_related('domain')
        payload = {
            'pending': [serialize_scan(s) for s in qs.filter(scan_status=-1).order_by('-id')[:100]],
            'scanning': [serialize_scan(s) for s in qs.filter(scan_status=1).order_by('-id')[:100]],
            'completed': [serialize_scan(s) for s in qs.filter(scan_status__in=[0, 2, 3]).order_by('-id')[:10]],
        }
        return Response(payload)


class McpListSubscansView(McpDataView):
    def get(self, request):
        scan_id = request.query_params.get('scan_id')
        if not scan_id:
            return Response({'error': 'scan_id is required'}, status=400)
        qs = SubScan.objects.filter(scan_history_id=scan_id).order_by('-id')
        return Response(page_queryset(qs, request, serialize_subscan))


class McpListSubdomainsView(McpDataView):
    def get(self, request):
        scan_id = request.query_params.get('scan_id')
        if not scan_id:
            return Response({'error': 'scan_id is required'}, status=400)
        qs = Subdomain.objects.filter(scan_history_id=scan_id).order_by('name')
        query = request.query_params.get('query')
        if query:
            qs = qs.filter(name__icontains=query)
        return Response(page_queryset(qs, request, serialize_subdomain))


class McpListEndpointsView(McpDataView):
    def get(self, request):
        scan_id = request.query_params.get('scan_id')
        if not scan_id:
            return Response({'error': 'scan_id is required'}, status=400)
        qs = EndPoint.objects.filter(scan_history_id=scan_id).order_by('id')
        query = request.query_params.get('query')
        if query:
            qs = qs.filter(http_url__icontains=query)
        return Response(page_queryset(qs, request, serialize_endpoint))


class McpListVulnerabilitiesView(McpDataView):
    def get(self, request):
        qs = Vulnerability.objects.select_related('subdomain').order_by('-id')
        scan_id = request.query_params.get('scan_id')
        target_id = request.query_params.get('target_id')
        if scan_id:
            qs = qs.filter(scan_history_id=scan_id)
        if target_id:
            qs = qs.filter(target_domain_id=target_id)
        severity = request.query_params.get('severity')
        if severity not in (None, ''):
            try:
                qs = qs.filter(severity=int(severity))
            except (TypeError, ValueError):
                return Response({'error': 'severity must be an integer'}, status=400)
        query = request.query_params.get('query')
        if query:
            qs = qs.filter(name__icontains=query)
        return Response(page_queryset(qs, request, serialize_vulnerability))


class McpListExposuresView(McpDataView):
    def get(self, request):
        qs = Exposure.objects.order_by('-id')
        scan_id = request.query_params.get('scan_id')
        target_id = request.query_params.get('target_id')
        if scan_id:
            qs = qs.filter(scan_history_id=scan_id)
        if target_id:
            qs = qs.filter(target_domain_id=target_id)
        query = request.query_params.get('query')
        if query:
            qs = qs.filter(status__icontains=query)
        return Response(page_queryset(qs, request, serialize_exposure))


class McpListEmailsView(McpDataView):
    def get(self, request):
        scan_id = request.query_params.get('scan_id')
        if not scan_id:
            return Response({'error': 'scan_id is required'}, status=400)
        scan = ScanHistory.objects.filter(pk=scan_id).first()
        if not scan:
            return Response({'error': 'Not found'}, status=404)
        qs = scan.emails.all().order_by('id')
        return Response(page_queryset(qs, request, serialize_email))


class McpListEmployeesView(McpDataView):
    def get(self, request):
        scan_id = request.query_params.get('scan_id')
        if not scan_id:
            return Response({'error': 'scan_id is required'}, status=400)
        scan = ScanHistory.objects.filter(pk=scan_id).first()
        if not scan:
            return Response({'error': 'Not found'}, status=404)
        qs = scan.employees.all().order_by('id')
        return Response(page_queryset(qs, request, serialize_employee))


class McpSearchView(McpDataView):
    def get(self, request):
        query = (request.query_params.get('query') or '').strip()
        if not query:
            return Response({'error': 'query is required'}, status=400)
        slug = request.query_params.get('project_slug')
        domains = Domain.objects.filter(name__icontains=query)
        scans = ScanHistory.objects.filter(domain__name__icontains=query).select_related('domain')
        vulns = Vulnerability.objects.filter(name__icontains=query)
        if slug:
            domains = domains.filter(project__slug=slug)
            scans = scans.filter(domain__project__slug=slug)
            vulns = vulns.filter(scan_history__domain__project__slug=slug)
        limit, offset = parse_limit_offset(request)
        items = (
            [{'type': 'target', **serialize_target(row)} for row in domains[offset:offset + limit]]
            + [{'type': 'scan', **serialize_scan(row)} for row in scans[offset:offset + limit]]
            + [{'type': 'vulnerability', **serialize_vulnerability(row)} for row in vulns[offset:offset + limit]]
        )
        total = domains.count() + scans.count() + vulns.count()
        return Response(page_payload(items[:limit], total, limit, offset))


class McpDashboardView(McpDataView):
    def get(self, request):
        slug = request.query_params.get('project_slug')
        if not slug:
            return Response({'error': 'project_slug is required'}, status=400)
        project = Project.objects.filter(slug=slug).first()
        if not project:
            return Response({'error': 'Not found'}, status=404)
        vulns = Vulnerability.objects.filter(scan_history__domain__project=project)
        return Response({
            'project': serialize_project(project),
            'kpis': {
                'domain_count': Domain.objects.filter(project=project).count(),
                'subdomain_count': Subdomain.objects.filter(scan_history__domain__project=project).count(),
                'endpoint_count': EndPoint.objects.filter(scan_history__domain__project=project).count(),
                'vulnerability_count': vulns.count(),
                'critical_count': vulns.filter(severity=4).count(),
                'high_count': vulns.filter(severity=3).count(),
            },
        })


class McpAttackPathsView(McpDataView):
    def get(self, request):
        from startScan.models import ImpactAssessment

        scan_id = request.query_params.get('scan_id')
        project_slug = request.query_params.get('project_slug') or request.query_params.get('project')
        if not scan_id and not project_slug:
            return Response({'error': 'scan_id or project_slug is required'}, status=400)
        assessments = ImpactAssessment.objects.all()
        if scan_id:
            try:
                assessments = assessments.filter(scan_history_id=int(scan_id))
            except (TypeError, ValueError):
                return Response({'error': 'scan_id must be an integer'}, status=400)
        if project_slug:
            assessments = assessments.filter(scan_history__domain__project__slug=project_slug)
        assessments = (
            assessments
            .exclude(potential_attack_chain__isnull=True)
            .exclude(potential_attack_chain={})
            .order_by('-remediation_priority', '-scan_history__start_scan_date')
        )
        paths = []
        for assessment in assessments:
            chain = assessment.potential_attack_chain or {}
            if not chain.get('apme_path_id'):
                continue
            paths.append({
                'path_id': chain.get('apme_path_id'),
                'risk': chain.get('risk', 'unknown'),
                'score': chain.get('score', 0.0),
                'step_count': len(chain.get('steps', [])),
                'steps': chain.get('steps', []),
                'potential_impact': assessment.potential_impact,
                'remediation_priority': assessment.remediation_priority,
                'vulnerability_id': assessment.vulnerability_id,
            })
        return Response({'total_paths': len(paths), 'paths': paths})


class McpListEnginesView(McpDataView):
    def get(self, request):
        qs = EngineType.objects.all().order_by('engine_name')
        return Response(page_queryset(qs, request, serialize_engine))


class McpHealthView(McpDataView):
    def get(self, request):
        db_up = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            db_up = False
        return Response({
            'status': 'online' if db_up else 'degraded',
            'database': {'status': 'up' if db_up else 'down'},
        })
