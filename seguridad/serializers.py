from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username_input = attrs.get('username')
        password = attrs.get('password')

        if not username_input or not password:
            raise serializers.ValidationError('Debe proporcionar usuario y contraseña.')

        # Detectar si es email o username
        if '@' in username_input:
            try:
                usuario = Usuario.objects.get(email=username_input)
                username = usuario.username
            except Usuario.DoesNotExist:
                raise serializers.ValidationError('Credenciales inválidas, intente nuevamente.')
        else:
            username = username_input

        # Buscar el usuario en la base de datos
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError('Credenciales inválidas, intente nuevamente.')

        # ========== VERIFICAR PRIMERO SI ESTÁ DESACTIVADO ==========
        if not usuario.is_active:
            raise serializers.ValidationError('Su cuenta ha sido desactivada. Contacte al administrador para reactivarla.')

        # Verificar si está bloqueado temporalmente
        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > timezone.now():
            segundos_restantes = int((usuario.bloqueado_hasta - timezone.now()).total_seconds())
            raise serializers.ValidationError(
                f'Cuenta bloqueada por seguridad. Intente nuevamente en {segundos_restantes} segundos.'
            )

        # Autenticar
        user = authenticate(username=username, password=password)

        if user:
            # Login exitoso: resetear contador de intentos
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.save()

            attrs['user'] = user
            return attrs
        else:
            # Login fallido: incrementar contador
            usuario.intentos_fallidos += 1

            # Si llega a 5 intentos, bloquear por 30 segundos
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = timezone.now() + timedelta(seconds=30)
                usuario.intentos_fallidos = 0  # Resetear para el próximo ciclo
                usuario.save()
                raise serializers.ValidationError(
                    'Demasiados intentos fallidos. Cuenta bloqueada por 30 segundos.'
                )

            usuario.save()
            intentos_restantes = 5 - usuario.intentos_fallidos
            raise serializers.ValidationError(
                f'Credenciales inválidas. Le quedan {intentos_restantes} intentos antes del bloqueo.')


class UsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    estado = serializers.SerializerMethodField()
    area_display = serializers.CharField(source='get_area_display', read_only=True) #campo para mostrar el nombre legible del área para acceso roles y vistas.
    nombre_completo = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username','nombre_completo', 'email', 'rol', 'rol_display',
                   'area', 'area_display', 'is_active', 'estado', 'date_joined']

    def get_estado(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True, max_length=150, validators=[])
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        }
    )
    nombre_completo = serializers.CharField(source='first_name', required=True)

    class Meta:
        model = Usuario
        fields = ['username', 'password', 'nombre_completo', 'email', 'rol']

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este nombre de usuario ya existe.')
        return value

    def validate_nombre_completo(self, value):
        if Usuario.objects.filter(first_name=value).exists():
            raise serializers.ValidationError('Este nombre completo ya está registrado.')
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este correo electrónico ya está registrado.')
        return value

    def create(self, validated_data):
        first_name = validated_data.pop('first_name', '')
        password = validated_data.pop('password')
        
        # El modelo genera automáticamente la configuracion_accesos gracias al método save()
        user = Usuario.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            rol=validated_data['rol'],
            first_name=first_name,
            password=password
        )
        return user