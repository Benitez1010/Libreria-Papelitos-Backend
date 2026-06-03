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

class ProcesarMovimientoView(APIView):
    # Forzamos seguridad por token y bloqueamos accesos a usuarios no logueados
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        tipo_contexto = data.get('tipo_contexto') # venta, entrada, traslado, daño, correccion
        justificacion = data.get('justificacion', '').strip()
        detalles = data.get('detalles', []) # Arreglo de productos elegidos en React

        if not detalles:
            return Response({
                "success": False,
                "message": "Debe seleccionar al menos un producto para registrar la transacción."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mapeo del contexto del frontend al Tipo de Movimiento real del backend
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
            # PROTECCIÓN EN BLOQUE ATÓMICO: Todo o nada
            with transaction.atomic():
                movimientos_registrados = []

                for item in detalles:
                    try:
                        producto = Producto.objects.get(id=item.get('producto_id'))
                    except Producto.DoesNotExist:
                        raise ValidationError(f"El producto con ID {item.get('producto_id')} no existe en el catálogo.")

                    # Construimos la instancia del movimiento leyendo las variables enviadas por React
                    movimiento = MovimientoInventario(
                        producto=producto,
                        tipo=tipo_movimiento_real,
                        cantidad=int(item.get('cantidad', 0)),
                        origen=item.get('origen'),
                        destino=item.get('destino'),
                        justificacion=justificacion,
                        usuario=request.user # Django extrae de forma segura el usuario del Token
                    )
                    
                    # Ejecuta clean() y save() nativo (aquí restará o sumará stock y validará stock negativo)
                    movimiento.save()
                    
                    # Guardamos referencias para la respuesta del JSON informativo
                    movimientos_registrados.append({
                        "producto": producto.nombre,
                        "cantidad": movimiento.cantidad,
                        "nuevo_stock_bodega": producto.stock_bodega,
                        "nuevo_stock_vitrina": producto.stock_vitrina,
                        "requiere_alerta": producto.stock_total <= producto.stock_minimo
                    })

            # Si el bucle termina con éxito, se confirma la transacción en la base de datos
            return Response({
                "success": True,
                "message": f"Transacción de tipo '{tipo_contexto.upper()}' procesada con éxito.",
                "detalles_procesados": movimientos_registrados
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Si el error viene agrupado en '__all__' por el método clean() del modelo, extraemos el texto limpio
            mensaje_limpio = str(e)
            if hasattr(e, 'message_dict') and '__all__' in e.message_dict:
                mensaje_limpio = e.message_dict['__all__'][0]
            elif hasattr(e, 'messages'):
                mensaje_limpio = e.messages[0]

            return Response({
                "success": False,
                "error_type": "BUSINESS_RULE_ERROR",
                "message": mensaje_limpio # Enviará "Existencias insuficientes para realizar la operación."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Fallo crítico en el servidor: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)