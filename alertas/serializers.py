from rest_framework import serializers
from .models import DestinatarioCorreo

class DestinatarioCorreoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinatarioCorreo
        fields = ['id', 'correo', 'activo']