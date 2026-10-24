from django.db import models

class DestinatarioCorreo(models.Model):
    """
    Modelo que almacena la lista de correos electrónicos del personal
    que debe ser notificado cuando un producto se quede sin existencias básicas.
    """
    correo = models.EmailField(unique=True, help_text="Correo electrónico que recibirá las alertas de stock crítico.")
    activo = models.BooleanField(default=True, help_text="Permite activar o desactivar el envío global a este correo.")

    def __str__(self):
        return f"{self.correo} ({'Activo' if self.activo else 'Inactivo'})"

    class Meta:
        db_table = 'destinatarios_correo'


class HistorialAlerta(models.Model):
    """
    Modelo que registra cada evento en el que un producto cayó por debajo 
    de su stock mínimo permitido, sirviendo como bitácora de control de inventario.
    """
    # Si se elimina un producto del catálogo, se borran automáticamente sus alertas pasadas (on_delete=models.CASCADE)
    producto = models.ForeignKey('inventario.Producto', on_delete=models.CASCADE, related_name='alertas_disparadas')
    saldo_momento = models.PositiveIntegerField(help_text="Stock total que tenía el artículo al momento de activarse la alerta.")
    fecha_hora = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora exacta del disparo de la alerta.")
    notificacion_enviada = models.BooleanField(default=False, help_text="Indica si el correo electrónico se envió con éxito.")

    class Meta:
        ordering = ['-fecha_hora'] 
        get_latest_by = 'fecha_hora'
        db_table = 'historial_alertas'

    def __str__(self):
        estado_envio = "Enviado" if self.notificacion_enviada else "Fallo Técnico"
        return f"Alerta: {self.producto.nombre} - Saldo: {self.saldo_momento} ({estado_envio})"
    
class ConfiguracionAlerta(models.Model):
    notificaciones_globales_activas = models.BooleanField(
        default=True, 
        help_text="Interruptor maestro para encender/apagar todas las alertas por correo del sistema."
    )

    class Meta:
        db_table = 'configuracion_alertas'

    def save(self, *args, **kwargs):
        self.pk = 1  # Forzamos a que siempre sea la fila con ID 1 (Patrón Singleton)
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        # Devuelve la configuración actual o crea una por defecto si no existe
        config, created = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return f"Configuración Global (Activa: {self.notificaciones_globales_activas})"