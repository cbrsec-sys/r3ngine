import re

PATH_TOOLS = (
    (re.compile(r'^/api/mcp/sessions/?$'), {'POST': 'session_open', 'GET': 'session_list'}),
    (re.compile(r'^/api/mcp/sessions/[^/]+/end/?$'), {'POST': 'session_end'}),
    (re.compile(r'^/api/mcp/projects/?$'), {'GET': 'r3ngine_list_projects'}),
    (re.compile(r'^/api/mcp/targets/\d+/?$'), {'GET': 'r3ngine_get_target'}),
    (re.compile(r'^/api/mcp/targets/?$'), {'GET': 'r3ngine_list_targets'}),
    (re.compile(r'^/api/mcp/scans/start/?$'), {'POST': 'r3ngine_start_scan'}),
    (re.compile(r'^/api/mcp/scans/pause/?$'), {'POST': 'r3ngine_pause_scan'}),
    (re.compile(r'^/api/mcp/scans/resume/?$'), {'POST': 'r3ngine_resume_scan'}),
    (re.compile(r'^/api/mcp/scans/stop/?$'), {'POST': 'r3ngine_stop_scan'}),
    (re.compile(r'^/api/mcp/scans/\d+/?$'), {'GET': 'r3ngine_get_scan'}),
    (re.compile(r'^/api/mcp/scans/?$'), {'GET': 'r3ngine_list_scans'}),
    (re.compile(r'^/api/mcp/scan-status/?$'), {'GET': 'r3ngine_get_scan_status'}),
    (re.compile(r'^/api/mcp/subscans/start/?$'), {'POST': 'r3ngine_start_subscan'}),
    (re.compile(r'^/api/mcp/subscans/?$'), {'GET': 'r3ngine_list_subscans'}),
    (re.compile(r'^/api/mcp/subdomains/?$'), {'GET': 'r3ngine_list_subdomains'}),
    (re.compile(r'^/api/mcp/endpoints/?$'), {'GET': 'r3ngine_list_endpoints'}),
    (re.compile(r'^/api/mcp/vulnerabilities/?$'), {'GET': 'r3ngine_list_vulnerabilities'}),
    (re.compile(r'^/api/mcp/exposures/?$'), {'GET': 'r3ngine_list_exposures'}),
    (re.compile(r'^/api/mcp/emails/?$'), {'GET': 'r3ngine_list_emails'}),
    (re.compile(r'^/api/mcp/employees/?$'), {'GET': 'r3ngine_list_employees'}),
    (re.compile(r'^/api/mcp/search/?$'), {'GET': 'r3ngine_search'}),
    (re.compile(r'^/api/mcp/dashboard/?$'), {'GET': 'r3ngine_get_dashboard'}),
    (re.compile(r'^/api/mcp/attack-paths/?$'), {'GET': 'r3ngine_get_attack_paths'}),
    (re.compile(r'^/api/mcp/engines/?$'), {'GET': 'r3ngine_list_engines'}),
    (re.compile(r'^/api/mcp/health/?$'), {'GET': 'r3ngine_get_system_health'}),
    (re.compile(r'^/api/mcp/tasks/retry/?$'), {'POST': 'r3ngine_retry_task'}),
    (re.compile(r'^/api/mcp/email-discovery/start/?$'), {'POST': 'r3ngine_start_email_discovery'}),
    (re.compile(r'^/api/mcp/email-discovery/stop/?$'), {'POST': 'r3ngine_stop_email_discovery'}),
    (re.compile(r'^/api/mcp/employee-intel/start/?$'), {'POST': 'r3ngine_start_employee_intel'}),
    (re.compile(r'^/api/mcp/employee-intel/stop/?$'), {'POST': 'r3ngine_stop_employee_intel'}),
    (re.compile(r'^/api/mcp/apme/trigger/?$'), {'POST': 'r3ngine_trigger_apme'}),
    (re.compile(r'^/api/mcp/apme/recalculate/?$'), {'POST': 'r3ngine_recalculate_apme'}),
    (re.compile(r'^/api/mcp/workflows/start/?$'), {'POST': 'r3ngine_start_workflow'}),
)


def tool_name_for(method: str, path: str) -> str:
    method = method.upper()
    for pattern, methods in PATH_TOOLS:
        if pattern.match(path):
            return methods.get(method, '')
    return ''
