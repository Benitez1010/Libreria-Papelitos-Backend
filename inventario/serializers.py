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

    # Validación estricta del backend para garantizar que el stock mínimo sea mayor a cero
    def validate_stock_minimo(self, value):
        if value <= 0:
            raise serializers.ValidationError("Ingrese una cantidad numérica válida mayor a cero")
        return value

    def validate(self, data):
        # Tomar nombre (nuevo o el actual)
        nombre = data.get('nombre')
        if not nombre and self.instance:
            nombre = self.instance.nombre

        # Tomar categoría (nueva o la actual)
        categoria = data.get('categoria')
        categoria_id = getattr(categoria, 'id', categoria)
        if categoria_id is None and self.instance:
            categoria_id = self.instance.categoria_id

        if nombre and categoria_id:
            nombre_limpio = nombre.strip()
            data['nombre'] = nombre_limpio

            # Validar duplicados ignorando mayúsculas/minúsculas dentro de la misma categoría
            query = Producto.objects.filter(nombre__iexact=nombre_limpio, categoria_id=categoria_id)
            if self.instance:
                query = query.exclude(id=self.instance.id)

            if query.exists():
                raise serializers.ValidationError({
                    "nombre": f"El producto '{nombre_limpio}' ya existe en esta categoría."
                })

        return data