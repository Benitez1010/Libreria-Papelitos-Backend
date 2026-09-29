from django.urls import path
from .views import ReporteExistenciasUbicacionView

urlpatterns = [
    path('reportes/existencias-ubicacion/', ReporteExistenciasUbicacionView.as_view(), name='reporte-existencias-ubicacion'),
]