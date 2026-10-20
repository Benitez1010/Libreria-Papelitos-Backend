from django.urls import path
from .views import ReporteExistenciasUbicacionView, ProductosSinMovimientoView
from .views import ReporteStockCriticoView

urlpatterns = [
    path('reportes/existencias-ubicacion/', ReporteExistenciasUbicacionView.as_view(), name='reporte-existencias-ubicacion'),
    path('reportes/sin-movimiento/', ProductosSinMovimientoView.as_view(), name='reporte-sin-movimiento'),
    path('reportes/stock-critico/', ReporteStockCriticoView.as_view(), name='reporte-stock-critico'),
]