from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('Usuario desactivado.')
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError('Credenciales inválidas, intente nuevamente.')
        else:
            raise serializers.ValidationError('Debe proporcionar usuario y contraseña.')


class UsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    estado = serializers.SerializerMethodField()
    area_display = serializers.CharField(source='get_area_display', read_only=True) #Nuevo campo para mostrar el nombre legible del área para acceso roles y vistas.

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'rol', 'rol_display',
                   'area', 'area_display', 'is_active', 'estado', 'date_joined']

    def get_estado(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'