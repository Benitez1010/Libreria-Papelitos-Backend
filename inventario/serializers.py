from rest_framework import serializers
from .models import Categoria, Producto

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

    def validate_nombre(self, value):
        # 1. Limpiar espacios extras en los extremos
        nombre_limpio = value.strip().upper()
        
        # 2. Validar que no se envíe un campo vacío o solo con espacios
        if not nombre_limpio:
            raise serializers.ValidationError("El nombre de la categoría no puede estar vacío.")

        # 3. Criterio de Aceptación: Validar que no se repitan nombres existentes
        # Se excluye el objeto actual
        instance_id = self.instance.id if self.instance else None
        if Categoria.objects.filter(nombre=nombre_limpio).exclude(id=instance_id).exists():
            raise serializers.ValidationError("Esta categoría ya se encuentra registrada.")
            
        return nombre_limpio
    
class ProductoSerializer(serializers.ModelSerializer):
    # Mostramos el nombre de la categoría en las respuestas de lectura
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'categoria', 'categoria_nombre', 'stock_bodega', 'stock_vitrina', 'stock_minimo', 'stock_total']

    def validate(self, data):
        nombre = data.get('nombre')
        categoria = data.get('categoria')

        # Ignoramos la validación si estamos editando un producto existente
        if not self.instance:
            # Criterio de Aceptación: Validar la unicidad (nombre + categoría)
            producto_existente = Producto.objects.filter(nombre__iexact=nombre, categoria=categoria).first()
            if producto_existente:
                # Levantamos un error personalizado que el Frontend pueda interpretar como una "sugerencia"
                raise serializers.ValidationError({
                    "code": "PRODUCTO_DUPLICADO",
                    "message": f"El producto '{nombre}' ya existe en esta categoría. ¿Deseas ir a actualizar su stock?",
                    "producto_id": producto_existente.id
                })
        return data