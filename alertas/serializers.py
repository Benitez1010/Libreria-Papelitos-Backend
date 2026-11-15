from rest_framework import serializers
from .models import DestinatarioCorreo, HistorialAlerta, ConfiguracionAlerta

class DestinatarioCorreoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinatarioCorreo
        fields = ['id', 'correo', 'activo']

class HistorialAlertaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    fecha_hora = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")

    class Meta:
        model = HistorialAlerta
        fields = ['id', 'producto_nombre', 'saldo_momento', 'fecha_hora', 'notificacion_enviada']

class ConfiguracionAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionAlerta
        fields = ['notificaciones_globales_activas']