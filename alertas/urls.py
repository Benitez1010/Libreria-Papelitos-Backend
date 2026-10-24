from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DestinatarioCorreoViewSet, HistorialAlertaViewSet, ConfiguracionGlobalView

router = DefaultRouter()
router.register(r'destinatarios', DestinatarioCorreoViewSet)
router.register(r'historial-alertas', HistorialAlertaViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('configuracion/', ConfiguracionGlobalView.as_view(), name='configuracion_global'),
]