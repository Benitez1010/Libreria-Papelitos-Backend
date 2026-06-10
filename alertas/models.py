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
        ordering = ['-fecha_hora'] # Muestra siempre las alertas más recientes primero
        get_latest_by = 'fecha_hora'
        db_table = 'historial_alertas'

    def __str__(self):
        estado_envio = "Enviado" if self.notificacion_enviada else "Fallo Técnico"
        return f"Alerta: {self.producto.nombre} - Saldo: {self.saldo_momento} ({estado_envio})"