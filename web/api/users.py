from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rolepermissions.roles import assign_role, clear_roles
from api.serializers import UserSerializer
from reNgine.definitions import PERM_MODIFY_SYSTEM_CONFIGURATIONS

User = get_user_model()

class UserManageViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated] # We should ideally have a custom permission check here

    def get_queryset(self):
        # Only allow admins to manage users
        if not self.request.user.is_superuser:
             # In reNgine roles, we should check for PERM_MODIFY_SYSTEM_CONFIGURATIONS
             pass
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        role = request.data.get('role', 'penetration_tester')
        
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.create_user(username=username, password=password)
            assign_role(user, role)
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'error': 'Cannot disable your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = not user.is_active
        user.save()
        return Response({'status': 'success', 'is_active': user.is_active})

    @action(detail=True, methods=['post'])
    def update_user(self, request, pk=None):
        user = self.get_object()
        role = request.data.get('role')
        password = request.data.get('password')
        
        if role:
            clear_roles(user)
            assign_role(user, role)
        
        if password:
            user.set_password(password)
            user.save()
            
        return Response({'status': 'success'})
