from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Categoria(models.Model):
    """
    Clase para clasificar los artículos del catálogo (Ej: Útiles, Oficina, Libros).
    Garantiza que los nombres guarden consistencia visual y protege la integridad referencial.
    """
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'categorias'

    def clean(self):
        # INV-01: Transforma el nombre a mayúsculas automáticamente
        if self.nombre:
            self.nombre = self.nombre.upper()

    def save(self, *args, **kwargs):
        self.full_clean()  # Fuerza la ejecución de clean() antes de guardar en la base de datos
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # INV-03: Bloquear la eliminación si tiene productos vinculados
        if self.productos.exists():
            raise ValidationError("No se puede eliminar: existen productos bajo esta categoría.")
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """
    Representa los artículos disponibles en la librería.
    Lleva el control de existencias por separado (Bodega / Vitrina) y define límites de alertas.
    """
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    stock_bodega = models.PositiveIntegerField(default=0)
    stock_vitrina = models.PositiveIntegerField(default=0)
    
    # ALT-03 & ALT-06: Configuración obligatoria de stock mínimo
    stock_minimo = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad mínima permitida antes de disparar alertas (Mayor a cero)."
    )

    class Meta:
        unique_together = ('nombre', 'categoria') # Evita que se registre el mismo producto en la misma categoría
        db_table = 'productos'

    @property
    def stock_total(self):
        return self.stock_bodega + self.stock_vitrina

    def clean(self):
        # ALT-06: Impedir el valor cero en el stock mínimo
        if self.stock_minimo is not None and self.stock_minimo <= 0:
            raise ValidationError({"stock_minimo": "Ingrese una cantidad numérica válida mayor a cero."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # INV-12: Bloquear la eliminación si el producto tiene stock activo
        if self.stock_bodega > 0 or self.stock_vitrina > 0:
            raise ValidationError("No se puede eliminar el producto: posee existencias en Bodega o Vitrina.")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"


class MovimientoInventario(models.Model):
    """
    Historial transaccional del inventario.
    Registra cada entrada, salida, traslado o ajuste, descontando o sumando stock en tiempo real.
    """
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada de Mercadería'
        SALIDA = 'SALIDA', 'Salida (Despacho)'
        TRASLADO = 'TRASLADO', 'Traslado (Bodega a Vitrina)'
        DAÑO = 'AVERIA', 'Ajuste por Merma/Daño'              # Requerido por INV-05
        CORRECCION = 'CORRECCION', 'Ajuste Administrativo'    # Requerido por INV-13

    class Ubicacion(models.TextChoices):
        BODEGA = 'BODEGA', 'Bodega'
        VITRINA = 'VITRINA', 'Vitrina'
        EXTERNO = 'EXTERNO', 'Proveedor/Cliente Externo'

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=15, choices=TipoMovimiento.choices)
    cantidad = models.PositiveIntegerField()
    
    origen = models.CharField(max_length=10, choices=Ubicacion.choices)
    destino = models.CharField(max_length=10, choices=Ubicacion.choices)
    
    # INV-05 & INV-13: Campo obligatorio para almacenar justificaciones de ajustes
    justificacion = models.TextField(
        blank=True, 
        null=True,
        help_text="Obligatorio para justificar mermas o correcciones administrativas."
    )
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos_inventario'

    def clean(self):
        # INV-06: Validar valores válidos de entrada
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError("La cantidad del movimiento debe ser mayor a cero.")

        # INV-05 y INV-13: Forzar obligatoriedad de comentario en ajustes
        if self.tipo in [self.TipoMovimiento.DAÑO, self.TipoMovimiento.CORRECCION] and not self.justificacion:
            raise ValidationError({"justificacion": "Es obligatorio ingresar un comentario detallado justificando la operación."})

        # INV-06: Validación contra inventario negativo basándose en el origen real
        if self.tipo in [self.TipoMovimiento.SALIDA, self.TipoMovimiento.TRASLADO, self.TipoMovimiento.DAÑO]:
            if self.origen == self.Ubicacion.BODEGA and self.producto.stock_bodega < self.cantidad:
                raise ValidationError("Existencias insuficientes para realizar la operación.")
            elif self.origen == self.Ubicacion.VITRINA and self.producto.stock_vitrina < self.cantidad:
                raise ValidationError("Existencias insuficientes para realizar la operación.")

    def save(self, *args, **kwargs):
        self.full_clean()

        # --- LÓGICA TRANSACCIONAL: ACTUALIZACIÓN AUTOMÁTICA DE STOCKS ---
        
        # 1. ENTRADAS: Incrementan el saldo de la ubicación de destino seleccionada
        if self.tipo == self.TipoMovimiento.ENTRADA:
            if self.destino == self.Ubicacion.BODEGA:
                self.producto.stock_bodega += self.cantidad
            elif self.destino == self.Ubicacion.VITRINA:
                self.producto.stock_vitrina += self.cantidad

        # 2. SALIDAS O MERMAS: Disminuyen el saldo de la ubicación de origen seleccionada   
        elif self.tipo in [self.TipoMovimiento.SALIDA, self.TipoMovimiento.DAÑO]:
            if self.origen == self.Ubicacion.BODEGA:
                self.producto.stock_bodega -= self.cantidad
            elif self.origen == self.Ubicacion.VITRINA:
                self.producto.stock_vitrina -= self.cantidad

        # 3. TRASLADOS INTERNOS: Restan de una ubicación y suman en la otra simultáneamente  
        elif self.tipo == self.TipoMovimiento.TRASLADO:
            if self.origen == self.Ubicacion.BODEGA and self.destino == self.Ubicacion.VITRINA:
                self.producto.stock_bodega -= self.cantidad
                self.producto.stock_vitrina += self.cantidad
            elif self.origen == self.Ubicacion.VITRINA and self.destino == self.Ubicacion.BODEGA:
                self.producto.stock_vitrina -= self.cantidad
                self.producto.stock_bodega += self.cantidad
            else:
                raise ValidationError("Para un traslado, el origen y destino deben ser BODEGA y VITRINA de forma cruzada.")

        # 4. CORRECCIONES: Permiten ajustar inventarios sumando o restando según se indique en origen/destino
        elif self.tipo == self.TipoMovimiento.CORRECCION:
            # INV-13: El ajuste administrativo permite tanto sumar como restar a conveniencia
            # Se asume que el origen/destino indica si incrementa o decrementa la bodega/vitrina
            if self.destino == self.Ubicacion.BODEGA:
                self.producto.stock_bodega += self.cantidad
            elif self.origen == self.Ubicacion.BODEGA:
                self.producto.stock_bodega -= self.cantidad
            elif self.destino == self.Ubicacion.VITRINA:
                self.producto.stock_vitrina += self.cantidad
            elif self.origen == self.Ubicacion.VITRINA:
                self.producto.stock_vitrina -= self.cantidad

        # Guarda los nuevos saldos calculados en el producto y luego registra el movimiento histórico
        self.producto.save()
        super().save(*args, **kwargs)