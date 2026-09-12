from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Usuario, BitacoraSeguridad
import math


class LoginSerializer(serializers.Serializer):
    """
    Valida las credenciales de acceso, controla los intentos fallidos
    y bloquea la cuenta temporalmente si se sobrepasan los límites.
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username_input = attrs.get('username')
        password = attrs.get('password')

        # Validación de campos obligatorios
        if not username_input or not password:
            raise serializers.ValidationError('Debe proporcionar usuario y contraseña.')

        # Si el usuario escribió un correo con '@', buscamos el username que le corresponde.
        # Siempre devolvemos "Credenciales inválidas" para no revelar si el correo existe en el sistema.
        if '@' in username_input:
            try:
                usuario = Usuario.objects.get(email=username_input)
                username = usuario.username
            except Usuario.DoesNotExist:
                raise serializers.ValidationError('Credenciales inválidas, intente nuevamente.')
        else:
            username = username_input

        # Verificamos si existe el usuario antes de intentar autenticarlo           
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError('Credenciales inválidas, intente nuevamente.')

        # Si el administrador dio de baja al usuario, frenamos el login de inmediato
        if not usuario.is_active:
            raise serializers.ValidationError('Su cuenta ha sido desactivada. Contacte al administrador para reactivarla.')

        # Revisamos si la cuenta aún tiene un castigo de tiempo activo
        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > timezone.now():
            segundos_restantes = (usuario.bloqueado_hasta - timezone.now()).total_seconds()
            minutos_restantes = max(1, math.ceil(segundos_restantes / 60))
            unidad = "minuto" if minutos_restantes == 1 else "minutos"
            raise serializers.ValidationError(
                f'Cuenta bloqueada temporalmente por seguridad. Intente nuevamente en {minutos_restantes} {unidad}'
            )

        # Verificamos la contraseña con el método nativo de Django
        user = authenticate(username=username, password=password)

        if user:
            # Login exitoso: se reinician contadores y penalizaciones
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.save()

            attrs['user'] = user
            return attrs
        else:
            # Login fallido: incrementa contador
            usuario.intentos_fallidos += 1

            # Bloqueo temporal tras 5 intentos fallidos
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
                usuario.intentos_fallidos = 0
                usuario.save()

                # ÚNICO REGISTRO EN BITÁCORA (SOLO BLOQUEO)
                BitacoraSeguridad.objects.create(
                    usuario=usuario.username,
                    evento='Bloqueo temporal de cuenta tras 5 intentos fallidos'
                )

                raise serializers.ValidationError(
                    'Cuenta bloqueada temporalmente por seguridad. Intente nuevamente en 15 minutos'
                )

            usuario.save()

            BitacoraSeguridad.objects.create(
                usuario=usuario.username,
                evento=f'Intento fallido de contraseña ({usuario.intentos_fallidos}/5)')
            
            intentos_restantes = 5 - usuario.intentos_fallidos
            raise serializers.ValidationError(
                f'Credenciales inválidas. Le quedan {intentos_restantes} intentos antes del bloqueo.'
            )

class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para consultar y listar la información de los usuarios.
    Muestra los datos en formatos legibles listos para las tablas del Frontend.
    """
    # Muestra el nombre completo del rol y del área en lugar de sus códigos de base de datos
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    estado = serializers.SerializerMethodField()
    area_display = serializers.CharField(source='get_area_display', read_only=True) #campo para mostrar el nombre legible del área para acceso roles y vistas.
    nombre_completo = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username','nombre_completo', 'email', 'rol', 'rol_display',
                   'area', 'area_display', 'is_active', 'estado', 'date_joined']

    def get_estado(self, obj):
        # Para mostrar "Activo" o "Inactivo" en lugar de un simple true/false
        return 'Activo' if obj.is_active else 'Inactivo'


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer dedicado a la creación y alta de nuevos usuarios dentro del sistema.
    Valida de forma estricta la unicidad de los datos personales.
    """
    username = serializers.CharField(required=True, max_length=150, validators=[])
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        }
    )
    # Mapea el campo personalizado 'nombre_completo' directamente hacia el 'first_name' nativo del modelo Usuario para mantener la compatibilidad con el sistema de autenticación de Django.
    nombre_completo = serializers.CharField(source='first_name', required=True)

    class Meta:
        model = Usuario
        fields = ['username', 'password', 'nombre_completo', 'email', 'rol']

    # --- Validamos duplicados campo por campo antes de guardar ---
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
        """
        Ejecuta la creación física del registro utilizando el manejador 'create_user' 
        de Django para aplicar correctamente el hash de seguridad a la contraseña.
        """
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

#Para recuperear contraseña
class SolicitudRecuperacionSerializer(serializers.Serializer):
    """
    Serializer encargado de recibir el correo para iniciar el proceso de recuperación.
    Solo valida el formato; la existencia del usuario se resuelve en la vista para no
    revelar si el correo está registrado en el sistema.
    """
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Debe proporcionar un correo electrónico.',
            'invalid': 'Ingrese un correo electrónico válido.',
            'blank': 'Debe proporcionar un correo electrónico.'
        }
    )


class ConfirmarRecuperacionSerializer(serializers.Serializer):
    """
    Serializer encargado de validar el enlace de recuperación y la nueva contraseña.
    Aplica las reglas de seguridad definidas en AUTH_PASSWORD_VALIDATORS.
    """
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 8 caracteres.',
            'required': 'Debe proporcionar una nueva contraseña.',
            'blank': 'Debe proporcionar una nueva contraseña.'
        }
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value 