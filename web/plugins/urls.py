from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PluginViewSet

router = DefaultRouter()
router.register(r'', PluginViewSet, basename='plugin')

urlpatterns = [
    path('', include(router.urls)),
]
