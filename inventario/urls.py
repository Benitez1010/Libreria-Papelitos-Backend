from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventario.views import (
    CategoriaViewSet, 
    ProductoViewSet, 
    ProcesarMovimientoView, 
    HistorialMovimientosView
)

# Se define un router específico para los endpoints de inventario
router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto') 

urlpatterns = [
    # Incluye todas las URL generadas automáticamente por el router superior (categorias, productos)
    path('', include(router.urls)),
    
    # EndPoint para consultar el historial de movimientos de inventario (SEG-07)
    path('movimientos/', HistorialMovimientosView.as_view(), name='historial-movimientos'),
    
    # EndPoint personalizado de tipo APIView dedicado a procesar las listas de movimientos masivos
    path('movimientos/procesar/', ProcesarMovimientoView.as_view(), name='procesar-movimiento-inventario'),
]