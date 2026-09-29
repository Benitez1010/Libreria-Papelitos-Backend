from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from inventario.models import Producto
from .serializers import ReporteExistenciasSerializer

class ReporteExistenciasUbicacionView(APIView):
    """
    REP-01: Reporte de existencias por ubicación (Bodega, Vitrina y Consolidado).
    Permite filtrar por id de categoría mediante query param ?categoria=<id>.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categoria_id = request.query_params.get('categoria', None)

        # Consulta optimizada con select_related para cumplir el tiempo de respuesta (< 5 segundos)
        queryset = Producto.objects.select_related('categoria').all().order_by('nombre')

        if categoria_id and categoria_id != 'todas':
            queryset = queryset.filter(categoria_id=categoria_id)

        serializer = ReporteExistenciasSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)