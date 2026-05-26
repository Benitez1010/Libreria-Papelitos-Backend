from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventario.views import CategoriaViewSet, ProductoViewSet

# Se define un router específico para los endpoints de inventario
router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto') 
urlpatterns = [
    path('', include(router.urls)),
]