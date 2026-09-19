from rest_framework.response import Response

from api.apme_views import RecalculateAttackPathsAPIView, TriggerLLMAPMEAPIView
from api.permissions import HasPermission, IsPenetrationTester
from api.views.recon import (
    StartEmailDiscoveryView,
    StartEmployeeIntelView,
    StopEmailDiscoveryView,
    StopEmployeeIntelView,
)
from api.views.scan import (
    InitiateScan,
    InitiateSubTask,
    PauseScan,
    ResumeScan,
    ScanActivityRetryAPIView,
    StartWorkflowView,
    StopScan,
)
from mcp.views.base import McpDataView
from reNgine.definitions import PERM_INITATE_SCANS_SUBSCANS


def _delegate_post(view_cls, request, **kwargs):
    view = view_cls()
    view.args = ()
    view.kwargs = kwargs
    view.request = request
    view.format_kwarg = None
    return view.post(request, **kwargs)


def _copy_scan_id_to_scan_ids(request):
    data = request.data
    if data.get('scan_ids'):
        return
    scan_id = data.get('scan_id')
    if scan_id is None:
        return
    try:
        data['scan_ids'] = [scan_id]
    except (TypeError, AttributeError):
        request._full_data = {**dict(data), 'scan_ids': [scan_id]}


class McpScanDispatchView(McpDataView):
    http_method_names = ['post', 'options']
    permission_classes = [HasPermission]
    permission_required = PERM_INITATE_SCANS_SUBSCANS


class McpIntelDispatchView(McpDataView):
    http_method_names = ['post', 'options']
    permission_classes = [IsPenetrationTester]


class McpStartScanView(McpScanDispatchView):
    def post(self, request):
        return _delegate_post(InitiateScan, request)


class McpPauseScanView(McpScanDispatchView):
    def post(self, request):
        _copy_scan_id_to_scan_ids(request)
        return _delegate_post(PauseScan, request)


class McpResumeScanView(McpScanDispatchView):
    def post(self, request):
        return _delegate_post(ResumeScan, request)


class McpStopScanView(McpScanDispatchView):
    def post(self, request):
        _copy_scan_id_to_scan_ids(request)
        return _delegate_post(StopScan, request)


class McpStartSubscanView(McpScanDispatchView):
    def post(self, request):
        return _delegate_post(InitiateSubTask, request)


class McpRetryTaskView(McpScanDispatchView):
    def post(self, request):
        pk = request.data.get('task_id') or request.data.get('pk')
        if not pk:
            return Response({'error': 'task_id is required'}, status=400)
        return _delegate_post(ScanActivityRetryAPIView, request, pk=pk)


class McpStartEmailDiscoveryView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(StartEmailDiscoveryView, request)


class McpStopEmailDiscoveryView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(StopEmailDiscoveryView, request)


class McpStartEmployeeIntelView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(StartEmployeeIntelView, request)


class McpStopEmployeeIntelView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(StopEmployeeIntelView, request)


class McpTriggerApmeView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(TriggerLLMAPMEAPIView, request)


class McpRecalculateApmeView(McpIntelDispatchView):
    def post(self, request):
        return _delegate_post(RecalculateAttackPathsAPIView, request)


class McpStartWorkflowView(McpIntelDispatchView):
    def post(self, request):
        slug = request.data.get('workflow_slug')
        if not slug:
            return Response({'error': 'workflow_slug is required'}, status=400)
        return _delegate_post(StartWorkflowView, request, workflow_slug=slug)
