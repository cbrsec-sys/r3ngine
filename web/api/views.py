import re
import socket
import logging
import threading
import requests
import validators
from django.conf import settings

from ipaddress import IPv4Network
from django.db.models import CharField, Count, F, Q, Value
from django.utils import timezone
from packaging import version
from django.template.defaultfilters import slugify
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer
from django.http import FileResponse, Http404
import mimetypes
import os


from django.shortcuts import get_object_or_404
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_204_NO_CONTENT, HTTP_202_ACCEPTED
from rest_framework.decorators import action
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

from dashboard.models import *
from recon_note.models import *
from reNgine.common_func import *
from reNgine.utils.database import *
from reNgine.definitions import (
	ABORTED_TASK,
	RUNNING_TASK,
	SUCCESS_TASK,
	PERM_MODIFY_TARGETS,
	PERM_MODIFY_SCAN_CONFIGURATIONS,
	PERM_MODIFY_WORDLISTS,
	PERM_INITATE_SCANS_SUBSCANS,
	PERM_MODIFY_SCAN_REPORT
)
from reNgine.tasks import *
from reNgine.llm import *
from reNgine.utilities import is_safe_path
from scanEngine.models import *
from startScan.models import *
from startScan.models import EndPoint
from targetApp.models import *
from api.shared_api_tasks import import_hackerone_programs_task, sync_bookmarked_programs_task
from api.permissions import *
from api.serializers import *
from reNgine.utils.graph import Neo4jManager


logger = logging.getLogger(__name__)


class ToggleBugBountyModeView(APIView):
	permission_classes = [IsAuthenticated]
	"""
		This class manages the user bug bounty mode
	"""
	def post(self, request, *args, **kwargs):
		user_preferences = get_object_or_404(UserPreferences, user=request.user)
		user_preferences.bug_bounty_mode = not user_preferences.bug_bounty_mode
		user_preferences.save()
		return Response({
			'bug_bounty_mode': user_preferences.bug_bounty_mode
		}, status=status.HTTP_200_OK)


class UpdateThemeView(APIView):
	permission_classes = [IsAuthenticated]
	"""
		This class manages the user theme and intensity
	"""
	def post(self, request, *args, **kwargs):
		user_preferences = get_object_or_404(UserPreferences, user=request.user)
		ui_version = request.data.get('ui_version')
		v3_intensity = request.data.get('v3_intensity')
		if ui_version:
			user_preferences.ui_version = ui_version
		if v3_intensity:
			user_preferences.v3_intensity = v3_intensity
		user_preferences.save()
		return Response({
			'status': True,
			'ui_version': user_preferences.ui_version,
			'v3_intensity': user_preferences.v3_intensity
		}, status=status.HTTP_200_OK)


class SOCSettingsViewSet(viewsets.ModelViewSet):
	"""ViewSet for managing global SOC configuration."""
	permission_classes = [IsAuditor]
	serializer_class = SOCConfigurationSerializer
	queryset = SOCConfiguration.objects.all()

	def get_queryset(self):
		return SOCConfiguration.objects.all()

	def list(self, request, *args, **kwargs):
		# Ensure at least one config exists
		config, created = SOCConfiguration.objects.get_or_create(id=1)
		serializer = self.get_serializer(config)
		return Response(serializer.data)

	@action(detail=False, methods=['post'])
	def toggle_streaming(self, request):
		config, created = SOCConfiguration.objects.get_or_create(id=1)
		config.enable_live_log_streaming = not config.enable_live_log_streaming
		config.save()
		return Response({
			'enable_live_log_streaming': config.enable_live_log_streaming
		}, status=status.HTTP_200_OK)


class HackerOneProgramViewSet(viewsets.ViewSet):
	permission_classes = [IsPenetrationTester]
	"""
		This class manages the HackerOne Program model, 
		provides basic fetching of programs and caching
	"""
	CACHE_KEY = 'hackerone_programs'
	CACHE_TIMEOUT = 60 * 30 # 30 minutes
	PROGRAM_CACHE_KEY = 'hackerone_program_{}'

	API_BASE = 'https://api.hackerone.com/v1/hackers'

	ALLOWED_ASSET_TYPES = ["WILDCARD", "DOMAIN", "IP_ADDRESS", "CIDR", "URL"]

	def list(self, request):
		try:
			sort_by = request.query_params.get('sort_by', 'age')
			sort_order = request.query_params.get('sort_order', 'desc')

			programs = self.get_cached_programs()

			if sort_by == 'name':
				programs = sorted(programs, key=lambda x: x['attributes']['name'].lower(), 
						reverse=(sort_order.lower() == 'desc'))
			elif sort_by == 'reports':
				programs = sorted(programs, key=lambda x: x['attributes'].get('number_of_reports_for_user', 0), 
						reverse=(sort_order.lower() == 'desc'))
			elif sort_by == 'age':
				programs = sorted(programs, 
					key=lambda x: datetime.strptime(x['attributes'].get('started_accepting_at', '1970-01-01T00:00:00.000Z'), '%Y-%m-%dT%H:%M:%S.%fZ'), 
					reverse=(sort_order.lower() == 'desc')
				)

			serializer = HackerOneProgramSerializer(programs, many=True)
			return Response(serializer.data)
		except Exception as e:
			return self.handle_exception(e)
	
	def get_api_credentials(self):
		try:
			api_key = HackerOneAPIKey.objects.first()
			if not api_key:
				raise ObjectDoesNotExist("HackerOne API credentials not found")
			return api_key.username, api_key.key
		except ObjectDoesNotExist:
			raise Exception("HackerOne API credentials not configured")

	@action(detail=False, methods=['get'])
	def bookmarked_programs(self, request):
		try:
			# do not cache bookmarked programs due to the user specific nature
			programs = self.fetch_programs_from_hackerone()
			bookmarked = [p for p in programs if p['attributes']['bookmarked']]
			serializer = HackerOneProgramSerializer(bookmarked, many=True)
			return Response(serializer.data)
		except Exception as e:
			return self.handle_exception(e)
	
	@action(detail=False, methods=['get'])
	def bounty_programs(self, request):
		try:
			programs = self.get_cached_programs()
			bounty_programs = [p for p in programs if p['attributes']['offers_bounties']]
			serializer = HackerOneProgramSerializer(bounty_programs, many=True)
			return Response(serializer.data)
		except Exception as e:
			return self.handle_exception(e)

	def get_cached_programs(self):
		programs = cache.get(self.CACHE_KEY)
		if programs is None:
			programs = self.fetch_programs_from_hackerone()
			cache.set(self.CACHE_KEY, programs, self.CACHE_TIMEOUT)
		return programs

	def fetch_programs_from_hackerone(self):
		url = f'{self.API_BASE}/programs?page[size]=100'
		headers = {'Accept': 'application/json'}
		all_programs = []
		try:
			username, api_key = self.get_api_credentials()
		except Exception as e:
			raise Exception("API credentials error: " + str(e))

		while url:
			response = requests.get(
				url,
				headers=headers,
				auth=(username, api_key)
			)

			if response.status_code == 401:
				raise Exception("Invalid API credentials")
			elif response.status_code != 200:
				raise Exception(f"HackerOne API request failed with status code {response.status_code}")

			data = response.json()
			all_programs.extend(data['data'])
			
			url = data['links'].get('next')

		return all_programs

	@action(detail=False, methods=['post'])
	def refresh_cache(self, request):
		try:
			programs = self.fetch_programs_from_hackerone()
			cache.set(self.CACHE_KEY, programs, self.CACHE_TIMEOUT)
			return Response({"status": "Cache refreshed successfully"})
		except Exception as e:
			return self.handle_exception(e)
	
	@action(detail=True, methods=['get'])
	def program_details(self, request, pk=None):
		try:
			program_handle = pk
			cache_key = self.PROGRAM_CACHE_KEY.format(program_handle)
			program_details = cache.get(cache_key)

			if program_details is None:
				program_details = self.fetch_program_details_from_hackerone(program_handle)
				if program_details:
					cache.set(cache_key, program_details, self.CACHE_TIMEOUT)

			if program_details:
				filtered_scopes = [
					scope for scope in program_details.get('relationships', {}).get('structured_scopes', {}).get('data', [])
					if scope.get('attributes', {}).get('asset_type') in self.ALLOWED_ASSET_TYPES
				]

				program_details['relationships']['structured_scopes']['data'] = filtered_scopes

				return Response(program_details)
			else:
				return Response({"error": "Program not found"}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			return self.handle_exception(e)

	def fetch_program_details_from_hackerone(self, program_handle):
		url = f'{self.API_BASE}/programs/{program_handle}'
		headers = {'Accept': 'application/json'}
		try:
			username, api_key = self.get_api_credentials()
		except Exception as e:
			raise Exception("API credentials error: " + str(e))

		response = requests.get(
			url,
			headers=headers,
			auth=(username, api_key)
		)

		if response.status_code == 401:
			raise Exception("Invalid API credentials")
		elif response.status_code == 200:
			return response.json()
		else:
			return None
		
	@action(detail=False, methods=['post'])
	def import_programs(self, request):
		try:
			project_slug = request.query_params.get('project_slug')
			if not project_slug:
				return Response({"error": "Project slug is required"}, status=status.HTTP_400_BAD_REQUEST)
			handles = request.data.get('handles', [])

			if not handles:
				return Response({"error": "No program handles provided"}, status=status.HTTP_400_BAD_REQUEST)

			threading.Thread(
				target=import_hackerone_programs_task,
				args=(handles, project_slug),
				daemon=True
			).start()

			create_inappnotification(
				title="HackerOne Program Import Started",
				description=f"Import process for {len(handles)} program(s) has begun.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				project_slug=project_slug,
				icon="mdi-download",
				status='info'
			)

			return Response({"message": f"Import process for {len(handles)} program(s) has begun."}, status=status.HTTP_202_ACCEPTED)
		except Exception as e:
			return self.handle_exception(e)
	
	@action(detail=False, methods=['get'])
	def sync_bookmarked(self, request):
		try:
			project_slug = request.query_params.get('project_slug')
			if not project_slug:
				return Response({"error": "Project slug is required"}, status=status.HTTP_400_BAD_REQUEST)

			threading.Thread(
				target=sync_bookmarked_programs_task,
				args=(project_slug,),
				daemon=True
			).start()

			create_inappnotification(
				title="HackerOne Bookmarked Programs Sync Started",
				description="Sync process for bookmarked programs has begun.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				project_slug=project_slug,
				icon="mdi-sync",
				status='info'
			)

			return Response({"message": "Sync process for bookmarked programs has begun."}, status=status.HTTP_202_ACCEPTED)
		except Exception as e:
			return self.handle_exception(e)

	def handle_exception(self, exc):
		if isinstance(exc, ObjectDoesNotExist):
			return Response({"error": "HackerOne API credentials not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		elif str(exc) == "Invalid API credentials":
			return Response({"error": "Invalid HackerOne API credentials"}, status=status.HTTP_401_UNAUTHORIZED)
		else:
			return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InAppNotificationManagerViewSet(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated]
	"""
		This class manages the notification model, provided CRUD operation on notif model
		such as read notif, clear all, fetch all notifications etc
	"""
	serializer_class = InAppNotificationSerializer
	pagination_class = None

	def get_queryset(self):
		# we will see later if user based notif is needed
		# return InAppNotification.objects.filter(user=self.request.user)
		project_slug = self.request.query_params.get('project_slug')
		queryset = InAppNotification.objects.all()
		if project_slug:
			queryset = queryset.filter(
				Q(project__slug=project_slug) | Q(notification_type='system')
			)
		return queryset.order_by('-created_at')

	@action(detail=False, methods=['post'])
	def mark_all_read(self, request):
		# marks all notification read
		project_slug = self.request.query_params.get('project_slug')
		queryset = self.get_queryset()

		if project_slug:
			queryset = queryset.filter(
				Q(project__slug=project_slug) | Q(notification_type='system')
			)
		queryset.update(is_read=True)
		return Response(status=HTTP_204_NO_CONTENT)

	@action(detail=True, methods=['post'])
	def mark_read(self, request, pk=None):
		# mark individual notification read when cliked
		notification = self.get_object()
		notification.is_read = True
		notification.save()
		return Response(status=HTTP_204_NO_CONTENT)

	@action(detail=False, methods=['get'])
	def unread_count(self, request):
		# this fetches the count for unread notif mainly for the badge
		project_slug = self.request.query_params.get('project_slug')
		queryset = self.get_queryset()
		if project_slug:
			queryset = queryset.filter(
				Q(project__slug=project_slug) | Q(notification_type='system')
			)
		count = queryset.filter(is_read=False).count()
		return Response({'count': count})

	@action(detail=False, methods=['post'])
	def clear_all(self, request):
		# when clicked on the clear button this must be called to clear all notif
		project_slug = self.request.query_params.get('project_slug')
		queryset = self.get_queryset()
		if project_slug:
			queryset = queryset.filter(
				Q(project__slug=project_slug) | Q(notification_type='system')
			)
		queryset.delete()
		return Response(status=HTTP_204_NO_CONTENT)


class OllamaManager(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		"""
		API to download Ollama Models
		sends a POST request to download the model
		"""
		req = self.request
		model_name = req.query_params.get('model')
		response = {
			'status': False
		}
		try:
			pull_model_api = f'{OLLAMA_INSTANCE}/api/pull'
			_response = requests.post(
				pull_model_api, 
				json={
					'name': model_name,
					'stream': False
				}
			).json()
			if _response.get('error'):
				response['status'] = False
				response['error'] = _response.get('error')
			else:
				response['status'] = True
		except Exception as e:
			response['error'] = str(e)		
		return Response(response)
	
	def delete(self, request):
		req = self.request
		model_name = req.query_params.get('model')
		delete_model_api = f'{OLLAMA_INSTANCE}/api/delete'
		response = {
			'status': False
		}
		try:
			_response = requests.delete(
				delete_model_api, 
				json={
					'name': model_name
				}
			).json()
			if _response.get('error'):
				response['status'] = False
				response['error'] = _response.get('error')
			else:
				response['status'] = True
		except Exception as e:
			response['error'] = str(e)
		return Response(response)
	
	def put(self, request):
		req = self.request
		model_name = req.query_params.get('model')
		# check if model_name is in DEFAULT_GPT_MODELS
		response = {
			'status': False
		}
		use_ollama = True
		if any(model['name'] == model_name for model in DEFAULT_GPT_MODELS):
			use_ollama = False
		try:
			OllamaSettings.objects.update_or_create(
				defaults={
					'selected_model': model_name,
					'use_ollama': use_ollama
				},
				id=1
			)
			response['status'] = True
		except Exception as e:
			response['error'] = str(e)
		return Response(response)


class GPTAttackSuggestion(APIView):
	"""API Endpoint to generate LLM-powered attack surface suggestions for a given subdomain.

	Provides a structured security analysis and potential attack vectors based on target recon data.
	"""
	permission_classes = [IsPenetrationTester]
	
	def get(self, request):
		"""Retrieve or trigger LLM generation of attack surface analysis for a subdomain.

		Args:
			request (Request): Django Rest Framework Request object.
				Requires 'subdomain_id' in GET parameters.

		Returns:
			Response: JSON response with 'status', 'description', and 'subdomain_name' or error details.
		"""
		req = self.request
		subdomain_id = req.query_params.get('subdomain_id')
		if not subdomain_id:
			return Response({
				'status': False,
				'error': 'Missing GET param Subdomain `subdomain_id`'
			}, status=status.HTTP_400_BAD_REQUEST)
		try:
			subdomain = Subdomain.objects.get(id=subdomain_id)
		except Exception as e:
			return Response({
				'status': False,
				'error': 'Subdomain not found with id ' + subdomain_id
			}, status=status.HTTP_404_NOT_FOUND)
		if subdomain.attack_surface:
			return Response({
				'status': True,
				'subdomain_name': subdomain.name,
				'description': subdomain.attack_surface
			})
		ip_addrs = subdomain.ip_addresses.all()
		open_ports_str = ''
		for ip in ip_addrs:
			ports = ip.ports.all()
			for port in ports:
				open_ports_str += f'{port.number}/{port.service_name}, '
		tech_used = ''
		for tech in subdomain.technologies.all():
			tech_used += f'{tech.name}, '
		llm_input = f'''
			Subdomain Name: {subdomain.name}
			Subdomain Page Title: {subdomain.page_title}
			Open Ports: {open_ports_str}
			HTTP Status: {subdomain.http_status}
			Technologies Used: {tech_used}
			Content type: {subdomain.content_type}
			Web Server: {subdomain.webserver}
			Page Content Length: {subdomain.content_length}
		'''
		llm_input = re.sub(r'\t', '', llm_input)
		gpt = LLMAttackSuggestionGenerator(logger)
		response = gpt.get_attack_suggestion(llm_input)
		response['subdomain_name'] = subdomain.name
		if response.get('status'):
			subdomain.attack_surface = response.get('description')
			subdomain.save()
			return Response(response)
		else:
			return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LLMVulnerabilityReportGenerator(APIView):
	"""API Endpoint to generate detailed vulnerability reports using LLMs.

	Triggers a Celery task that queries the LLM config and enrich descriptions/impacts/remediations.
	"""
	permission_classes = [IsPenetrationTester]
	
	def get(self, request):
		"""Enrich vulnerability with LLM generated descriptions and mitigation options.

		Args:
			request (Request): Django Rest Framework Request object.
				Requires vulnerability 'id' in GET parameters.

		Returns:
			Response: JSON response containing description, impact, remediation, and references.
		"""
		req = self.request
		vulnerability_id = req.query_params.get('id')
		if not vulnerability_id:
			return Response({
				'status': False,
				'error': 'Missing GET param Vulnerability `id`'
			}, status=status.HTTP_400_BAD_REQUEST)
		response = llm_vulnerability_description(vulnerability_id)
		if response and response.get('status'):
			return Response(response)
		else:
			return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ProjectViewSet(viewsets.ModelViewSet):
	queryset = Project.objects.all().order_by('-insert_date')
	serializer_class = ProjectSerializer
	permission_classes = [IsAuthenticated]
	renderer_classes = [JSONRenderer]


	@action(detail=True, methods=['post'])
	def delete_project(self, request, pk=None):
		if not request.user.has_perm('dashboard.modify_targets'):
			return Response({'status': False, 'message': 'Permission Denied'}, status=403)
		project = self.get_object()
		project.delete()
		return Response({'status': True})


class CreateProjectApi(APIView):

	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_TARGETS
	renderer_classes = [JSONRenderer]


	def post(self, request):
		req = self.request
		project_name = req.data.get('name')
		if not project_name:
			return Response({'status': False, 'error': 'Project name is required'}, status=HTTP_400_BAD_REQUEST)
		slug = slugify(project_name)
		insert_date = timezone.now()

		try:
			project = Project.objects.create(
				name=project_name,
				slug=slug,
				insert_date =insert_date
			)
			response = {
				'status': True,
				'project_name': project_name
			}
			return Response(response)
		except Exception as e:
			response = {
				'status': False,
				'error': str(e)
			}
			return Response(response, status=HTTP_400_BAD_REQUEST)



class QueryInterestingSubdomains(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		domain_id = req.query_params.get('target_id')

		if scan_id:
			queryset = get_interesting_subdomains(scan_history=scan_id)
		elif domain_id:
			queryset = get_interesting_subdomains(domain_id=domain_id)
		else:
			queryset = get_interesting_subdomains()

		queryset = queryset.distinct('name')

		return Response(InterestingSubdomainSerializer(queryset, many=True).data)


class ListTargetsDatatableViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Domain.objects.all().order_by('-id')
	serializer_class = DomainSerializer

	def get_queryset(self):
		queryset = Domain.objects.all()
		slug = self.request.GET.get('slug', None)
		if slug:
			queryset = queryset.filter(project__slug=slug)
		
		org_id = self.request.GET.get('organization_id', None)
		if org_id:
			queryset = queryset.filter(domains__id=org_id)
			
		return queryset.order_by('-id')

	def filter_queryset(self, qs):
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'id'
			if _order_col == '2':
				order_col = 'name'
			elif _order_col == '4':
				order_col = 'insert_date'
			elif _order_col == '5':
				order_col = 'start_scan_date'
				if _order_direction == 'desc':
					return qs.order_by(F('start_scan_date').desc(nulls_last=True))
				return qs.order_by(F('start_scan_date').asc(nulls_last=True))


			if _order_direction == 'desc':
				order_col = f'-{order_col}'

			qs = qs.filter(
				Q(name__icontains=search_value) |
				Q(description__icontains=search_value) |
				Q(domains__name__icontains=search_value)
			)
			return qs.order_by(order_col)
		return qs



class MonitoringDiscoveryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPenetrationTester]
    queryset = MonitoringDiscovery.objects.all()
    serializer_class = MonitoringDiscoverySerializer

    def get_queryset(self):
        slug = self.request.query_params.get('slug')
        if slug:
            return self.queryset.filter(domain__project__slug=slug).order_by('-discovered_at')
        return self.queryset.order_by('-discovered_at')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        slug = self.request.query_params.get('slug')
        if not slug:
            return Response({'error': 'Slug is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        project = get_object_or_404(Project, slug=slug)
        discoveries = MonitoringDiscovery.objects.filter(domain__project=project)
        
        stats = {
            'total_discoveries': discoveries.count(),
            'subdomain_discoveries': discoveries.filter(discovery_type='subdomain').count(),
            'endpoint_discoveries': discoveries.filter(discovery_type='directory').count(),
            'login_discoveries': discoveries.filter(discovery_type='login').count(),
        }
        return Response(stats)



class OsintStagingViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = OsintStaging.objects.filter(status='pending').order_by('-confidence', '-discovered_date')
	serializer_class = OsintStagingSerializer

	def get_queryset(self):
		queryset = self.queryset
		scan_id = self.request.query_params.get('scan_id')
		target_id = self.request.query_params.get('target_id')
		osint_type = self.request.query_params.get('osint_type')
		status_param = self.request.query_params.get('status')
		
		if scan_id:
			queryset = queryset.filter(scan_history_id=scan_id)
		if target_id:
			queryset = queryset.filter(target_domain_id=target_id)
		if osint_type:
			queryset = queryset.filter(osint_type=osint_type)
		if status_param:
			queryset = OsintStaging.objects.filter(status=status_param) # Allow override to see validated/ignored
		
		# Universal Search for Staging
		search = self.request.query_params.get('search')
		if search:
			queryset = queryset.filter(
				Q(content__icontains=search) |
				Q(source__icontains=search) |
				Q(metadata__icontains=search) |
				Q(osint_type__icontains=search)
			)
			
		return queryset

	@action(detail=False, methods=['post'])
	def bulk_discard(self, request):
		"""Bulk delete staging items."""
		ids = request.data.get('ids', [])
		if not ids:
			return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		
		OsintStaging.objects.filter(id__in=ids).delete()
		return Response({'status': 'success', 'message': f'Deleted {len(ids)} items'})

	@action(detail=False, methods=['post'])
	def bulk_promote(self, request):
		"""Bulk promote staging items to primary tables."""
		from reNgine.tasks import persist_osint_item
		ids = request.data.get('ids', [])
		if not ids:
			return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
		
		items = OsintStaging.objects.filter(id__in=ids)
		count = 0
		for item in items:
			ctx = {
				'scan_history_id': item.scan_history.id,
				'domain_id': item.target_domain.id
			}
			persist_osint_item(
				scan_history=item.scan_history,
				domain=item.target_domain,
				osint_type=item.osint_type,
				e_data=item.content,
				confidence=item.confidence,
				source_data=item.metadata.get('source_data'),
				event_type=item.metadata.get('sf_type'),
				ctx=ctx
			)
			item.status = 'validated'
			item.save()
			count += 1
			
		return Response({'status': 'success', 'message': f'Promoted {count} items'})

	@action(detail=True, methods=['post'])
	def promote(self, request, pk=None):
		"""Individual promote."""
		from reNgine.tasks import persist_osint_item
		item = self.get_object()
		ctx = {
			'scan_history_id': item.scan_history.id,
			'domain_id': item.target_domain.id
		}
		persist_osint_item(
			scan_history=item.scan_history,
			domain=item.target_domain,
			osint_type=item.osint_type,
			e_data=item.content,
			confidence=item.confidence,
			source_data=item.metadata.get('source_data'),
			event_type=item.metadata.get('sf_type'),
			ctx=ctx
		)
		item.status = 'validated'
		item.save()
		return Response({'status': 'success'})

	@action(detail=True, methods=['post'])
	def discard(self, request, pk=None):
		"""Individual discard."""
		item = self.get_object()
		item.delete()
		return Response({'status': 'success'})



class WafDetector(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		url= req.query_params.get('url')
		response = {}
		response['status'] = False

		# validate url as a first step to avoid command injection
		if not (validators.url(url) or validators.domain(url)):
			response['message'] = 'Invalid Domain/URL provided!'
			return Response(response)
		
		wafw00f_command = f'wafw00f {url}'
		_, output = run_command.run(wafw00f_command, shell=True, remove_ansi_sequence=True)
		regex = r"behind (.*?) WAF"
		group = re.search(regex, output)
		if group:
			response['status'] = True
			response['results'] = group.group(1)
		else:
			response['message'] = 'Could not detect any WAF!'

		return Response(response)


class SearchHistoryView(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request

		response = {}
		response['status'] = False

		scan_history = SearchHistory.objects.all().order_by('-id')[:5]

		if scan_history:
			response['status'] = True
			response['results'] = SearchHistorySerializer(scan_history, many=True).data

		return Response(response)


class UniversalSearch(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		query = req.query_params.get('query')

		response = {}
		response['status'] = False

		if not query:
			response['message'] = 'No query parameter provided!'
			return Response(response)

		response['results'] = {}

		# search history to be saved
		SearchHistory.objects.get_or_create(
			query=query
		)

		# lookup query in subdomain
		subdomain = Subdomain.objects.filter(
			Q(name__icontains=query) |
			Q(cname__icontains=query) |
			Q(page_title__icontains=query) |
			Q(http_url__icontains=query)
		).distinct('name').prefetch_related(
			'screenshots', 'technologies', 'ip_addresses', 'ip_addresses__ports'
		)
		subdomain_data = SubdomainSerializer(subdomain, many=True).data
		response['results']['subdomains'] = subdomain_data

		endpoint = EndPoint.objects.filter(
			Q(http_url__icontains=query) |
			Q(page_title__icontains=query) |
			Q(parameters__name__icontains=query)
		).distinct('http_url')
		endpoint_data = EndpointSerializer(endpoint, many=True).data
		response['results']['endpoints'] = endpoint_data

		vulnerability = Vulnerability.objects.filter(
			Q(http_url__icontains=query) |
			Q(name__icontains=query) |
			Q(description__icontains=query)
		).distinct()
		vulnerability_data = VulnerabilitySerializer(vulnerability, many=True).data
		response['results']['vulnerabilities'] = vulnerability_data

		response['results']['others'] = {}

		if subdomain_data or endpoint_data or vulnerability_data:
			response['status'] = True

		return Response(response)


class FetchMostCommonVulnerability(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		req = self.request
		data = req.data

		try:
			limit = data.get('limit', 20)
			project_slug = data.get('slug')
			scan_history_id = data.get('scan_history_id')
			target_id = data.get('target_id')
			is_ignore_info = data.get('ignore_info', False)

			response = {}
			response['status'] = False

			if project_slug:
				project = Project.objects.get(slug=project_slug)
				vulnerabilities = Vulnerability.objects.filter(target_domain__project=project)
			else:
				vulnerabilities = Vulnerability.objects.all()


			if scan_history_id:
				vuln_query = (
					vulnerabilities
					.filter(scan_history__id=scan_history_id)
					.values("name", "severity")
				)
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query
						.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)

			elif target_id:
				vuln_query = vulnerabilities.filter(target_domain__id=target_id).values("name", "severity")
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query
						.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)

			else:
				vuln_query = vulnerabilities.values("name", "severity")
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)


			most_common_vulnerabilities = [vuln for vuln in most_common_vulnerabilities]

			if most_common_vulnerabilities:
				response['status'] = True
				response['result'] = most_common_vulnerabilities
		except Exception as e:
			print(str(e))
			response = {}

		return Response(response)


class FetchMostVulnerable(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		req = self.request
		data = req.data

		project_slug = data.get('slug')
		scan_history_id = data.get('scan_history_id')
		target_id = data.get('target_id')
		limit = data.get('limit', 20)
		is_ignore_info = data.get('ignore_info', False)

		response = {}
		response['status'] = False

		if project_slug:
			project = Project.objects.get(slug=project_slug)
			subdomains = Subdomain.objects.filter(target_domain__project=project)
			domains = Domain.objects.filter(project=project)
		else:
			subdomains = Subdomain.objects.all()
			domains = Domain.objects.all()

		if scan_history_id:
			subdomain_query = subdomains.filter(scan_history__id=scan_history_id)
			if is_ignore_info:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(
						vuln_count=Count('vulnerability__name', filter=~Q(vulnerability__severity=0))
					)
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

				if most_vulnerable_subdomains:
					response['status'] = True
					response['result'] = (
						SubdomainSerializer(
							most_vulnerable_subdomains,
							many=True)
						.data
					)

		elif target_id:
			subdomain_query = subdomains.filter(target_domain__id=target_id)
			if is_ignore_info:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name', filter=~Q(vulnerability__severity=0)))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

			if most_vulnerable_subdomains:
				response['status'] = True
				response['result'] = (
					SubdomainSerializer(
						most_vulnerable_subdomains,
						many=True)
					.data
				)
		else:
			if is_ignore_info:
				most_vulnerable_targets = (
					domains
					.annotate(vuln_count=Count('subdomain__vulnerability__name', filter=~Q(subdomain__vulnerability__severity=0)))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_targets = (
					domains
					.annotate(vuln_count=Count('subdomain__vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

			if most_vulnerable_targets:
				response['status'] = True
				response['result'] = (
					DomainSerializer(
						most_vulnerable_targets,
						many=True)
					.data
				)

		return Response(response)


class CVEDetails(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request

		cve_id = req.query_params.get('cve_id')

		if not cve_id:
			return Response({'status': False, 'message': 'CVE ID not provided'})

		response = requests.get('https://cve.circl.lu/api/cve/' + cve_id)

		if response.status_code != 200:
			return  Response({'status': False, 'message': 'Unknown Error Occured!'})

		if not response.json():
			return  Response({'status': False, 'message': 'CVE ID does not exists.'})

		return Response({'status': True, 'result': response.json()})


class AddReconNote(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		req = self.request
		data = req.data

		subdomain_id = data.get('subdomain_id')
		title = data.get('title')
		description = data.get('description')
		project = data.get('project')

		try:
			project = Project.objects.get(slug=project)
			note = TodoNote()
			note.title = title
			note.description = description

			# get scan history for subdomain_id
			if subdomain_id:
				subdomain = Subdomain.objects.get(id=subdomain_id)
				note.subdomain = subdomain

				# also get scan history
				scan_history_id = subdomain.scan_history.id
				scan_history = ScanHistory.objects.get(id=scan_history_id)
				note.scan_history = scan_history

			note.project = project
			note.save()
			response = {'status': True}
		except Exception as e:
			response = {'status': False, 'message': str(e)}

		return Response(response)


class ToggleSubdomainImportantStatus(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		req = self.request
		data = req.data

		subdomain_id = data.get('subdomain_id')

		response = {'status': False, 'message': 'No subdomain_id provided'}

		name = Subdomain.objects.get(id=subdomain_id)
		name.is_important = not name.is_important
		name.save()

		response = {'status': True}

		return Response(response)


class AddTarget(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_TARGETS

	def post(self, request):
		data = request.data
		h1_team_handle = data.get('h1_team_handle')
		description = data.get('description')
		domain_name_input = data.get('domain_name', '')
		organization_name = data.get('organization')
		slug = data.get('slug')

		# Monitoring settings
		is_monitored = data.get('is_monitored', False)
		monitor_frequency = data.get('monitor_frequency', 'daily')
		monitor_scan_scope = data.get('monitor_scan_scope', 'none')
		monitor_engine_id = data.get('monitor_engine_id')

		# Advanced scan configuration
		starting_point_path = data.get('starting_point_path')
		excluded_paths = data.get('excluded_paths', [])

		# Support for multiple targets separated by newline.
		# The user wants to add multiple domains/IPs to a target when creating a new target.
		# This should create them as a SINGLE entry with secondary domains and in-scope IPs grouped.
		target_names = [t.strip().replace('*', '') for t in domain_name_input.split('\n') if t.strip()]
		
		# Clean up targets (remove leading dots)
		cleaned_targets = []
		for name in target_names:
			if name.startswith('.'):
				name = name[1:]
			cleaned_targets.append(name)

		if not cleaned_targets:
			return Response({'status': False, 'message': 'No valid targets provided'}, status=status.HTTP_400_BAD_REQUEST)

		# The first entry becomes the main target name
		primary_target = cleaned_targets[0]
		secondary_domains_list = []
		in_scope_ips_list = []

		# Loop through subsequent items and classify them as In-Scope IPs or Secondary Domains
		# IP checks are done via simple validator logic or typical patterns (checking for digits, colons, CIDRs)
		import ipaddress
		for extra in cleaned_targets[1:]:
			# Check if it's an IP, CIDR block, or IP range
			is_ip_or_range = False
			try:
				# Check if CIDR or single IP
				if '/' in extra:
					ipaddress.ip_network(extra, strict=False)
					is_ip_or_range = True
				else:
					ipaddress.ip_address(extra)
					is_ip_or_range = True
			except ValueError:
				# Fallback regex check for standard IP/CIDR/range representations if parsing fails
				if re.match(r'^[\d\.\:\/\-]+$', extra):
					is_ip_or_range = True

			if is_ip_or_range:
				in_scope_ips_list.append(extra)
			else:
				secondary_domains_list.append(extra)

		# Format manually parsed lists as newline-separated text strings
		in_scope_ips_str = '\n'.join(in_scope_ips_list) if in_scope_ips_list else None
		secondary_domains_str = '\n'.join(secondary_domains_list) if secondary_domains_list else None

		targets_to_import = [{'name': primary_target, 'description': description}]

		status_import = bulk_import_targets(
			targets=targets_to_import,
			organization_name=organization_name,
			h1_team_handle=h1_team_handle,
			project_slug=slug,
			is_monitored=is_monitored,
			monitor_frequency=monitor_frequency,
			monitor_engine_id=monitor_engine_id,
			monitor_scan_scope=monitor_scan_scope,
			starting_point_path=starting_point_path,
			excluded_paths=excluded_paths,
			in_scope_ips=in_scope_ips_str,
			secondary_domains=secondary_domains_str
		)

		if status_import:
			msg = f'Target {primary_target} successfully created as a single entry'
			if secondary_domains_list or in_scope_ips_list:
				msg += f' with {len(secondary_domains_list)} secondary domains and {len(in_scope_ips_list)} in-scope IPs.'
			else:
				msg += '.'
			return Response({
				'status': True,
				'message': msg,
			})
		return Response({
			'status': False,
			'message': 'Failed to add target! It may already exist or is invalid.'
		})


class FetchSubscanResults(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		# data = req.data
		subscan_id = req.query_params.get('subscan_id')
		subscan = SubScan.objects.filter(id=subscan_id)
		if not subscan.exists():
			return Response({
				'status': False,
				'error': f'Subscan {subscan_id} does not exist'
			})

		subscan_data = SubScanResultSerializer(subscan.first(), many=False).data
		task_name = subscan_data['type']
		subscan_results = []

		if task_name == 'port_scan':
			ips_in_subscan = IpAddress.objects.filter(ip_subscan_ids__in=subscan)
			subscan_results = IpSerializer(ips_in_subscan, many=True).data

		elif task_name == 'vulnerability_scan':
			vulns_in_subscan = Vulnerability.objects.filter(vuln_subscan_ids__in=subscan)
			subscan_results = VulnerabilitySerializer(vulns_in_subscan, many=True).data

		elif task_name == 'fetch_url':
			endpoints_in_subscan = EndPoint.objects.filter(endpoint_subscan_ids__in=subscan)
			subscan_results = EndpointSerializer(endpoints_in_subscan, many=True).data

		elif task_name == 'dir_file_fuzz':
			dirs_in_subscan = DirectoryScan.objects.filter(dir_subscan_ids__in=subscan)
			subscan_results = DirectoryScanSerializer(dirs_in_subscan, many=True).data

		elif task_name == 'subdomain_discovery':
			subdomains_in_subscan = Subdomain.objects.filter(subdomain_subscan_ids__in=subscan)
			subscan_results = SubdomainSerializer(subdomains_in_subscan, many=True).data

		elif task_name == 'screenshot':
			subdomains_in_subscan = Subdomain.objects.filter(subdomain_subscan_ids__in=subscan, screenshot_path__isnull=False)
			subscan_results = SubdomainSerializer(subdomains_in_subscan, many=True).data

		logger.info(subscan_data)
		logger.info(subscan_results)

		return Response({'subscan': subscan_data, 'result': subscan_results})


class ListSubScans(APIView):
	permission_classes = [IsAuditor]
	def post(self, request):
		req = self.request
		data = req.data
		subdomain_id = data.get('subdomain_id', None)
		scan_history = data.get('scan_history_id', None)
		domain_id = data.get('domain_id', None)
		response = {}
		response['status'] = False

		if subdomain_id:
			subscans = (
				SubScan.objects
				.filter(subdomain__id=subdomain_id)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		elif scan_history:
			subscans = (
				SubScan.objects
				.filter(scan_history__id=scan_history)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		elif domain_id:
			scan_history = ScanHistory.objects.filter(domain__id=domain_id)
			subscans = (
				SubScan.objects
				.filter(scan_history__in=scan_history)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		return Response(response)


class DeleteMultipleRows(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_TARGETS

	def post(self, request):
		req = self.request
		data = req.data

		try:
			if data['type'] == 'subscan':
				for row in data['rows']:
					SubScan.objects.get(id=row).delete()
			elif data['type'] == 'organization':
				for row in data['rows']:
					Organization.objects.get(id=row).delete()
			elif data['type'] == 'scan_engine':
				for row in data['rows']:
					EngineType.objects.get(id=row).delete()
			elif data['type'] == 'wordlist':
				for row in data['rows']:
					Wordlist.objects.get(id=row).delete()
			elif data['type'] == 'target':
				for row in data['rows']:
					Domain.objects.get(id=row).delete()
			elif data['type'] == 'scan_history':
				for row in data['rows']:
					ScanHistory.objects.get(id=row).delete()
			response = True
		except Exception as e:
			response = False

		return Response({'status': response})


class CreateEngine(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def post(self, request):
		data = request.data
		name = data.get('engine_name')
		yaml_configuration = data.get('yaml_configuration')

		if not name or not yaml_configuration:
			return Response({
				'status': False,
				'message': 'Name and YAML configuration are required'
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			EngineType.objects.create(
				engine_name=name,
				yaml_configuration=yaml_configuration
			)
			return Response({
				'status': True,
				'message': 'Engine created successfully'
			})
		except Exception as e:
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class UploadWordlist(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_WORDLISTS

	def post(self, request):
		data = request.data
		name = data.get('name')
		short_name = data.get('short_name')
		upload_file = request.FILES.get('upload_file')

		if not name or not short_name or not upload_file:
			return Response({
				'status': False,
				'message': 'Name, short name and file are required'
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			wordlist_content = upload_file.read().decode('UTF-8', "ignore")
			wordlist_dir = '/usr/src/wordlist/'
			if not os.path.exists(wordlist_dir):
				os.makedirs(wordlist_dir)

			file_path = os.path.join(wordlist_dir, f"{short_name}.txt")
			with open(file_path, 'w') as f:
				f.write(wordlist_content)

			Wordlist.objects.create(
				name=name,
				short_name=short_name,
				count=wordlist_content.count('\n')
			)
			return Response({
				'status': True,
				'message': 'Wordlist uploaded successfully'
			})
		except Exception as e:
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class GetWordlistContent(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_WORDLISTS

	def get(self, request):
		wordlist_id = request.query_params.get('wordlist_id')
		if not wordlist_id:
			return Response({
				'status': False,
				'message': 'Wordlist ID is required'
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			wordlist = Wordlist.objects.get(id=wordlist_id)
			file_path = f'/usr/src/wordlist/{wordlist.short_name}.txt'
			if os.path.exists(file_path):
				with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
					# Read first 1000 lines or something to avoid huge responses
					content = "".join([next(f) for _ in range(1000)])
					return Response({
						'status': True,
						'content': content,
						'name': wordlist.name
					})
			return Response({
				'status': False,
				'message': 'File not found'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class GetEngineDetails(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def get(self, request):
		engine_id = request.query_params.get('engine_id')
		if not engine_id:
			return Response({
				'status': False,
				'message': 'Engine ID is required'
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			engine = EngineType.objects.get(id=engine_id)
			return Response({
				'status': True,
				'engine_name': engine.engine_name,
				'yaml_configuration': engine.yaml_configuration
			})
		except Exception as e:
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class UpdateEngine(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def post(self, request):
		data = request.data
		engine_id = data.get('engine_id')
		name = data.get('engine_name')
		yaml_configuration = data.get('yaml_configuration')

		if not engine_id or not name or not yaml_configuration:
			return Response({
				'status': False,
				'message': 'Engine ID, name and YAML configuration are required'
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			engine = EngineType.objects.get(id=engine_id)
			engine.engine_name = name
			engine.yaml_configuration = yaml_configuration
			engine.save()
			return Response({
				'status': True,
				'message': 'Engine updated successfully'
			})
		except Exception as e:
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class StopScan(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_INITATE_SCANS_SUBSCANS

	def post(self, request):
		req = self.request
		data = req.data
		scan_ids = data.get('scan_ids', [])
		subscan_ids = data.get('subscan_ids', [])

		scan_ids = [int(id) for id in scan_ids]
		subscan_ids = [int(id) for id in subscan_ids]

		response = {'status': False}

		def abort_scan(scan):
			from reNgine.temporal_client import TemporalClientProvider
			response = {}
			logger.info(f'Aborting scan History')
			try:
				logger.info(f"Setting scan {scan} status to ABORTED_TASK")
				scan.scan_status = ABORTED_TASK
				scan.stop_scan_date = timezone.now()
				scan.aborted_by = request.user
				scan.save()
				for te in scan.temporal_executions.filter(status="RUNNING"):
					try:
						TemporalClientProvider.cancel_workflow(te.workflow_id)
						te.status = "CANCELLED"
						te.ended_at = timezone.now()
						te.save()
					except Exception as cancel_err:
						logger.warning(f"Temporal cancel failed for {te.workflow_id}: {cancel_err}")

				subscans = SubScan.objects.filter(scan_history=scan, status=RUNNING_TASK)
				for subscan in subscans:
					abort_subscan(subscan)

				tasks = (
					ScanActivity.objects
					.filter(scan_of=scan)
					.filter(status=RUNNING_TASK)
					.order_by('-pk')
				)
				for task in tasks:
					task.status = ABORTED_TASK
					task.time = timezone.now()
					task.save()

				create_scan_activity(
					scan.id,
					"Scan aborted",
					ABORTED_TASK
				)
				response['status'] = True
			except Exception as e:
				logger.error(e)
				response = {'status': False, 'message': str(e)}

			return response

		def abort_subscan(subscan):
			response = {}
			logger.info(f'Aborting subscan')
			try:
				logger.info(f"Setting scan {subscan} status to ABORTED_TASK")
				subscan.status = ABORTED_TASK
				subscan.stop_scan_date = timezone.now()
				subscan.save()
				create_scan_activity(
					subscan.scan_history.id,
					f'Subscan aborted',
					ABORTED_TASK
				)
				response['status'] = True
			except Exception as e:
				logger.error(e)
				response = {'status': False, 'message': str(e)}

			return response

		for scan_id in scan_ids:
			try:
				scan = ScanHistory.objects.get(id=scan_id)
				# if scan is already successful or aborted then do nothing
				if scan.scan_status == SUCCESS_TASK or scan.scan_status == ABORTED_TASK:
					continue
				response = abort_scan(scan)
			except Exception as e:
				logger.error(e)
				response = {'status': False, 'message': str(e)}
			
		for subscan_id in subscan_ids:
			try:
				subscan = SubScan.objects.get(id=subscan_id)
				if subscan.status == SUCCESS_TASK or subscan.status == ABORTED_TASK:
					continue
				response = abort_subscan(subscan)
			except Exception as e:
				logger.error(e)
				response = {'status': False, 'message': str(e)}

		return Response(response)


class ResumeScan(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_INITATE_SCANS_SUBSCANS

	def post(self, request):
		data = request.data
		scan_id = data.get('scan_id')

		response = {'status': False}
		if not scan_id:
			return Response({'status': False, 'message': 'Scan ID required.'})

		try:
			scan = ScanHistory.objects.get(id=scan_id)
			if scan.scan_status == SUCCESS_TASK:
				return Response({'status': False, 'message': 'Scan is already completed.'})
			
			from reNgine.tasks import resume_scan_temporal
			resume_scan_temporal(scan.id)
			
			response['status'] = True
			response['message'] = 'Scan resumption initiated successfully.'
		except ScanHistory.DoesNotExist:
			response['message'] = 'Scan not found'
		except Exception as e:
			logger.error(f'Error resuming scan {scan_id}: {e}')
			response['message'] = str(e)
		
		return Response(response)


class InitiateScan(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_INITATE_SCANS_SUBSCANS

	def post(self, request):
		data = request.data
		domain_ids = data.get('domain_id')
		engine_id = data.get('engine_id')
		
		try:
			# Convert single ID to list for uniform processing
			if not isinstance(domain_ids, list):
				domain_ids = [domain_ids]

			results = []
			errors = []

			for domain_id in domain_ids:
				try:
					domain = Domain.objects.get(pk=domain_id)
					
					# Extract optional scan parameters
					subdomains_in = data.get('importSubdomainTextArea', [])
					subdomains_out = data.get('outOfScopeSubdomainTextarea', [])
					starting_point_path = data.get('startingPointPath', '').strip()
					excluded_paths = data.get('excludedPaths', [])
					if isinstance(excluded_paths, str):
						excluded_paths = [path.strip() for path in excluded_paths.split(',')]
					
					custom_dorks = data.get('customDorkTextarea', '').strip() if data.get('customDorkSwitch') else None
					spiderfoot_scan = data.get('spiderfoot_scan', False)

					# Create ScanHistory object
					scan_history_id = create_scan_object(
						host_id=domain_id,
						engine_id=engine_id,
						initiated_by_id=request.user.id
					)
					scan = ScanHistory.objects.get(pk=scan_history_id)
					if custom_dorks:
						scan.cfg_custom_dorks = custom_dorks
						scan.save()

					# Start the scan via Temporal durable workflow orchestration
					kwargs = {
						'scan_history_id': scan.id,
						'domain_id': domain.id,
						'engine_id': engine_id,
						'scan_type': LIVE_SCAN,
						'results_dir': settings.RENGINE_RESULTS,
						'imported_subdomains': subdomains_in,
						'out_of_scope_subdomains': subdomains_out,
						'starting_point_path': starting_point_path,
						'excluded_paths': excluded_paths,
						'custom_dorks': custom_dorks,
						'enable_spiderfoot_scan': spiderfoot_scan,
						'initiated_by_id': request.user.id
					}
					initiate_scan_temporal(**kwargs)
					results.append({'domain': domain.name, 'scan_id': scan.id})
					
				except Exception as e:
					logger.error(f"Error initiating scan for domain {domain_id}: {str(e)}")
					errors.append({'domain_id': domain_id, 'error': str(e)})

			if not results:
				return Response({
					'status': False,
					'message': 'Failed to initiate any scans',
					'errors': errors
				}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

			return Response({
				'status': True,
				'message': f'Successfully initiated {len(results)} scan(s)',
				'results': results,
				'errors': errors if errors else None
			})
		except Exception as e:
			logger.error(e)
			return Response({
				'status': False,
				'message': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class InitiateSubTask(APIView):

	permission_classes = [HasPermission]
	permission_required = PERM_INITATE_SCANS_SUBSCANS

	def post(self, request):
		"""Initiate a set of subscans on one or more subdomains.

		Args:
			request (HttpRequest): Django HTTP request containing:
				- engine_id (int): Engine configuration ID to use.
				- tasks (list[str]): Task names to execute (e.g. 'port_scan', 'fetch_url').
				- subdomain_ids (list[int]): Subdomain IDs to run subtasks on.
		"""
		req = self.request
		data = req.data
		engine_id = data.get('engine_id')
		scan_types = data['tasks']
		# Accept both subdomain_ids (list) and subdomain_id (single int) for mobile compatibility
		subdomain_ids = data.get('subdomain_ids') or []
		if not subdomain_ids:
			single = data.get('subdomain_id')
			if single:
				subdomain_ids = [single]
		for subdomain_id in subdomain_ids:
			logger.info(f'Running subscans {scan_types} on subdomain "{subdomain_id}" ...')
			ctx = {
				'scan_history_id': None,
				'subdomain_id': subdomain_id,
				'scan_type': scan_types,
				'engine_id': engine_id
			}
			initiate_subscan_temporal(**ctx)
		return Response({'status': True})


class ToggleMonitoringAPIView(APIView):
	permission_classes = [IsAuthenticated, HasPermission]
	permission_required = PERM_MODIFY_TARGETS

	def post(self, request):
		domain_id = request.data.get('domain_id')
		try:
			from targetApp.models import Domain
			domain = Domain.objects.get(id=domain_id)
			domain.is_monitored = not domain.is_monitored
			domain.save()
			from targetApp.views import manage_monitoring_task
			manage_monitoring_task(domain)
			return Response({
				'status': True,
				'is_monitored': domain.is_monitored,
				'message': f'Monitoring {"enabled" if domain.is_monitored else "disabled"} for {domain.name}'
			})
		except Exception as e:
			return Response({'status': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeleteSubdomain(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_RESULTS

	def post(self, request):
		req = self.request
		for id in req.data['subdomain_ids']:
			Subdomain.objects.get(id=id).delete()
		return Response({'status': True})


class DeleteVulnerability(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_RESULTS

	def post(self, request):
		req = self.request
		for id in req.data['vulnerability_ids']:
			Vulnerability.objects.get(id=id).delete()
		return Response({'status': True})


class ListInterestingKeywords(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request, format=None):
		req = self.request
		keywords = get_lookup_keywords()
		return Response(keywords)


class RengineUpdateCheck(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		github_api = \
			'https://api.github.com/repos/whiterabb17/r3ngine/releases'
		
		return_response = {
			'status': False,
			'update_available': False,
			'latest_version': None,
			'current_version': RENGINE_CURRENT_VERSION,
			'redirect_link': 'https://github.com/whiterabb17/r3ngine/releases'
		}

		def safe_parse_version(v_str):
			if not v_str:
				return version.parse('0.0.0')
			v_str = v_str.strip().lstrip('v')
			try:
				return version.parse(v_str)
			except Exception:
				# PEP 440 sanitization fallback
				sanitized = v_str.replace('-beta.rc', 'b').replace('-rc', 'rc').replace('-beta', 'b').replace('-', '.')
				try:
					return version.parse(sanitized)
				except Exception:
					digits = re.findall(r'\d+', v_str)
					if digits:
						try:
							return version.parse('.'.join(digits))
						except Exception:
							pass
					return version.parse('0.0.0')

		try:
			response = requests.get(github_api).json()
			if 'message' in response and 'rate limit' in response['message'].lower():
				return_response['message'] = 'RateLimited'
			elif isinstance(response, list) and len(response) > 0:
				latest_release_name = response[0]['name']
				latest_release_version = re.search(r'v?(\d+\.)?(\d+\.)?(\*|\d+)', latest_release_name)
				if latest_release_version:
					latest_release_version = latest_release_version.group(0).replace('v', '')
					return_response['latest_version'] = latest_release_version
					return_response['changelog'] = response[0]['body']
					return_response['status'] = True
		except Exception as e:
			logger.error(f"Error fetching GitHub releases: {str(e)}")

		# Fallback: check .version file in master branch
		version_url = 'https://raw.githubusercontent.com/whiterabb17/r3ngine/main/web/.version'
		try:
			raw_version_response = requests.get(version_url)
			if raw_version_response.status_code == 200:
				raw_version = raw_version_response.text.strip().replace('v', '')
				# If raw_version is higher than latest release or no release found
				if not return_response['latest_version'] or safe_parse_version(raw_version) > safe_parse_version(return_response['latest_version']):
					return_response['latest_version'] = raw_version
					return_response['redirect_link'] = 'https://github.com/whiterabb17/r3ngine'
					return_response['changelog'] = 'A new update is available in the repository. Please pull the latest changes from the main branch.'
					return_response['status'] = True
		except Exception as e:
			logger.error(f"Error fetching raw .version: {str(e)}")

		if return_response['status'] and return_response['latest_version']:
			is_version_update_available = safe_parse_version(return_response['current_version']) < safe_parse_version(return_response['latest_version'])
			return_response['update_available'] = is_version_update_available

			if is_version_update_available:
				create_inappnotification(
					title='r3ngine Update Available',
					description=f'Update to version {return_response["latest_version"]} is available',
					notification_type=SYSTEM_LEVEL_NOTIFICATION,
					project_slug=None,
					icon='mdi-update',
					redirect_link=return_response['redirect_link'],
					open_in_new_tab=True
				)

		return Response(return_response)


class RengineSystemSettingsAPIView(APIView):
	permission_classes = [IsAuthenticated, HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		import shutil
		total, used, _ = shutil.disk_usage("/")
		total_gb = total // (2**30)
		used_gb = used // (2**30)
		free_gb = total_gb - used_gb
		consumed_percent = int(100 * float(used_gb) / float(total_gb)) if total_gb > 0 else 0

		return Response({
			'total': total_gb,
			'used': used_gb,
			'free': free_gb,
			'consumed_percent': consumed_percent
		})


class ProxySettingsAPIView(APIView):
	permission_classes = [IsAuthenticated, HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def get(self, request):
		proxy = Proxy.objects.first()
		serializer = ProxySerializer(proxy)
		return Response(serializer.data)

	def post(self, request):
		proxy = Proxy.objects.first()
		if not proxy:
			proxy = Proxy.objects.create()
		data = request.data.copy()
		message = 'Proxies updated successfully'
		skip_validation = request.data.get('skip_validation') == 'true'
		if data.get('use_proxy') and data.get('proxies') and not skip_validation:
			from reNgine.common_func import validate_proxies
			original_count = len([line for line in data['proxies'].splitlines() if line.strip()])
			validated = validate_proxies(data['proxies'])
			data['proxies'] = validated
			saved_count = len([line for line in validated.splitlines() if line.strip()])
			message = f'Proxies updated. Validated {saved_count}/{original_count} live proxies.'
		serializer = ProxySerializer(proxy, data=data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response({'status': True, 'message': message})
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProxyFetchAPIView(APIView):
	permission_classes = [IsAuthenticated, HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def post(self, request):
		try:
			from reNgine.tasks import fetch_proxies_task
			from reNgine.job_tracker import create_job
			import threading
			limit = request.data.get('limit', 1000)
			try:
				limit = int(limit)
			except Exception:
				limit = 1000
			job_id = create_job()
			threading.Thread(
				target=fetch_proxies_task,
				kwargs={'limit': limit, 'job_id': job_id},
				daemon=True,
			).start()
			return Response({'status': True, 'task_id': job_id})
		except Exception as e:
			return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UninstallTool(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		req = self.request
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)


		if tool.is_default:
			return Response({'status': False, 'message': 'Default tools can not be uninstalled'})

		# check install instructions, if it is installed using go, then remove from go bin path,
		# else try to remove from github clone path

		# getting tool name is tricky!

		if 'go install' in tool.install_command:
			tool_name = tool.install_command.split('/')[-1].split('@')[0]
			uninstall_command = 'rm /usr/local/bin/' + tool_name
		elif 'git clone' in tool.install_command:
			tool_name = tool.install_command[:-1] if tool.install_command[-1] == '/' else tool.install_command
			tool_name = tool_name.split('/')[-1]
			uninstall_command = 'rm -rf ' + tool.github_clone_path
		else:
			return Response({'status': False, 'message': 'Cannot uninstall tool!'})

		run_command.run(uninstall_command, shell=True)

		tool.delete()

		return Response({'status': True, 'message': 'Uninstall Tool Success'})


class UpdateTool(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		req = self.request
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)

		# if git clone was used for installation, then we must use git pull inside project directory,
		# otherwise use the same command as given

		update_command = tool.update_command.lower()

		if not update_command:
			return Response({'status': False, 'message': tool.name + 'has missing update command! Cannot update the tool.'})
		elif update_command == 'git pull':
			tool_name = tool.install_command[:-1] if tool.install_command[-1] == '/' else tool.install_command
			tool_name = tool_name.split('/')[-1]
			update_command = 'cd /usr/src/github/' + tool_name + ' && git pull && cd -'

		
		try:
			return_code, output = run_command.run(update_command, shell=True)
			if return_code == 0:
				return Response({'status': True, 'message': tool.name + ' updated successfully.'})
			else:
				logger.error(f"Update failed for {tool.name}: {output}")
				return Response({'status': False, 'message': f'Update failed: {output[:200]}...'})
		except Exception as e:
			logger.error(str(e))
			return Response({'status': False, 'message': str(e)})

class UninstallTool(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		req = self.request
		tool_id = req.query_params.get('tool_id')
		if not InstalledExternalTool.objects.filter(id=tool_id).exists():
			return Response({'status': False, 'message': 'Tool Not found'})
		tool = InstalledExternalTool.objects.get(id=tool_id)
		
		try:
			return_code, output = run_command.run(tool.uninstall_command, shell=True)
			if return_code == 0:
				tool.delete()
				return Response({'status': True, 'message': tool.name + ' uninstalled successfully.'})
			else:
				return Response({'status': False, 'message': f'Uninstall failed: {output[:200]}'})
		except Exception as e:
			logger.error(str(e))
			return Response({'status': False, 'message': str(e)})

class GetExternalToolCurrentVersion(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

	def get(self, request):
		req = self.request
		# toolname is also the command
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')
		# can supply either tool id or tool_name

		tool = None

		if tool_id:
			if not InstalledExternalTool.objects.filter(id=tool_id).exists():
				return Response({'status': False, 'message': 'Tool Not found'})
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			if not InstalledExternalTool.objects.filter(name=tool_name).exists():
				return Response({'status': False, 'message': 'Tool Not found'})
			tool = InstalledExternalTool.objects.get(name=tool_name)

		if not tool.version_lookup_command:
			return Response({'status': False, 'message': 'Version Lookup command not provided.'})

		version_number = None
		try:
			return_code, stdout = run_command.run(tool.version_lookup_command, shell=True)
			if return_code != 0:
				logger.warning(f"Version lookup failed for {tool.name} with code {return_code}: {stdout}")
				return Response({'status': False, 'message': 'Tool not found or check failed.'})
		except Exception as e:
			logger.error(f"Error running version lookup command: {str(e)}")
			return Response({'status': False, 'message': f'Error running version lookup command: {str(e)}'})

		if tool.version_match_regex:
			version_number = re.search(re.compile(tool.version_match_regex), str(stdout))
		else:
			# Improved regex: must look like a version and NOT be part of a path
			# Looks for version at start of line or preceded by space, and not followed by /
			version_match_regex = r'(?:^|\s)(?i:v)?(\d+\.\d+(?:\.\d+)*)(?!\/)'
			version_number = re.search(version_match_regex, str(stdout))
		
		if not version_number:
			return Response({'status': False, 'message': 'Tool installed but version could not be parsed.'})

		# Use group(1) to get the captured version number without the leading space
		version = version_number.group(1) if version_number.groups() else version_number.group(0)
		
		# Final check: if version is just a single digit, it's probably wrong (unless it matches a strict regex)
		if not tool.version_match_regex and len(version.strip()) < 3 and '.' not in version:
			return Response({'status': False, 'message': 'Invalid version parsed.'})

		return Response({'status': True, 'version_number': version.strip(), 'tool_name': tool.name})



class GithubToolCheckGetLatestRelease(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS
	
	def get(self, request):
		req = self.request

		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if not InstalledExternalTool.objects.filter(id=tool_id).exists():
			return Response({'status': False, 'message': 'Tool Not found'})

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)

		if not tool.github_url:
			return Response({'status': False, 'message': 'Github URL is not provided, Cannot check updates'})

		# if tool_github_url has https://github.com/ remove and also remove trailing /
		tool_github_url = tool.github_url.replace('http://github.com/', '').replace('https://github.com/', '')
		tool_github_url = remove_lead_and_trail_slash(tool_github_url)
		github_api = f'https://api.github.com/repos/{tool_github_url}/releases'
		try:
			res = requests.get(github_api, timeout=10)
			if res.status_code == 403:
				return Response({'status': False, 'message': 'GitHub Rate Limit Exceeded'})
			response = res.json()
		except requests.exceptions.Timeout:
			return Response({'status': False, 'message': 'GitHub API Timeout'})
		except Exception as e:
			return Response({'status': False, 'message': f'Error fetching from GitHub: {str(e)}'})

		# check if api rate limit exceeded
		if isinstance(response, dict) and 'message' in response:
			if 'rate limit' in response['message'].lower():
				return Response({'status': False, 'message': 'RateLimited'})
			elif 'Not Found' in response['message']:
				return Response({'status': False, 'message': 'Repository Not Found'})
		
		if not response or not isinstance(response, list):
			return Response({'status': False, 'message': 'No releases found'})

		# only send latest release
		response = response[0]

		# Try to find a version string in tag_name or name
		latest_version = response.get('tag_name') or response.get('name') or 'Unknown'
		# If tag_name was used, use name as a secondary identifier
		release_name = response.get('name') or response.get('tag_name') or 'Unknown'

		api_response = {
			'status': True,
			'url': response.get('html_url'),
			'id': response.get('id'),
			'name': release_name,
			'version_number': latest_version,
			'changelog': response.get('body'),
		}
		return Response(api_response)


class ScanStatus(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		slug = self.request.GET.get('project', None)

		# main tasks
		recently_completed_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(Q(scan_status=0) | Q(scan_status=2) | Q(scan_status=3))[:10]
		)
		current_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(scan_status=1)
		)
		pending_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.filter(scan_status=-1)
		)

		# subtasks
		recently_completed_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(Q(status=0) | Q(status=2) | Q(status=3))[:15]
		)
		current_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(status=1)
		)
		pending_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.filter(status=-1)
		)
		response = {
			'scans': {
				'pending': ScanHistorySerializer(pending_scans, many=True).data,
				'scanning': ScanHistorySerializer(current_scans, many=True).data,
				'completed': ScanHistorySerializer(recently_completed_scans, many=True).data
			},
			'tasks': {
				'pending': SubScanSerializer(pending_tasks, many=True).data,
				'running': SubScanSerializer(current_tasks, many=True).data,
				'completed': SubScanSerializer(recently_completed_tasks, many=True).data
			}
		}
		
		return Response(response)


class Whois(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		target = req.query_params.get('target')
		if not target:
			return Response({'status': False, 'message': 'Target IP/Domain required!'})
		if not (validators.domain(target) or validators.ipv4(target) or validators.ipv6(target)):
			print(f'Ip address or domain "{target}" did not pass validator.')
			return Response({'status': False, 'message': 'Invalid domain or IP'})
		is_force_update = req.query_params.get('is_reload')
		is_force_update = True if is_force_update and 'true' == is_force_update.lower() else False
		response = query_whois(target, is_force_update)
		return Response(response)


class ReverseWhois(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		lookup_keyword = req.query_params.get('lookup_keyword')
		response = query_reverse_whois(lookup_keyword)
		return Response(response)


class DomainIPHistory(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		domain = req.query_params.get('domain')
		response = query_ip_history(domain)
		return Response(response)


class CMSDetector(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		url = req.query_params.get('url')
		#save_db = True if 'save_db' in req.query_params else False
		response = {'status': False}

		if not (validators.url(url) or validators.domain(url)):
			response['message'] = 'Invalid Domain/URL provided!'
			return Response(response)

		try:
			# response = get_cms_details(url)
			response = {}
			cms_detector_command = f'python3 /usr/src/github/CMSeeK/cmseek.py'
			cms_detector_command += ' --random-agent --batch --follow-redirect'
			cms_detector_command += f' -u {url}'

			_, output = run_command.run(cms_detector_command, shell=True, remove_ansi_sequence=True)

			response['message'] = 'Could not detect CMS!'

			parsed_url = urlparse(url)

			domain_name = parsed_url.hostname
			port = parsed_url.port

			find_dir = domain_name

			if port:
				find_dir += '_{}'.format(port)
			# look for result path in output
			path_regex = r"Result: (\/usr\/src[^\"\s]*)"
			match = re.search(path_regex, output)
			if match:
				cms_json_path = match.group(1)
				if os.path.isfile(cms_json_path):
					cms_file_content = json.loads(open(cms_json_path, 'r').read())
					if not cms_file_content.get('cms_id'):
						return response
					response = {}
					response = cms_file_content
					response['status'] = True
					try:
						# remove results
						cms_dir_path = os.path.dirname(cms_json_path)
						shutil.rmtree(cms_dir_path)
					except Exception as e:
						logger.error(e)
					return Response(response)
			return Response(response)
		except Exception as e:
			response = {'status': False, 'message': str(e)}
			return Response(response)


class IPToDomain(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		ip_address = req.query_params.get('ip_address')
		if not ip_address:
			return Response({
				'status': False,
				'message': 'IP Address Required'
			})
		try:
			logger.info(f'Resolving IP address {ip_address} ...')
			resolved_ips = []
			for ip in IPv4Network(ip_address, False):
				domains = []
				ips = []
				try:
					(domain, domains, ips) = socket.gethostbyaddr(str(ip))
				except socket.herror:
					logger.info(f'No PTR record for {ip_address}')
					domain = str(ip)
				if domain not in domains:
					domains.append(domain)
				resolved_ips.append({'ip': str(ip),'domain': domain, 'domains': domains, 'ips': ips})
			response = {
				'status': True,
				'orig': ip_address,
				'ip_address': resolved_ips,
			}
		except Exception as e:
			logger.exception(e)
			response = {
				'status': False,
				'ip_address': ip_address,
				'message': f'Exception {e}'
			}
		finally:
			return Response(response)


class VulnerabilityReport(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request):
		req = self.request
		vulnerability_id = req.query_params.get('vulnerability_id')
		return Response({"status": send_hackerone_report(vulnerability_id)})


class GetFileContents(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request, format=None):
		import pathlib
		req = self.request
		name = req.query_params.get('name')

		response = {}
		response['status'] = False

		if 'nuclei_config' in req.query_params:
			path = "/root/.config/nuclei/config.yaml"
			if not os.path.exists(path):
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'subfinder_config' in req.query_params:
			path = "/root/.config/subfinder/config.yaml"
			if not os.path.exists(path):
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'naabu_config' in req.query_params:
			path = "/root/.config/naabu/config.yaml"
			if not os.path.exists(path):
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'theharvester_config' in req.query_params:
			path = "/usr/src/github/theHarvester/api-keys.yaml"
			if not os.path.exists(path):
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'spiderfoot_config' in req.query_params:
			path = "/usr/src/github/spiderfoot/spiderfoot.cfg"
			if not os.path.exists(path):
				# Create a default config or just touch
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'amass_config' in req.query_params:
			path = "/root/.config/amass.ini"
			if not os.path.exists(path):
				pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
				pathlib.Path(path).touch()
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'gf_pattern' in req.query_params:
			basedir = '/root/.gf'
			path = f'/root/.gf/{name}.json'
			if is_safe_path(basedir, path) and os.path.exists(path):
				content = open(path, "r").read()
				response['status'] = True
				response['content'] = content
			else:
				response['message'] = "Invalid path!"
				response['status'] = False
			return Response(response)


		if 'nuclei_template' in req.query_params:
			safe_dir = '/root/nuclei-templates'
			path = f'/root/nuclei-templates/{name}'
			if is_safe_path(safe_dir, path) and os.path.exists(path):
				content = open(path.format(name), "r").read()
				response['status'] = True
				response['content'] = content
			else:
				response['message'] = 'Invalid Path!'
				response['status'] = False
			return Response(response)

		response['message'] = 'Invalid Query Params'
		return Response(response)


class ListTodoNotes(APIView):
	permission_classes = [IsPenetrationTester]
	def get(self, request, format=None):
		req = self.request
		notes = TodoNote.objects.all().order_by('-id')
		scan_id = req.query_params.get('scan_id')
		project = req.query_params.get('project')
		if project:
			notes = notes.filter(project__slug=project)
		target_id = req.query_params.get('target_id')
		todo_id = req.query_params.get('todo_id')
		subdomain_id = req.query_params.get('subdomain_id')
		if target_id:
			notes = notes.filter(scan_history__in=ScanHistory.objects.filter(domain__id=target_id))
		elif scan_id:
			notes = notes.filter(scan_history__id=scan_id)
		if todo_id:
			notes = notes.filter(id=todo_id)
		if subdomain_id:
			notes = notes.filter(subdomain__id=subdomain_id)
		notes = ReconNoteSerializer(notes, many=True)
		return Response({'notes': notes.data})


class ToggleTodoStatus(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		todo_id = request.data.get('id')
		try:
			note = TodoNote.objects.get(id=todo_id)
			note.is_done = not note.is_done
			note.save()
			return Response({'status': True, 'is_done': note.is_done})
		except TodoNote.DoesNotExist:
			return Response({'status': False, 'message': 'Note not found'}, status=404)


class ToggleNoteImportance(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		todo_id = request.data.get('id')
		try:
			note = TodoNote.objects.get(id=todo_id)
			note.is_important = not note.is_important
			note.save()
			return Response({'status': True, 'is_important': note.is_important})
		except TodoNote.DoesNotExist:
			return Response({'status': False, 'message': 'Note not found'}, status=404)


class DeleteReconNote(APIView):
	permission_classes = [IsPenetrationTester]
	def post(self, request):
		todo_id = request.data.get('id')
		try:
			TodoNote.objects.filter(id=todo_id).delete()
			return Response({'status': True})
		except Exception as e:
			return Response({'status': False, 'message': str(e)}, status=400)


class ListScanHistory(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_history = ScanHistory.objects.all().order_by('-start_scan_date')
		project = req.query_params.get('project')
		if project:
			scan_history = scan_history.filter(domain__project__slug=project)
		scan_history = ScanHistorySerializer(scan_history, many=True)
		return Response(scan_history.data)


class ListEngines(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		engines = EngineType.objects.order_by('engine_name').all()
		engine_serializer = EngineSerializer(engines, many=True)
		return Response({'engines': engine_serializer.data})


class ListOrganizations(APIView):
	permission_classes = [IsAuthenticated, IsAuditor]
	def get(self, request, format=None):
		req = self.request
		organizations = Organization.objects.all()
		organization_serializer = OrganizationSerializer(organizations, many=True)
		return Response({'organizations': organization_serializer.data})


class CreateOrganization(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_TARGETS

	def post(self, request):
		data = request.data
		name = data.get('name')
		description = data.get('description', '')
		domains = data.get('domains', [])
		slug = data.get('slug')

		if not name or not slug:
			return Response({'status': False, 'message': 'Name and project slug are required'}, status=400)

		try:
			project = Project.objects.get(slug=slug)
			organization = Organization.objects.create(
				name=name,
				description=description,
				project=project,
				insert_date=timezone.now()
			)
			for domain_id in domains:
				domain = Domain.objects.get(id=domain_id)
				organization.domains.add(domain)
			return Response({'status': True, 'message': 'Organization created successfully', 'id': organization.id})
		except Exception as e:
			return Response({'status': False, 'message': str(e)}, status=400)


class UpdateOrganization(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_TARGETS

	def post(self, request):
		data = request.data
		org_id = data.get('id')
		name = data.get('name')
		description = data.get('description', '')
		domains = data.get('domains', [])

		if not org_id or not name:
			return Response({'status': False, 'message': 'ID and Name are required'}, status=400)

		try:
			organization = Organization.objects.get(id=org_id)
			organization.name = name
			organization.description = description
			organization.save()
			
			# Update domains
			organization.domains.clear()
			for domain_id in domains:
				domain = Domain.objects.get(id=domain_id)
				organization.domains.add(domain)
				
			return Response({'status': True, 'message': 'Organization updated successfully'})
		except Exception as e:
			return Response({'status': False, 'message': str(e)}, status=400)


class ListWordlists(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		wordlists = Wordlist.objects.all()
		wordlist_serializer = WordlistSerializer(wordlists, many=True)
		return Response({'wordlists': wordlist_serializer.data})


class ListConfigurations(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		configurations = Configuration.objects.all()
		configuration_serializer = ConfigurationSerializer(configurations, many=True)
		return Response({'configurations': configuration_serializer.data})


class ListTargetsInOrganization(APIView):
	permission_classes = [IsAuthenticated, HasPermission]
	def get(self, request, format=None):
		req = self.request
		organization_id = req.query_params.get('organization_id')
		organization = Organization.objects.filter(id=organization_id)
		targets = Domain.objects.filter(domains__in=organization)
		organization_serializer = OrganizationSerializer(organization, many=True)
		targets_serializer = OrganizationTargetsSerializer(targets, many=True)
		return Response({'organization': organization_serializer.data, 'domains': targets_serializer.data})


class ListTargetsWithoutOrganization(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		targets = Domain.objects.exclude(domains__in=Organization.objects.all())
		targets_serializer = OrganizationTargetsSerializer(targets, many=True)
		return Response({'domains': targets_serializer.data})


class VisualiseData(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		if scan_id:
			mitch_data = ScanHistory.objects.filter(id=scan_id)
		elif target_id:
			mitch_data = ScanHistory.objects.filter(domain__id=target_id).order_by('-start_scan_date')[:1]
		else:
			return Response([])

		serializer = VisualiseDataSerializer(mitch_data, many=True)
		return Response(serializer.data)


class ListTechnology(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')

		if target_id:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.filter(
					target_domain__id=target_id)).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})
		elif scan_id:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.filter(
					scan_history__id=scan_id)).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})
		else:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.all()).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})


class ListDorkTypes(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.filter(id=scan_id)
			).values('type').annotate(count=Count('type')).order_by('-count')
			serializer = DorkCountSerializer(dork, many=True)
			return Response({"dorks": serializer.data})
		else:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.all()
			).values('type').annotate(count=Count('type')).order_by('-count')
			serializer = DorkCountSerializer(dork, many=True)
			return Response({"dorks": serializer.data})


class ListEmails(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			email = Email.objects.filter(
				emails__in=ScanHistory.objects.filter(id=scan_id)).order_by('password')
			serializer = EmailSerializer(email, many=True)
			return Response({"emails": serializer.data})


class ListDorks(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		type = req.query_params.get('type')
		if scan_id:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.filter(id=scan_id))
		else:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.all())
		if scan_id and type:
			dork = dork.filter(type=type)
		serializer = DorkSerializer(dork, many=True)
		grouped_res = {}
		for item in serializer.data:
			item_type = item['type']
			if item_type not in grouped_res:
				grouped_res[item_type] = []
			grouped_res[item_type].append(item)
		return Response({"dorks": grouped_res})


class ListEmployees(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			employee = Employee.objects.filter(
				employees__in=ScanHistory.objects.filter(id=scan_id))
			serializer = EmployeeSerializer(employee, many=True)
			return Response({"employees": serializer.data})


class ListPorts(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		ip_address = req.query_params.get('ip_address')

		if target_id:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.filter(
						target_domain__id=target_id))).distinct()
		elif scan_id:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.filter(
						scan_history__id=scan_id))).distinct()
		else:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.all())).distinct()

		if ip_address:
			port = port.filter(ports__address=ip_address).distinct()

		serializer = PortSerializer(port, many=True)
		return Response({"ports": serializer.data})


class ListSubdomains(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		project = req.query_params.get('project')
		target_id = req.query_params.get('target_id')
		ip_address = req.query_params.get('ip_address')
		port = req.query_params.get('port')
		tech = req.query_params.get('tech')

		subdomains = Subdomain.objects.all()
		if project:
			subdomains = subdomains.filter(target_domain__project__slug=project)

		if scan_id:
			subdomain_query = subdomains.filter(scan_history__id=scan_id).distinct('name')
		elif target_id:
			subdomain_query = subdomains.filter(target_domain__id=target_id).distinct('name')
		else:
			subdomain_query = subdomains.all().distinct('name')

		# Prefetch for performance
		subdomain_query = subdomain_query.prefetch_related(
			'screenshots', 'technologies', 'ip_addresses', 'ip_addresses__ports'
		)

		if ip_address:
			subdomain_query = subdomain_query.filter(ip_addresses__address=ip_address)

		if tech:
			subdomain_query = subdomain_query.filter(technologies__name=tech)

		if port:
			subdomain_query = subdomain_query.filter(
				ip_addresses__in=IpAddress.objects.filter(
					ports__in=Port.objects.filter(
						number=port)))

		if 'only_important' in req.query_params:
			subdomain_query = subdomain_query.filter(is_important=True)

		if 'no_lookup_interesting' in req.query_params:
			serializer = OnlySubdomainNameSerializer(subdomain_query, many=True)
		else:
			serializer = SubdomainSerializer(subdomain_query, many=True)
		return Response({"subdomains": serializer.data})

	def post(self, req):
		req = self.request
		data = req.data

		subdomain_ids = data.get('subdomain_ids')

		subdomain_names = []

		for id in subdomain_ids:
			subdomain_names.append(Subdomain.objects.get(id=id).name)

		if subdomain_names:
			return Response({'status': True, "results": subdomain_names})

		return Response({'status': False})



class ListOsintUsers(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).exclude(author__isnull=True).values('author').distinct()
			serializer = MetafinderUserSerializer(documents, many=True)
			return Response({"users": serializer.data})


class ListMetadata(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).distinct()
			serializer = MetafinderDocumentSerializer(documents, many=True)
			return Response({"metadata": serializer.data})


class ListIPs(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')

		port = req.query_params.get('port')

		if target_id:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.filter(
					target_domain__id=target_id)).distinct()
		elif scan_id:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.filter(
					scan_history__id=scan_id)).distinct()
		else:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.all()).distinct()

		if port:
			ips = ips.filter(
				ports__in=Port.objects.filter(
					number=port)).distinct()


		serializer = IpSerializer(ips, many=True)
		return Response({"ips": serializer.data})


class IpAddressViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Subdomain.objects.none()
	serializer_class = IpSubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')

		if scan_id:
			self.queryset = Subdomain.objects.filter(
				scan_history__id=scan_id).exclude(
				ip_addresses__isnull=True).distinct()
		else:
			self.serializer_class = IpSerializer
			self.queryset = IpAddress.objects.all()
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainsViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			queryset = Subdomain.objects.filter(scan_history__id=scan_id).prefetch_related(
				'screenshots', 'technologies', 'ip_addresses', 'ip_addresses__ports'
			)
			if 'only_screenshot' in self.request.query_params:
				return queryset.filter(
					Q(screenshot_path__isnull=False) | Q(screenshots__isnull=False)
				).distinct()
			return queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainChangesViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	'''
		This viewset will return the Subdomain changes
		To get the new subdomains, we will look for ScanHistory with
		subdomain_discovery = True and the status of the last scan has to be
		successful and calculate difference
	'''
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainChangesSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		changes = req.query_params.get('changes')
		domain_id = ScanHistory.objects.filter(id=scan_id)[0].domain.id
		scan_history_query = (
			ScanHistory.objects
			.filter(domain=domain_id)
			.filter(tasks__overlap=['subdomain_discovery'])
			.filter(id__lte=scan_id)
			.exclude(Q(scan_status=-1) | Q(scan_status=1))
		)
		if scan_history_query.count() > 1:
			last_scan = scan_history_query.order_by('-start_scan_date')[1]
			scanned_host_q1 = (
				Subdomain.objects
				.filter(scan_history__id=scan_id)
				.values('name')
			)
			scanned_host_q2 = (
				Subdomain.objects
				.filter(scan_history__id=last_scan.id)
				.values('name')
			)
			added_subdomain = scanned_host_q1.difference(scanned_host_q2)
			removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
			if changes == 'added':
				return (
					Subdomain.objects
					.filter(scan_history=scan_id)
					.filter(name__in=added_subdomain)
					.annotate(
						change=Value('added', output_field=CharField())
					)
				)
			elif changes == 'removed':
				return (
					Subdomain.objects
					.filter(scan_history=last_scan)
					.filter(name__in=removed_subdomains)
					.annotate(
						change=Value('removed', output_field=CharField())
					)
				)
			else:
				added_subdomain = (
					Subdomain.objects
					.filter(scan_history=scan_id)
					.filter(name__in=added_subdomain)
					.annotate(
						change=Value('added', output_field=CharField())
					)
				)
				removed_subdomains = (
					Subdomain.objects
					.filter(scan_history=last_scan)
					.filter(name__in=removed_subdomains)
					.annotate(
						change=Value('removed', output_field=CharField())
					)
				)
				changes = added_subdomain.union(removed_subdomains)
				return changes
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class EndPointChangesViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	'''
		This viewset will return the EndPoint changes
	'''
	queryset = EndPoint.objects.none()
	serializer_class = EndPointChangesSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		changes = req.query_params.get('changes')
		domain_id = ScanHistory.objects.filter(id=scan_id).first().domain.id
		scan_history = (
			ScanHistory.objects
			.filter(domain=domain_id)
			.filter(tasks__overlap=['fetch_url'])
			.filter(id__lte=scan_id)
			.filter(scan_status=2)
		)
		if scan_history.count() > 1:
			last_scan = scan_history.order_by('-start_scan_date')[1]
			scanned_host_q1 = (
				EndPoint.objects
				.filter(scan_history__id=scan_id)
				.values('http_url')
			)
			scanned_host_q2 = (
				EndPoint.objects
				.filter(scan_history__id=last_scan.id)
				.values('http_url')
			)
			added_endpoints = scanned_host_q1.difference(scanned_host_q2)
			removed_endpoints = scanned_host_q2.difference(scanned_host_q1)
			if changes == 'added':
				return (
					EndPoint.objects
					.filter(scan_history=scan_id)
					.filter(http_url__in=added_endpoints)
					.annotate(change=Value('added', output_field=CharField()))
				)
			elif changes == 'removed':
				return (
					EndPoint.objects
					.filter(scan_history=last_scan)
					.filter(http_url__in=removed_endpoints)
					.annotate(change=Value('removed', output_field=CharField()))
				)
			else:
				added_endpoints = (
					EndPoint.objects
					.filter(scan_history=scan_id)
					.filter(http_url__in=added_endpoints)
					.annotate(change=Value('added', output_field=CharField()))
				)
				removed_endpoints = (
					EndPoint.objects
					.filter(scan_history=last_scan)
					.filter(http_url__in=removed_endpoints)
					.annotate(change=Value('removed', output_field=CharField()))
				)
				changes = added_endpoints.union(removed_endpoints)
				return changes
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class InterestingSubdomainViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		domain_id = req.query_params.get('target_id')

		if 'only_subdomains' in self.request.query_params:
			self.serializer_class = InterestingSubdomainSerializer

		if scan_id:
			self.queryset = get_interesting_subdomains(scan_history=scan_id)
		elif domain_id:
			self.queryset = get_interesting_subdomains(domain_id=domain_id)
		else:
			self.queryset = get_interesting_subdomains()

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		order_col = 'content_length'
		if _order_col == '0':
			order_col = 'name'
		elif _order_col == '1':
			order_col = 'page_title'
		elif _order_col == '2':
			order_col = 'http_status'
		elif _order_col == '3':
			order_col = 'content_length'

		if _order_direction == 'desc':
			order_col = f'-{order_col}'

		if search_value:
			qs = self.queryset.filter(
				Q(name__icontains=search_value) |
				Q(page_title__icontains=search_value) |
				Q(http_status__icontains=search_value)
			)
		return qs.order_by(order_col)

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class InterestingEndpointViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = EndPoint.objects.none()
	serializer_class = EndpointSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		if 'only_endpoints' in self.request.query_params:
			self.serializer_class = InterestingEndPointSerializer
		if scan_id:
			return get_interesting_endpoints(scan_history=scan_id)
		elif target_id:
			return get_interesting_endpoints(target=target_id)
		else:
			return get_interesting_endpoints()

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainDatatableViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		url_query = req.query_params.get('query_param')
		ip_address = req.query_params.get('ip_address')
		name = req.query_params.get('name')
		project = req.query_params.get('project')

		subdomains = Subdomain.objects.filter(target_domain__project__slug=project)

		if 'is_important' in req.query_params:
			subdomains = subdomains.filter(is_important=True)

		if target_id:
			self.queryset = (
				subdomains
				.filter(target_domain__id=target_id)
				.distinct()
			)
		elif url_query:
			self.queryset = (
				subdomains
				.filter(Q(target_domain__name=url_query))
				.distinct()
			)
		elif scan_id:
			self.queryset = (
				subdomains
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		else:
			self.queryset = subdomains.distinct()

		if 'only_directory' in req.query_params:
			self.queryset = self.queryset.exclude(directories__isnull=True)

		if ip_address:
			self.queryset = self.queryset.filter(ip_addresses__address__icontains=ip_address)

		if name:
			self.queryset = self.queryset.filter(name=name)

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		order_col = 'content_length'
		if _order_col == '0':
			order_col = 'checked'
		elif _order_col == '1':
			order_col = 'name'
		elif _order_col == '4':
			order_col = 'http_status'
		elif _order_col == '5':
			order_col = 'page_title'
		elif _order_col == '8':
			order_col = 'content_length'
		elif _order_col == '10':
			order_col = 'response_time'
		if _order_direction == 'desc':
			order_col = f'-{order_col}'
		# if the search query is separated by = means, it is a specific lookup
		# divide the search query into two half and lookup
		if search_value:
			operators = ['=', '&', '|', '>', '<', '!']
			if any(x in search_value for x in operators):
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Subdomain.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
		return qs.order_by(order_col)

	def general_lookup(self, search_value):
		qs = self.queryset.filter(
			Q(name__icontains=search_value) |
			Q(cname__icontains=search_value) |
			Q(http_status__icontains=search_value) |
			Q(page_title__icontains=search_value) |
			Q(http_url__icontains=search_value) |
			Q(technologies__name__icontains=search_value) |
			Q(webserver__icontains=search_value) |
			Q(ip_addresses__address__icontains=search_value) |
			Q(ip_addresses__ports__number__icontains=search_value) |
			Q(ip_addresses__ports__service_name__icontains=search_value) |
			Q(ip_addresses__ports__description__icontains=search_value)
		)

		if 'only_directory' in self.request.query_params:
			qs = qs | self.queryset.filter(
				Q(directories__directory_files__name__icontains=search_value)
			)

		return qs

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'name' in title:
				qs = self.queryset.filter(name__icontains=content)
			elif 'page_title' in title:
				qs = self.queryset.filter(page_title__icontains=content)
			elif 'http_url' in title:
				qs = self.queryset.filter(http_url__icontains=content)
			elif 'content_type' in title:
				qs = self.queryset.filter(content_type__icontains=content)
			elif 'cname' in title:
				qs = self.queryset.filter(cname__icontains=content)
			elif 'webserver' in title:
				qs = self.queryset.filter(webserver__icontains=content)
			elif 'ip_addresses' in title:
				qs = self.queryset.filter(
					ip_addresses__address__icontains=content)
			elif 'is_important' in title:
				if 'true' in content.lower():
					qs = self.queryset.filter(is_important=True)
				else:
					qs = self.queryset.filter(is_important=False)
			elif 'port' in title:
				qs = (
					self.queryset
					.filter(ip_addresses__ports__number__icontains=content)
					|
					self.queryset
					.filter(ip_addresses__ports__service_name__icontains=content)
					|
					self.queryset
					.filter(ip_addresses__ports__description__icontains=content)
				)
			elif 'technology' in title:
				qs = (
					self.queryset
					.filter(technologies__name__icontains=content)
				)
			elif 'http_status' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.filter(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.filter(content_length=int_http_status)
				except Exception as e:
					print(e)

		elif '>' in search_value:
			search_param = search_value.split(">")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'http_status' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(http_status__gt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(content_length__gt=int_val)
				except Exception as e:
					print(e)

		elif '<' in search_value:
			search_param = search_value.split("<")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'http_status' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(http_status__lt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(content_length__lt=int_val)
				except Exception as e:
					print(e)

		elif '!' in search_value:
			search_param = search_value.split("!")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'name' in title:
				qs = self.queryset.exclude(name__icontains=content)
			elif 'page_title' in title:
				qs = self.queryset.exclude(page_title__icontains=content)
			elif 'http_url' in title:
				qs = self.queryset.exclude(http_url__icontains=content)
			elif 'content_type' in title:
				qs = (
					self.queryset
					.exclude(content_type__icontains=content)
				)
			elif 'cname' in title:
				qs = self.queryset.exclude(cname__icontains=content)
			elif 'webserver' in title:
				qs = self.queryset.exclude(webserver__icontains=content)
			elif 'ip_addresses' in title:
				qs = self.queryset.exclude(
					ip_addresses__address__icontains=content)
			elif 'port' in title:
				qs = (
					self.queryset
					.exclude(ip_addresses__ports__number__icontains=content)
					|
					self.queryset
					.exclude(ip_addresses__ports__service_name__icontains=content)
					|
					self.queryset
					.exclude(ip_addresses__ports__description__icontains=content)
				)
			elif 'technology' in title:
				qs = (
					self.queryset
					.exclude(technologies__name__icontains=content)
				)
			elif 'http_status' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.exclude(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.exclude(content_length=int_http_status)
				except Exception as e:
					print(e)

		return qs


class ListActivityLogsViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	serializer_class = CommandSerializer
	queryset = Command.objects.none()
	def get_queryset(self):
		req = self.request
		activity_id = req.query_params.get('activity_id')
		self.queryset = Command.objects.filter(activity__id=activity_id)
		return self.queryset


class ListScanLogsViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	serializer_class = CommandSerializer
	queryset = Command.objects.none()
	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		self.queryset = Command.objects.filter(scan_history__id=scan_id)
		return self.queryset


class ListEndpoints(APIView):
	permission_classes = [IsAuditor]
	def get(self, request, format=None):
		req = self.request

		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		subdomain_name = req.query_params.get('subdomain_name')
		pattern = req.query_params.get('pattern')

		if scan_id:
			endpoints = (
				EndPoint.objects
				.filter(scan_history__id=scan_id)
			)
		elif target_id:
			endpoints = (
				EndPoint.objects
				.filter(target_domain__id=target_id)
				.distinct()
			)
		else:
			endpoints = EndPoint.objects.all()

		if subdomain_name:
			endpoints = endpoints.filter(subdomain__name=subdomain_name)

		if pattern:
			endpoints = endpoints.filter(matched_gf_patterns__icontains=pattern)

		if 'only_urls' in req.query_params:
			endpoints_serializer = EndpointOnlyURLsSerializer(endpoints, many=True)

		else:
			endpoints_serializer = EndpointSerializer(endpoints, many=True)

		return Response({'endpoints': endpoints_serializer.data})


class EndPointViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = EndPoint.objects.none()
	serializer_class = EndpointSerializer

	def get_queryset(self):
		req = self.request

		scan_id = req.query_params.get('scan_history')
		target_id = req.query_params.get('target_id')
		url_query = req.query_params.get('query_param')
		subdomain_id = req.query_params.get('subdomain_id')
		project = req.query_params.get('project')

		endpoints_obj = EndPoint.objects.filter(scan_history__domain__project__slug=project)

		gf_tag = req.query_params.get(
			'gf_tag') if 'gf_tag' in req.query_params else None

		if scan_id:
			endpoints = (
				endpoints_obj
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		else:
			endpoints = endpoints_obj.distinct()

		if url_query:
			endpoints = (
				endpoints
				.filter(Q(target_domain__name=url_query))
				.distinct()
			)

		if gf_tag:
			endpoints = endpoints.filter(matched_gf_patterns__icontains=gf_tag)

		if target_id:
			endpoints = endpoints.filter(target_domain__id=target_id)

		if subdomain_id:
			endpoints = endpoints.filter(subdomain__id=subdomain_id)

		if 'only_urls' in req.query_params:
			self.serializer_class = EndpointOnlyURLsSerializer

		# Filter status code 404 and 0
		# endpoints = (
		# 	endpoints
		# 	.exclude(http_status=0)
		# 	.exclude(http_status=None)
		# 	.exclude(http_status=404)
		# )

		self.queryset = endpoints

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'content_length'
			if _order_col == '1':
				order_col = 'http_url'
			elif _order_col == '2':
				order_col = 'http_status'
			elif _order_col == '3':
				order_col = 'page_title'
			elif _order_col == '4':
				order_col = 'matched_gf_patterns'
			elif _order_col == '5':
				order_col = 'content_type'
			elif _order_col == '6':
				order_col = 'content_length'
			elif _order_col == '7':
				order_col = 'techs'
			elif _order_col == '8':
				order_col = 'webserver'
			elif _order_col == '9':
				order_col = 'response_time'
			if _order_direction == 'desc':
				order_col = f'-{order_col}'
			# if the search query is separated by = means, it is a specific lookup
			# divide the search query into two half and lookup
			if '=' in search_value or '&' in search_value or '|' in search_value or '>' in search_value or '<' in search_value or '!' in search_value:
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Subdomain.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
			return qs.order_by(order_col)
		return qs

	def general_lookup(self, search_value):
		return \
			self.queryset.filter(Q(http_url__icontains=search_value) |
								 Q(page_title__icontains=search_value) |
								 Q(http_status__icontains=search_value) |
								 Q(content_type__icontains=search_value) |
								 Q(webserver__icontains=search_value) |
								 Q(techs__name__icontains=search_value) |
								 Q(content_type__icontains=search_value) |
								 Q(parameters__name__icontains=search_value) |
								 Q(matched_gf_patterns__icontains=search_value))

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_url' in lookup_title:
				qs = self.queryset.filter(http_url__icontains=lookup_content)
			elif 'page_title' in lookup_title:
				qs = (
					self.queryset
					.filter(page_title__icontains=lookup_content)
				)
			elif 'content_type' in lookup_title:
				qs = (
					self.queryset
					.filter(content_type__icontains=lookup_content)
				)
			elif 'webserver' in lookup_title:
				qs = self.queryset.filter(webserver__icontains=lookup_content)
			elif 'technology' in lookup_title:
				qs = (
					self.queryset
					.filter(techs__name__icontains=lookup_content)
				)
			elif 'gf_pattern' in lookup_title:
				qs = (
					self.queryset
					.filter(matched_gf_patterns__icontains=lookup_content)
				)
			elif 'http_status' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.filter(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.filter(content_length=int_http_status)
				except Exception as e:
					print(e)
			elif 'parameter' in lookup_title:
				qs = (
					self.queryset
					.filter(parameters__name__icontains=lookup_content)
				)
		elif '>' in search_value:
			search_param = search_value.split(">")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_status' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = (
						self.queryset
						.filter(http_status__gt=int_val)
					)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(content_length__gt=int_val)
				except Exception as e:
					print(e)
		elif '<' in search_value:
			search_param = search_value.split("<")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_status' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(http_status__lt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(content_length__lt=int_val)
				except Exception as e:
					print(e)
		elif '!' in search_value:
			search_param = search_value.split("!")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_url' in lookup_title:
				qs = (
					self.queryset
					.exclude(http_url__icontains=lookup_content)
				)
			elif 'page_title' in lookup_title:
				qs = (
					self.queryset
					.exclude(page_title__icontains=lookup_content)
				)
			elif 'content_type' in lookup_title:
				qs = (
					self.queryset
					.exclude(content_type__icontains=lookup_content)
				)
			elif 'webserver' in lookup_title:
				qs = (
					self.queryset
					.exclude(webserver__icontains=lookup_content)
				)
			elif 'technology' in lookup_title:
				qs = (
					self.queryset
					.exclude(techs__name__icontains=lookup_content)
				)
			elif 'gf_pattern' in lookup_title:
				qs = (
					self.queryset
					.exclude(matched_gf_patterns__icontains=lookup_content)
				)
			elif 'http_status' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.exclude(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.exclude(content_length=int_http_status)
				except Exception as e:
					print(e)
		return qs


class SecretLeakViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	serializer_class = SecretLeakSerializer
	queryset = SecretLeak.objects.none()

	def get_queryset(self):
		req = self.request
		project = req.query_params.get('project')
		target_id = req.query_params.get('target_id')
		scan_id = req.query_params.get('scan_id')
		
		queryset = SecretLeak.objects.all()

		if project:
			queryset = queryset.filter(scan_history__domain__project__slug=project)
		if target_id:
			queryset = queryset.filter(scan_history__domain__id=target_id)
		if scan_id:
			queryset = queryset.filter(scan_history__id=scan_id)
			
		return queryset.order_by('-discovered_date')


class ScreenshotViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	queryset = Screenshot.objects.all()
	serializer_class = ScreenshotSerializer

	def get_queryset(self):
		req = self.request
		project = req.query_params.get('project')
		target_id = req.query_params.get('target_id')
		scan_id = req.query_params.get('scan_id')

		queryset = self.queryset
		if project:
			queryset = queryset.filter(scan_history__domain__project__slug=project)
		if target_id:
			queryset = queryset.filter(scan_history__domain__id=target_id)
		if scan_id:
			queryset = queryset.filter(scan_history__id=scan_id)
		
		return queryset.order_by('-created_at')


from rest_framework.permissions import AllowAny

class DirectoryViewSet(viewsets.ModelViewSet):
	permission_classes = [IsAuditor]

	queryset = EndPoint.objects.none()
	serializer_class = DirectoryFileSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_history')
		subdomain_id = req.query_params.get('subdomain_id')
		
		if not (scan_id or subdomain_id):
			return EndPoint.objects.none()

		queryset = EndPoint.objects.filter(scan_history__id=scan_id)
		if subdomain_id and subdomain_id != '0':
			queryset = queryset.filter(subdomain__id=subdomain_id)
		
		return queryset.order_by('http_url')

	def get_serializer_class(self):
		return EndPointDirectorySerializer

	def list(self, request, *args, **kwargs):
		scan_id = self.request.query_params.get('scan_history')
		subdomain_id = self.request.query_params.get('subdomain_id')

		# Handle '0' as falsy for subdomain_id
		if subdomain_id == '0':
			subdomain_id = None

		# If subdomain_id is missing, return list of subdomains that have findings
		if scan_id and not subdomain_id:
			subdomains = Subdomain.objects.filter(
				scan_history__id=scan_id,
				endpoint__isnull=False
			).distinct()
			
			results = []
			for sd in subdomains:
				results.append({
					'id': sd.id,
					'name': sd.name,
					'directory_count': EndPoint.objects.filter(scan_history__id=scan_id, subdomain=sd).count()
				})
			return Response({
				'count': len(results),
				'next': None,
				'previous': None,
				'results': results
			})
		
		return super().list(request, *args, **kwargs)




class VulnerabilityViewSet(viewsets.ModelViewSet):
	permission_classes = [IsPenetrationTester]
	serializer_class = VulnerabilitySerializer
	queryset = Vulnerability.objects.none()

	def get_queryset(self):
		req = self.request
		project = req.query_params.get('project')
		target_id = req.query_params.get('target_id')
		scan_id = req.query_params.get('scan_history')
		domain = req.query_params.get('domain')
		severity = req.query_params.get('severity')
		subdomain_id = req.query_params.get('subdomain_id')
		subdomain_name = req.query_params.get('subdomain')
		vulnerability_name = req.query_params.get('vulnerability_name')
		slug = self.request.GET.get('project', None)

		if slug:
			vulnerabilities = Vulnerability.objects.filter(scan_history__domain__project__slug=slug)
		else:
			vulnerabilities = Vulnerability.objects.all()

		if scan_id:
			qs = (
				vulnerabilities
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		elif target_id:
			qs = (
				vulnerabilities
				.filter(target_domain__id=target_id)
				.distinct()
			)
		elif subdomain_name:
			subdomains = Subdomain.objects.filter(name=subdomain_name)
			qs = (
				vulnerabilities
				.filter(subdomain__in=subdomains)
				.distinct()
			)
		else:
			qs = vulnerabilities.distinct()

		if domain:
			qs = qs.filter(Q(target_domain__name=domain)).distinct()
		if vulnerability_name:
			qs = qs.filter(Q(name=vulnerability_name)).distinct()
		if severity:
			qs = qs.filter(severity=severity)
		if subdomain_id:
			qs = qs.filter(subdomain__id=subdomain_id)
		self.queryset = qs
		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', '')
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'severity'
			if _order_col == '1':
				order_col = 'source'
			elif _order_col == '3':
				order_col = 'name'
			elif _order_col == '7':
				order_col = 'severity'
			elif _order_col == '11':
				order_col = 'http_url'
			elif _order_col == '15':
				order_col = 'open_status'

			if _order_direction == 'desc':
				order_col = f'-{order_col}'
			# if the search query is separated by = means, it is a specific lookup
			# divide the search query into two half and lookup
			operators = ['=', '&', '|', '>', '<', '!']
			if any(x in search_value for x in operators):
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Vulnerability.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
			return qs.order_by(order_col)
		return qs.order_by('-severity')

	def general_lookup(self, search_value):
		qs = (
			self.queryset
			.filter(Q(http_url__icontains=search_value) |
					Q(target_domain__name__icontains=search_value) |
					Q(template__icontains=search_value) |
					Q(template_id__icontains=search_value) |
					Q(name__icontains=search_value) |
					Q(severity__icontains=search_value) |
					Q(description__icontains=search_value) |
					Q(extracted_results__icontains=search_value) |
					Q(references__url__icontains=search_value) |
					Q(cve_ids__name__icontains=search_value) |
					Q(cwe_ids__name__icontains=search_value) |
					Q(cvss_metrics__icontains=search_value) |
					Q(cvss_score__icontains=search_value) |
					Q(type__icontains=search_value) |
					Q(open_status__icontains=search_value) |
					Q(hackerone_report_id__icontains=search_value) |
					Q(tags__name__icontains=search_value))
		)
		return qs

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'severity' in lookup_title:
				severity_value = NUCLEI_SEVERITY_MAP.get(lookup_content, -1)
				qs = (
					self.queryset
					.filter(severity=severity_value)
				)
			elif 'name' in lookup_title:
				qs = (
					self.queryset
					.filter(name__icontains=lookup_content)
				)
			elif 'http_url' in lookup_title:
				qs = (
					self.queryset
					.filter(http_url__icontains=lookup_content)
				)
			elif 'template' in lookup_title:
				qs = (
					self.queryset
					.filter(template__icontains=lookup_content)
				)
			elif 'template_id' in lookup_title:
				qs = (
					self.queryset
					.filter(template_id__icontains=lookup_content)
				)
			elif 'cve_id' in lookup_title or 'cve' in lookup_title:
				qs = (
					self.queryset
					.filter(cve_ids__name__icontains=lookup_content)
				)
			elif 'cwe_id' in lookup_title or 'cwe' in lookup_title:
				qs = (
					self.queryset
					.filter(cwe_ids__name__icontains=lookup_content)
				)
			elif 'cvss_metrics' in lookup_title:
				qs = (
					self.queryset
					.filter(cvss_metrics__icontains=lookup_content)
				)
			elif 'cvss_score' in lookup_title:
				qs = (
					self.queryset
					.filter(cvss_score__exact=lookup_content)
				)
			elif 'type' in lookup_title:
				qs = (
					self.queryset
					.filter(type__icontains=lookup_content)
				)
			elif 'tag' in lookup_title:
				qs = (
					self.queryset
					.filter(tags__name__icontains=lookup_content)
				)
			elif 'status' in lookup_title:
				open_status = lookup_content == 'open'
				qs = (
					self.queryset
					.filter(open_status=open_status)
				)
			elif 'description' in lookup_title:
				qs = (
					self.queryset
					.filter(Q(description__icontains=lookup_content) |
							Q(template__icontains=lookup_content) |
							Q(extracted_results__icontains=lookup_content))
				)
		elif '!' in search_value:
			search_param = search_value.split("!")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'severity' in lookup_title:
				severity_value = NUCLEI_SEVERITY_MAP.get(lookup_title, -1)
				qs = (
					self.queryset
					.exclude(severity=severity_value)
				)
			elif 'name' in lookup_title:
				qs = (
					self.queryset
					.exclude(name__icontains=lookup_content)
				)
			elif 'http_url' in lookup_title:
				qs = (
					self.queryset
					.exclude(http_url__icontains=lookup_content)
				)
			elif 'template' in lookup_title:
				qs = (
					self.queryset
					.exclude(template__icontains=lookup_content)
				)
			elif 'template_id' in lookup_title:
				qs = (
					self.queryset
					.exclude(template_id__icontains=lookup_content)
				)
			elif 'cve_id' in lookup_title or 'cve' in lookup_title:
				qs = (
					self.queryset
					.exclude(cve_ids__icontains=lookup_content)
				)
			elif 'cwe_id' in lookup_title or 'cwe' in lookup_title:
				qs = (
					self.queryset
					.exclude(cwe_ids__icontains=lookup_content)
				)
			elif 'cvss_metrics' in lookup_title:
				qs = (
					self.queryset
					.exclude(cvss_metrics__icontains=lookup_content)
				)
			elif 'cvss_score' in lookup_title:
				qs = (
					self.queryset
					.exclude(cvss_score__exact=lookup_content)
				)
			elif 'type' in lookup_title:
				qs = (
					self.queryset
					.exclude(type__icontains=lookup_content)
				)
			elif 'tag' in lookup_title:
				qs = (
					self.queryset
					.exclude(tags__icontains=lookup_content)
				)
			elif 'status' in lookup_title:
				open_status = lookup_content == 'open'
				qs = (
					self.queryset
					.exclude(open_status=open_status)
				)
			elif 'description' in lookup_title:
				qs = (
					self.queryset
					.exclude(Q(description__icontains=lookup_content) |
							 Q(template__icontains=lookup_content) |
							 Q(extracted_results__icontains=lookup_content))
				)

		elif '>' in search_value:
			search_param = search_value.split(">")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'cvss_score' in lookup_title:
				try:
					val = float(lookup_content)
					qs = self.queryset.filter(cvss_score__gt=val)
				except Exception as e:
					print(e)

		elif '<' in search_value:
			search_param = search_value.split("<")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'cvss_score' in lookup_title:
				try:
					val = int(lookup_content)
					qs = self.queryset.filter(cvss_score__lt=val)
				except Exception as e:
					print(e)

		return qs

class ReportSettingsAPIView(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_REPORT

	def get(self, request):
		report_setting = VulnerabilityReportSetting.objects.first()
		if not report_setting:
			# Create default settings if not exists
			report_setting = VulnerabilityReportSetting.objects.create()
		serializer = VulnerabilityReportSettingSerializer(report_setting)
		return Response(serializer.data)

	def post(self, request):
		report_setting = VulnerabilityReportSetting.objects.first()
		if not report_setting:
			report_setting = VulnerabilityReportSetting.objects.create()
		serializer = VulnerabilityReportSettingSerializer(report_setting, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class NotificationSettingsAPIView(APIView):
	permission_classes = [HasPermission]
	permission_required = PERM_MODIFY_SCAN_CONFIGURATIONS

	def get(self, request):
		notification = Notification.objects.first()
		if not notification:
			notification = Notification.objects.create()
		serializer = NotificationSettingsSerializer(notification)
		return Response(serializer.data)

	def post(self, request):
		notification = Notification.objects.first()
		serializer = NotificationSettingsSerializer(notification, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			# Send test messages if requested or on every save (to match legacy)
			if request.data.get('send_test', True):
				send_slack_message('*reNgine*\nCongratulations! your notification services are working.')
				send_lark_message('*reNgine*\nCongratulations! your notification services are working.')
				send_telegram_message('*reNgine*\nCongratulations! your notification services are working.')
				send_discord_message('**reNgine**\nCongratulations! your notification services are working.')
			return Response({'status': True, 'message': 'Notification settings updated and test message sent.'})
		return Response(serializer.errors, status=400)

class MobileMediaServeView(APIView):
	permission_classes = [AllowAny]
	def get(self, request):
		#logger.warning(f"!!! MobileMediaServeView HIT !!! User authenticated: {request.user.is_authenticated}")
		path = request.query_params.get('path')
		#logger.warning(f"!!! Path requested: {path} !!!")
		if not path:
			return Response({'error': 'Path is required'}, status=status.HTTP_400_BAD_REQUEST)
		
		# Normalize path
		if path.startswith(settings.MEDIA_ROOT):
			path = os.path.relpath(path, settings.MEDIA_ROOT)
		elif path.startswith('/usr/src/scan_results'):
			path = os.path.relpath(path, '/usr/src/scan_results')
		
		if path.startswith('scan_results/'):
			path = path[len('scan_results/'):]
		elif path.startswith('media/'):
			path = path[len('media/'):]
		elif path.startswith('/media/'):
			path = path[len('/media/'):]
		
		path = path.lstrip('/')
		file_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, path))
		
		#logger.info(f"MobileMediaServeView: path={path}, file_path={file_path}, MEDIA_ROOT={settings.MEDIA_ROOT}")
		
		# Security check
		if not is_safe_path(settings.MEDIA_ROOT, file_path):
			logger.error(f"is_safe_path failed for {file_path}")
			raise Http404("File not found")
			
		if os.path.exists(file_path):
			if os.path.isdir(file_path):
				raise Http404("File not found")
				
			content_type, _ = mimetypes.guess_type(file_path)
			#logger.warning(f"!!! MobileMediaServeView: Returning file with content_type={content_type} !!!")
			return FileResponse(open(file_path, 'rb'), content_type=content_type)
		else:
			logger.error(f"File not found: {file_path}")
			raise Http404("File not found")


class SystemHealthAPIView(APIView):
	permission_classes = [IsPenetrationTester]

	def get(self, request):
		import shutil
		import os
		import time
		from django.db import connection

		# 1. Database Health
		db_start = time.time()
		db_up = True
		try:
			with connection.cursor() as cursor:
				cursor.execute("SELECT 1")
		except Exception:
			db_up = False
		db_latency = int((time.time() - db_start) * 1000)

		# 2. Worker Status (Temporal orchestrator)
		try:
			import asyncio
			from reNgine.temporal_client import TemporalClientProvider
			_loop = asyncio.new_event_loop()
			asyncio.set_event_loop(_loop)
			try:
				_client = _loop.run_until_complete(TemporalClientProvider.get_client())
				workers_online = _client is not None
			finally:
				_loop.close()
			worker_count = 1 if workers_online else 0
		except Exception:
			workers_online = False
			worker_count = 0

		# 3. Disk Usage
		try:
			total, used, free = shutil.disk_usage("/")
			disk_used_percent = int(100 * used / total)
		except Exception:
			disk_used_percent = 0
			free = 0

		# 4. System Load
		try:
			load_avg = os.getloadavg()
		except AttributeError:
			load_avg = (0.0, 0.0, 0.0)

		return Response({
			"status": "online" if db_up and workers_online else "degraded",
			"database": {
				"status": "up" if db_up else "down",
				"latency_ms": db_latency
			},
			"workers": {
				"status": "online" if workers_online else "offline",
				"count": worker_count
			},
			"disk": {
				"used_percent": disk_used_percent,
				"free_gb": free // (2**30)
			},
			"load": load_avg[0],
			"timestamp": time.time()
		})


class GetScanGraphData(APIView):
	"""Fetch Cytoscape-compatible graph data for a specific scan."""
	permission_classes = [IsAuditor]
	def get(self, request, scan_id):
		graph = Neo4jManager()
		data = graph.get_cytoscape_json(scan_id)
		graph.close()
		return Response(data)

class GetTargetGraphData(APIView):
	"""Fetch Cytoscape-compatible graph data for an entire target."""
	permission_classes = [IsAuditor]
	def get(self, request, target_id):
		target = get_object_or_404(Domain, id=target_id)
		graph = Neo4jManager()
		data = graph.get_target_graph_data(target.name)
		graph.close()
		return Response(data)

class GetNodeDetails(APIView):
	"""Fetch detailed metadata for a specific graph node."""
	permission_classes = [IsAuditor]
	def get(self, request, node_id):
		graph = Neo4jManager()
		data = graph.get_node_details(node_id)
		graph.close()
		return Response(data)

class GetSystemLogs(APIView):
	"""Fetch the tail of the system logs. Restricted to SysAdmins."""
	permission_classes = [IsSysAdmin]
	def get(self, request):
		# SECURITY: Path is hardcoded and validated to prevent directory traversal
		log_file = os.path.normpath(os.path.join(settings.BASE_DIR, 'scan.log'))

		# Ensure we only read from the allowed directory
		if not log_file.startswith(os.path.normpath(settings.BASE_DIR)):
			return Response({'status': False, 'message': 'Forbidden log path'}, status=403)

		if not os.path.exists(log_file):
			return Response({'status': False, 'message': 'Log file not found'}, status=404)

		try:
			with open(log_file, 'r') as f:
				# Efficiently read last ~50KB (~500 lines)
				f.seek(0, os.SEEK_END)
				filesize = f.tell()
				offset = min(filesize, 50000)
				f.seek(filesize - offset)
				# read() then splitlines() to handle partial first line
				data = f.read()
				lines = data.splitlines()
				# Return at most 500 lines
				return Response({'status': True, 'logs': lines[-500:]})
		except Exception as e:
			logger.error(f"Error reading system logs: {str(e)}")
			return Response({'status': False, 'message': 'Internal error reading logs'}, status=500)


class LaunchADAssessmentFromSubdomain(APIView):
	"""Create an ADAssessment pre-populated from a Subdomain's root domain.

	The AD Intelligence plugin must be installed. The assessment is created
	in PENDING state; users start it explicitly from the AD plugin dashboard.
	This view intentionally does NOT start the workflow automatically to avoid
	unintended automated enumeration activity.
	"""
	permission_classes = [HasPermission]
	permission_required = PERM_INITATE_SCANS_SUBSCANS

	def post(self, request):
		subdomain_id = request.data.get('subdomain_id')
		if not subdomain_id:
			return Response(
				{'error': 'subdomain_id is required.'},
				status=HTTP_400_BAD_REQUEST,
			)
		try:
			subdomain = Subdomain.objects.select_related(
				'scan_history__domain'
			).get(id=subdomain_id)
		except Subdomain.DoesNotExist:
			return Response(
				{'error': f'Subdomain {subdomain_id} not found.'},
				status=HTTP_400_BAD_REQUEST,
			)

		target_domain = subdomain.scan_history.domain.name

		try:
			from plugins_data.active_directory.backend.models import ADAssessment as _ADAssessment
		except ImportError:
			return Response(
				{'error': 'AD Intelligence plugin is not installed.'},
				status=HTTP_400_BAD_REQUEST,
			)

		assessment = _ADAssessment.objects.create(
			name=f'AD Assessment — {target_domain}',
			target_domain=target_domain,
			status='PENDING',
			created_by=request.user,
		)
		return Response({
			'assessment_id': assessment.id,
			'assessment_name': assessment.name,
			'target_domain': target_domain,
			'status': 'created',
		}, status=status.HTTP_201_CREATED)
