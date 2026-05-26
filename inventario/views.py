from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    # Redefinimos el método de creación para personalizar el mensaje de éxito del criterio de aceptación
    def create(self, request, *args, **kwargs):
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Criterio de Aceptación: Mensaje de éxito explícito tras el guardado
            return Response({
                "success": True,
                "message": "Categoría registrada con éxito.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if 'cantidad_inicial' in data:
            data['stock_bodega'] = data['cantidad_inicial']

        # Criterio de Aceptación: Validar la unicidad ANTES de procesar
        nombre = data.get('nombre', '')
        categoria_id = data.get('categoria')
        
        producto_existente = Producto.objects.filter(nombre__iexact=nombre, categoria_id=categoria_id).first()
        
        if producto_existente:
            # Enviamos una respuesta con un código de error específico y un mensaje
            return Response({
                "success": False,
                "error_type": "PRODUCTO_DUPLICADO",
                "message": f"El producto '{nombre}' ya existe en esta categoría. ¿Deseas ir a actualizar su stock?",
                "producto_id": producto_existente.id
            }, status=status.HTTP_400_BAD_REQUEST)

        # Si no existe, procedemos con el flujo normal
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Producto registrado con éxito en el catálogo.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            "success": False,
            "error_type": "VALIDATION_ERROR",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)