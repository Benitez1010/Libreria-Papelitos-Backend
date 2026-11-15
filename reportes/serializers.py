from rest_framework import serializers
from inventario.models import Producto

class ReporteExistenciasSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    total_consolidado = serializers.IntegerField(source='stock_total', read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre',
            'categoria',
            'categoria_nombre',
            'stock_bodega',
            'stock_vitrina',
            'total_consolidado',
        ]


class ReporteStockCriticoSerializer(serializers.ModelSerializer):
    """
    REP-06: Productos cuyo stock total es menor o igual al stock mínimo.
    Requiere que el queryset traiga anotado el campo cantidad_sugerida.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    total_consolidado = serializers.IntegerField(source='stock_total', read_only=True)
    cantidad_sugerida = serializers.IntegerField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre',
            'categoria',
            'categoria_nombre',
            'stock_bodega',
            'stock_vitrina',
            'total_consolidado',
            'stock_minimo',
            'cantidad_sugerida',
        ]