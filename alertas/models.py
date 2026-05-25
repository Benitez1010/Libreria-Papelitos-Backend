from django.db import models

class DestinatarioCorreo(models.Model):
    correo = models.EmailField(unique=True, help_text="Correo electrónico que recibirá las alertas de stock crítico.")
    activo = models.BooleanField(default=True, help_text="Permite activar o desactivar el envío global a este correo.")

    def __str__(self):
        return f"{self.correo} ({'Activo' if self.activo else 'Inactivo'})"

    class Meta:
        db_table = 'destinatarios_correo'


class HistorialAlerta(models.Model):
    # models.CASCADE porque si se elimina el producto, sus alertas históricas pierden sentido
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