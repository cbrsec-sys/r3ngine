from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rolepermissions.checkers import has_role

from mcp.authentication import McpApiKeyAuthentication
from mcp.models import McpAuditEvent, McpSession


def _is_admin(user):
    return bool(user and (user.is_superuser or has_role(user, 'sys_admin')))


def _serialize_session(row):
    return {
        'id': str(row.id),
        'session_id': str(row.id),
        'key_id': row.key_id,
        'key_name': row.key.name,
        'key_prefix': row.key.prefix,
        'user_id': row.user_id,
        'username': row.user.username,
        'transport': row.transport,
        'client_name': row.client_name,
        'client_version': row.client_version,
        'user_agent': row.user_agent,
        'source_ip': row.source_ip,
        'connected_at': row.connected_at.isoformat() if row.connected_at else None,
        'last_seen_at': row.last_seen_at.isoformat() if row.last_seen_at else None,
        'revoked_at': row.revoked_at.isoformat() if row.revoked_at else None,
        'ended_at': row.ended_at.isoformat() if row.ended_at else None,
        'connected': row.is_connected(),
        'status': (
            'revoked' if row.revoked_at else
            'ended' if row.ended_at else
            'connected' if row.is_connected() else
            'idle'
        ),
    }


def _owned_or_admin_session(request, pk):
    session = get_object_or_404(McpSession, pk=pk)
    if session.user_id != request.user.id and not _is_admin(request.user):
        return None
    return session


class McpSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_authenticators(self):
        if getattr(self, 'request', None) is not None and self.request.method == 'POST':
            return [McpApiKeyAuthentication()]
        return [JWTAuthentication(), SessionAuthentication()]

    def get(self, request):
        qs = McpSession.objects.select_related('key', 'user').order_by('-connected_at')
        if not (request.query_params.get('all') == '1' and _is_admin(request.user)):
            qs = qs.filter(user=request.user)
        if request.query_params.get('status') == 'connected':
            cutoff = timezone.now() - timedelta(seconds=McpSession.CONNECTED_WINDOW_SECONDS)
            qs = qs.filter(
                revoked_at__isnull=True,
                ended_at__isnull=True,
                last_seen_at__gte=cutoff,
            )
        items = [_serialize_session(row) for row in qs]
        return Response({'items': items, 'count': len(items)})

    def post(self, request):
        transport = request.data.get('transport') or 'stdio'
        if transport not in ('stdio', 'http'):
            return Response(
                {'error': 'transport must be stdio or http'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        key = getattr(request, 'mcp_key', None)
        if key is None:
            return Response({'error': 'MCP API key required'}, status=status.HTTP_401_UNAUTHORIZED)
        session = McpSession.objects.create(
            key=key,
            user=request.user,
            transport=transport,
            client_name=request.data.get('client_name') or '',
            client_version=request.data.get('client_version') or '',
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
            source_ip=request.META.get('REMOTE_ADDR'),
        )
        McpAuditEvent.objects.create(
            session=session,
            key=key,
            user=request.user,
            tool_name='session_open',
            method='POST',
            path='/api/mcp/sessions/',
            status_code=201,
            duration_ms=0,
            request_body={'transport': transport, 'client_name': session.client_name},
            response_body={'session_id': str(session.id)},
        )
        return Response({'session_id': str(session.id)}, status=status.HTTP_201_CREATED)


class McpSessionHeartbeatView(APIView):
    authentication_classes = [McpApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        key = getattr(request, 'mcp_key', None)
        session = getattr(request, 'mcp_session', None)
        if key is None:
            return Response({'error': 'MCP API key required'}, status=status.HTTP_401_UNAUTHORIZED)
        if session is None or str(session.id) != str(pk):
            return Response(
                {'error': 'MCP session invalid or revoked. Reconnect or use a new session; the API key may still be valid.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        session.last_seen_at = timezone.now()
        session.save(update_fields=['last_seen_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class McpSessionEndView(APIView):
    authentication_classes = [McpApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        session = getattr(request, 'mcp_session', None)
        if session is None or str(session.id) != str(pk):
            return Response(
                {'error': 'MCP session invalid or revoked. Reconnect or use a new session; the API key may still be valid.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        session.ended_at = timezone.now()
        session.save(update_fields=['ended_at'])
        McpAuditEvent.objects.create(
            session=session,
            key=session.key,
            user=request.user,
            tool_name='session_end',
            method='POST',
            path=request.path,
            status_code=200,
            duration_ms=0,
            request_body={},
            response_body={'status': 'ended'},
        )
        return Response({'status': 'ended'})


class McpSessionRevokeView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        session = _owned_or_admin_session(request, pk)
        if session is None:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        session.revoked_at = timezone.now()
        session.save(update_fields=['revoked_at'])
        return Response(_serialize_session(session))
