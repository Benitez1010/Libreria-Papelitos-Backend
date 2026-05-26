from rest_framework import serializers
from .models import Categoria

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