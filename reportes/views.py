from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication
from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q
from inventario.models import Producto, MovimientoInventario
from .serializers import ReporteExistenciasSerializer

class ProductosSinMovimientoView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fecha_limite = timezone.now() - timedelta(days=90)

        productos_con_salidas = MovimientoInventario.objects.filter(
            tipo=MovimientoInventario.TipoMovimiento.SALIDA,
            fecha_hora__gte=fecha_limite
        ).values_list('producto_id', flat=True)

        productos_estancados = Producto.objects.exclude(
            id__in=productos_con_salidas
        ).annotate(
            ultima_venta=Max(
                'movimientos__fecha_hora',
                filter=Q(movimientos__tipo=MovimientoInventario.TipoMovimiento.SALIDA)
    )
        ).select_related('categoria').order_by('categoria__nombre', 'nombre')

        resultados = {}
        
        for producto in productos_estancados:
            categoria_nombre = producto.categoria.nombre if producto.categoria else 'Sin Categoría Asignada'
            
            if categoria_nombre not in resultados:
                resultados[categoria_nombre] = []
            
            resultados[categoria_nombre].append({
                'id': producto.id,
                'nombre': producto.nombre,
                'stock_bodega': producto.stock_bodega,
                'stock_vitrina': producto.stock_vitrina,
                'stock_total': producto.stock_total,
                'ultimo_movimiento': producto.ultima_venta
            })

        return Response(resultados)

class ReporteExistenciasUbicacionView(APIView):
    """
    REP-01: Reporte de existencias por ubicación (Bodega, Vitrina y Consolidado).
    Permite filtrar por id de categoría mediante query param ?categoria=<id>.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        categoria_id = request.query_params.get('categoria', None)

        # Consulta optimizada con select_related para cumplir el tiempo de respuesta (< 5 segundos)
        queryset = Producto.objects.select_related('categoria').all().order_by('nombre')

        if categoria_id and categoria_id != 'todas':
            queryset = queryset.filter(categoria_id=categoria_id)

        serializer = ReporteExistenciasSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)