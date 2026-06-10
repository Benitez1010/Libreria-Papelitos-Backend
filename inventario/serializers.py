from rest_framework import serializers
from .models import Categoria, Producto

class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializer para el manejo de categorías.
    Se encarga de transformar los datos para el listado, creación y edición,
    aplicando reglas para evitar nombres duplicados o vacíos.
    """
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

    def validate_nombre(self, value):
        # 1. Limpia los espacios de los lados y transforma a mayúsculas para homogeneizar
        nombre_limpio = value.strip().upper()
        
        # 2. Validar que no se envíe un campo vacío o solo con espacios
        if not nombre_limpio:
            raise serializers.ValidationError("El nombre de la categoría no puede estar vacío.")

        # 3. Criterio de Aceptación: Validar que no se repitan nombres existentes en la base de datos
        # Se obtiene el ID si se está editando (para no validarse contra sí mismo), si es nuevo se mantiene como None
        instance_id = self.instance.id if self.instance else None
        if Categoria.objects.filter(nombre=nombre_limpio).exclude(id=instance_id).exists():
            raise serializers.ValidationError("Esta categoría ya se encuentra registrada.")
            
        return nombre_limpio
    
class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializer para la gestión del catálogo de productos.
    Mapea las existencias por ubicación y expone campos calculados listos para el Frontend.
    """
    # Campo de solo lectura para mostrar el texto de la categoría en las tablas de React
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    class Meta:
        model = Producto
        # El campo 'categoria' recibe el ID al guardar, mientras que 'categoria_nombre' se usa para mostrar el texto al listar
        fields = ['id', 'nombre', 'categoria', 'categoria_nombre', 'stock_bodega', 'stock_vitrina', 'stock_minimo', 'stock_total']