from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework import permissions
from .models import MovimientoInventario
from django.db import transaction
from django.core.exceptions import ValidationError
from alertas.utils import disparar_alerta_email # <-- Importación del motor de alertas


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    Controlador CRUD completo para las categorías.
    Centraliza las operaciones de listado, creación, edición y eliminación.
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    def create(self, request, *args, **kwargs):
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Categoría registrada con éxito.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """INV-03: Bloqueo de eliminación y captura de validación del modelo."""
        instancia = self.get_object()
        try:
            instancia.delete()
            return Response({
                "success": True,
                "message": "Categoría eliminada con éxito."
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            mensaje = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({
                "success": False,
                "message": mensaje
            }, status=status.HTTP_400_BAD_REQUEST)
    
class ProductoViewSet(viewsets.ModelViewSet):
    """
    Controlador CRUD completo para el catálogo de productos.
    Incluye lógica de asistencia para inventario inicial y alertas preventivas de duplicados.
    """
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def create(self, request, *args, **kwargs):
        """Maneja el registro de nuevos productos verificando que no existan previamente."""
        data = request.data.copy()
        # Si el usuario ingresa una cantidad inicial, se asigna automáticamente como stock de Bodega
        if 'cantidad_inicial' in data:
            data['stock_bodega'] = data['cantidad_inicial']

        # Criterio de Aceptación: Validar si el artículo ya existe ignorando mayúsculas/minúsculas
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

class ProcesarMovimientoView(APIView):
    """
    Vista transaccional que procesa listas de productos facturados o trasladados desde React.
    Garantiza consistencia en bloque, aplicando la regla de: 'O se guardan todos o ninguno'.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        tipo_contexto = data.get('tipo_contexto')
        justificacion = data.get('justificacion', '').strip()
        detalles = data.get('detalles', [])

        if not detalles:
            return Response({
                "success": False,
                "message": "Debe seleccionar al menos un producto para registrar la transacción."
            }, status=status.HTTP_400_BAD_REQUEST)

        mapeo_tipos = {
            'venta': MovimientoInventario.TipoMovimiento.SALIDA,
            'entrada': MovimientoInventario.TipoMovimiento.ENTRADA,
            'traslado': MovimientoInventario.TipoMovimiento.TRASLADO,
            'daño': MovimientoInventario.TipoMovimiento.DAÑO,
            'correccion': MovimientoInventario.TipoMovimiento.CORRECCION
        }

        tipo_movimiento_real = mapeo_tipos.get(tipo_contexto)
        if not tipo_movimiento_real:
            return Response({
                "success": False,
                "message": "El contexto de la transacción enviado no es válido."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                movimientos_registrados = []

                for item in detalles:
                    try:
                        producto = Producto.objects.get(id=item.get('producto_id'))
                    except Producto.DoesNotExist:
                        raise ValidationError(f"El producto con ID {item.get('producto_id')} no existe en el catálogo.")

                    movimiento = MovimientoInventario(
                        producto=producto,
                        tipo=tipo_movimiento_real,
                        cantidad=int(item.get('cantidad', 0)),
                        origen=item.get('origen'),
                        destino=item.get('destino'),
                        justificacion=justificacion,
                        usuario=request.user 
                    )
                    
                    # Al guardar se calculan los nuevos saldos
                    movimiento.save()
                    
                    # --- LÓGICA DE ALERTA ALT-05 ---
                    requiere_alerta = producto.stock_total <= producto.stock_minimo
                    
                    if requiere_alerta:
                        # Determinamos dinámicamente si la alerta fue provocada en Bodega o Vitrina
                        ubicacion_alerta = item.get('origen') if tipo_movimiento_real in [MovimientoInventario.TipoMovimiento.SALIDA, MovimientoInventario.TipoMovimiento.DAÑO, MovimientoInventario.TipoMovimiento.TRASLADO] else item.get('destino')
                        
                        # transaction.on_commit asegura que el hilo del correo arranque SOLO si no hubo errores en el bloque atomic
                        # Usamos argumentos por defecto (p_id=producto.id, etc) para blindar el contexto en ciclos for
                        transaction.on_commit(
                            lambda p_id=producto.id, p_nom=producto.nombre, c_nom=producto.categoria.nombre, 
                                   u=ubicacion_alerta, s_act=producto.stock_total, s_min=producto.stock_minimo: 
                            disparar_alerta_email(p_id, p_nom, c_nom, u, s_act, s_min)
                        )
                    
                    movimientos_registrados.append({
                        "producto": producto.nombre,
                        "cantidad": movimiento.cantidad,
                        "nuevo_stock_bodega": producto.stock_bodega,
                        "nuevo_stock_vitrina": producto.stock_vitrina,
                        "requiere_alerta": requiere_alerta
                    })

            return Response({
                "success": True,
                "message": f"Transacción de tipo '{tipo_contexto.upper()}' procesada con éxito.",
                "detalles_procesados": movimientos_registrados
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            mensaje_limpio = str(e)
            if hasattr(e, 'message_dict') and '__all__' in e.message_dict:
                mensaje_limpio = e.message_dict['__all__'][0]
            elif hasattr(e, 'messages'):
                mensaje_limpio = e.messages[0]

            return Response({
                "success": False,
                "error_type": "BUSINESS_RULE_ERROR",
                "message": mensaje_limpio 
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Fallo crítico en el servidor: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)