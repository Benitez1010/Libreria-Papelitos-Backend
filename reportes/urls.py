from django.urls import path
from .views import ReporteExistenciasUbicacionView, ProductosSinMovimientoView

urlpatterns = [
    path('reportes/existencias-ubicacion/', ReporteExistenciasUbicacionView.as_view(), name='reporte-existencias-ubicacion'),
    path('reportes/sin-movimiento/', ProductosSinMovimientoView.as_view(), name='reporte-sin-movimiento'),
]