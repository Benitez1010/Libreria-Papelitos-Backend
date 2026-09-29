from rest_framework import serializers
from .models import Categoria, Producto, MovimientoInventario

class CategoriaSerializer(serializers.ModelSerializer):
    """
    Controla los datos de las categorías al listar, crear o editar.
    Asegura que no se guarden nombres vacíos ni repetidos.
    """
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

    def validate_nombre(self, value):
        # Quitamos espacios sobrantes en las orillas y pasamos a mayúsculas
        # para que "Lápiz", " lápiz " y "LÁPIZ" se traten como lo mismo
        nombre_limpio = value.strip().upper()
        
        if not nombre_limpio:
            raise serializers.ValidationError("El nombre de la categoría no puede estar vacío.")

        # Si estamos editando, self.instance tiene la categoría actual.
        # Guardamos su ID para no comparar la categoría contra sí misma.
        instance_id = self.instance.id if self.instance else None

        # Buscamos si ya existe otra categoría con el mismo nombre
        if Categoria.objects.filter(nombre=nombre_limpio).exclude(id=instance_id).exists():
            raise serializers.ValidationError("Esta categoría ya se encuentra registrada.")
            
        return nombre_limpio
    
class ProductoSerializer(serializers.ModelSerializer):
    """
    Controla los datos de los productos, sus existencias por área
    y valida que no haya dos productos iguales en la misma categoría.
    """
    # Trae directo el nombre del texto de la categoría para que la app que consuma
    # la API no tenga que hacer otra petición solo para saber cómo se llama
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    class Meta:
        model = Producto
        # El campo 'categoria' recibe el ID al guardar, mientras que 'categoria_nombre' se usa para mostrar el texto al listar
        fields = ['id', 'nombre', 'categoria', 'categoria_nombre', 'stock_bodega', 'stock_vitrina', 'stock_minimo', 'stock_total']

    def validate_stock_minimo(self, value):
        # No tiene sentido permitir stock mínimo en cero o números negativos
        if value <= 0:
            raise serializers.ValidationError("Ingrese una cantidad numérica válida mayor a cero")
        return value

    def validate(self, data):
        """
        Revisa si el producto ya existe dentro de la categoría elegida.
        """
        # Si mandaron un nombre nuevo úsalo; si están editando y no lo mandaron, toma el nombre que ya tenía guardado en la base de datos
        nombre = data.get('nombre')
        if not nombre and self.instance:
            nombre = self.instance.nombre

        # Hacemos lo mismo con la categoría: toma la nueva o mantén la que ya tenía.
        # getattr maneja el caso de si DRF entrega el objeto completo o solo el número de ID
        categoria = data.get('categoria')
        categoria_id = getattr(categoria, 'id', categoria)
        if categoria_id is None and self.instance:
            categoria_id = self.instance.categoria_id

        # Solo validamos si logramos obtener tanto el nombre como la categoría
        if nombre and categoria_id:
            nombre_limpio = nombre.strip()
            data['nombre'] = nombre_limpio

            # Busca si ya existe ese nombre en esa categoría (sin importar mayúsculas o minúsculas)
            query = Producto.objects.filter(nombre__iexact=nombre_limpio, categoria_id=categoria_id)

            # Si estamos editando el producto, ignóralo a él mismo para no dar falso error
            if self.instance:
                query = query.exclude(id=self.instance.id)

            if query.exists():
                raise serializers.ValidationError({
                    "nombre": f"El producto '{nombre_limpio}' ya existe en esta categoría."
                })

        return data

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    """
    Controla las transacciones de inventario y la trazabilidad (SEG-07).
    Expone el responsable y valida la justificación en ajustes.
    """
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    destino_display = serializers.CharField(source='get_destino_display', read_only=True)
    
    # Campo obligatorio para los reportes de historial (SEG-07)
    responsable = serializers.ReadOnlyField(source='usuario.username')

    class Meta:
        model = MovimientoInventario
        fields = [
            'id',
            'producto',
            'producto_nombre',
            'tipo',
            'tipo_display',
            'cantidad',
            'origen',
            'origen_display',
            'destino',
            'destino_display',
            'justificacion',
            'responsable',
            'fecha_hora'
        ]
        # El usuario y la fecha se asignan automáticamente en el backend
        read_only_fields = ['usuario', 'fecha_hora']

    def validate(self, data):
        tipo = data.get('tipo')
        justificacion = data.get('justificacion')

        # Criterio SEG-07: Obligatoriedad de justificación en ajustes/mermas
        if tipo in [MovimientoInventario.TipoMovimiento.DAÑO, MovimientoInventario.TipoMovimiento.CORRECCION]:
            if not justificacion or not justificacion.strip():
                raise serializers.ValidationError({
                    'justificacion': 'Es obligatorio ingresar un comentario detallado justificando la operación.'
                })
        return data