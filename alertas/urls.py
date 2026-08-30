from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DestinatarioCorreoViewSet

router = DefaultRouter()
router.register(r'destinatarios', DestinatarioCorreoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]