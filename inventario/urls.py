from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventario.views import CategoriaViewSet, ProductoViewSet, ProcesarMovimientoView

# Se define un router específico para los endpoints de inventario
router = DefaultRouter()

# Registra las rutas del CRUD completo para categorías y productos (Listar, Crear, Editar, Eliminar)
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto') 
urlpatterns = [
    # Incluye todas las URL generadas automáticamente por el router superior
    path('', include(router.urls)),
    # EndPoint personalizado de tipo APIView dedicado a procesar las listas de movimientos masivos
    path('movimientos/procesar/', ProcesarMovimientoView.as_view(), name='procesar-movimiento-inventario'),
]