from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer, MovimientoInventarioSerializer
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework import permissions
from .models import MovimientoInventario
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from alertas.models import ConfiguracionAlerta
from alertas.utils import disparar_alerta_email 

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
    queryset = Producto.objects.filter(descontinuado=False).order_by('nombre')
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
            # LÓGICA DE REACTIVACIÓN
            if producto_existente.descontinuado:
                producto_existente.descontinuado = False
                if 'cantidad_inicial' in data:
                    producto_existente.stock_bodega += int(data['cantidad_inicial'])
                if 'stock_minimo' in data:
                    producto_existente.stock_minimo = int(data['stock_minimo'])
                producto_existente.save()
                
                serializer = self.get_serializer(producto_existente)
                return Response({
                    "success": True,
                    "message": f"El producto '{nombre}' estaba descontinuado y ha sido reactivado con éxito.",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({
            "success": True,
            "message": "Producto actualizado con éxito.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "error_type": "VALIDATION_ERROR",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        try:
            instancia.delete()
            return Response({
                "success": True,
                "message": "Producto eliminado con éxito."
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            mensaje = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({
                "success": False,
                "message": mensaje
            }, status=status.HTTP_400_BAD_REQUEST)
        except ProtectedError:
            instancia.descontinuado = True
            instancia.save()
            return Response({
                "success": True,
                "message": "El producto tiene historial registrado. Fue descontinuado lógicamente y oculto del catálogo."
            }, status=status.HTTP_200_OK)

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

        # Criterio SEG-07: Justificación obligatoria en mermas/ajustes
        if tipo_movimiento_real in [MovimientoInventario.TipoMovimiento.DAÑO, MovimientoInventario.TipoMovimiento.CORRECCION]:
            if not justificacion:
                return Response({
                    "success": False,
                    "message": "Es obligatorio ingresar un comentario detallado justificando la operación."
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                movimientos_registrados = []
                # Variable para rastrear si ALGÚN correo se envió en este bloque
                alerta_enviada = False

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
                    
                    estado_notificacion = None
                    if requiere_alerta:
                        ubicacion_alerta = item.get('origen') if tipo_movimiento_real in [MovimientoInventario.TipoMovimiento.SALIDA, MovimientoInventario.TipoMovimiento.DAÑO, MovimientoInventario.TipoMovimiento.TRASLADO] else item.get('destino')
                        
                        # Disparamos la alerta de manera síncrona para capturar la respuesta real
                        resultado_envio = disparar_alerta_email(
                            producto.id, producto.nombre, producto.categoria.nombre, 
                            ubicacion_alerta, producto.stock_total, producto.stock_minimo
                        )
                        
                        if resultado_envio:
                            alerta_enviada = True
                            estado_notificacion = "enviada"
                        elif not ConfiguracionAlerta.get_config().notificaciones_globales_activas:
                            estado_notificacion = "desactivada"
                        else:
                            estado_notificacion = "no_enviada"
                    
                    movimientos_registrados.append({
                        "producto": producto.nombre,
                        "cantidad": movimiento.cantidad,
                        "nuevo_stock_bodega": producto.stock_bodega,
                        "nuevo_stock_vitrina": producto.stock_vitrina,
                        "requiere_alerta": requiere_alerta,
                        "estado_notificacion": estado_notificacion
                    })

            # --- EVALUACIÓN FINAL DEL MENSAJE PARA REACT ---
            mensaje_exito = f"Transacción de tipo '{tipo_contexto.upper()}' procesada con éxito."
            if alerta_enviada:
                mensaje_exito += " Se ha enviado un correo al destinatario del stock crítico."

            return Response({
                "success": True,
                "message": mensaje_exito,
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

class HistorialMovimientosView(APIView):
    """
    SEG-07: Lista el historial de movimientos con trazabilidad completa.
    Requiere sesión activa y expone el campo 'responsable'.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        movimientos = MovimientoInventario.objects.all().select_related('producto', 'usuario').order_by('-fecha_hora')
        serializer = MovimientoInventarioSerializer(movimientos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)