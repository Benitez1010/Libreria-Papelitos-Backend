from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .serializers import (
    LoginSerializer, UsuarioSerializer, RegistroUsuarioSerializer,
    SolicitudRecuperacionSerializer, ConfirmarRecuperacionSerializer
)
from .models import Usuario, BitacoraSeguridad
from django.shortcuts import get_object_or_404 
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone

class LoginView(APIView):
    """
    Vista encargada de procesar el inicio de sesión.
    Genera o recupera el token de seguridad y adjunta la matriz de accesos para React.
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Obtiene el token existente o crea uno nuevo si es el primer inicio de sesión
            token, created = Token.objects.get_or_create(user=user)

            # Adjunta los permisos personalizados del usuario para que React pueda controlar el acceso a vistas y funcionalidades según su rol.
            permisos = user.configuracion_accesos if user.configuracion_accesos else {}

            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'rol': user.get_rol_display(),
                'permisos': permisos # Enviamos los permisos a React
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UsuarioMeView(APIView):
    """
    Vista protegida que devuelve el perfil completo del usuario autenticado actual.
    Sirve para mantener la sesión persistente en el Frontend tras recargar el navegador.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        # Adjuntamos los permisos personalizados del usuario para que React pueda controlar el acceso a vistas y funcionalidades según su rol.
        datos = serializer.data
        datos['permisos'] = request.user.configuracion_accesos if request.user.configuracion_accesos else {}
        return Response(datos)

class UsuarioListView(APIView):
    """
    Vista para listar todos los usuarios registrados en el sistema de forma ordenada.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuarios = Usuario.objects.all().order_by('id')
        serializer = UsuarioSerializer(usuarios, many=True)
        return Response(serializer.data)

class DesactivarUsuarioView(APIView):
    """
    Vista encargada de dar de baja o suspender la cuenta de un usuario.
    Incluye candados de seguridad para proteger la integridad administrativa.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            usuario = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Candado 1: Evita que el usuario en sesión apague su propio acceso
        if request.user.id == usuario.id:
            return Response({'error': 'No puede desactivar su propia cuenta.'}, status=status.HTTP_403_FORBIDDEN)

        # Candado 2: Protege la jerarquía evitando que un administrador desactive a otro administrador
        if usuario.rol == Usuario.Roles.ADMINISTRADOR and request.user.id != usuario.id:
            return Response({'error': 'No puede desactivar a otro administrador.'}, status=status.HTTP_403_FORBIDDEN)

        usuario.is_active = False
        usuario.save()

        return Response({
            'mensaje': f'Usuario {usuario.username} desactivado exitosamente.',
            'usuario': UsuarioSerializer(usuario).data
        }, status=status.HTTP_200_OK)

class ReactivarUsuarioView(APIView):
    """
    Vista encargada de restablecer o dar de alta nuevamente a una cuenta suspendida.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            usuario = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        usuario.is_active = True
        usuario.save()

        return Response({
            'mensaje': f'Usuario {usuario.username} reactivado exitosamente.',
            'usuario': UsuarioSerializer(usuario).data
        }, status=status.HTTP_200_OK)

class RegistroUsuarioView(APIView):
    """
    Vista exclusiva para la creación de nuevas cuentas dentro del catálogo de usuarios.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Restricción por rol: Solo el rol ADMIN puede dar de alta nuevos accesos
        if request.user.rol != Usuario.Roles.ADMINISTRADOR:
            raise PermissionDenied('Solo los administradores pueden registrar nuevos usuarios.')

        # Validamos los datos de entrada utilizando el serializer dedicado a la creación de usuarios
        serializer = RegistroUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response({
                'mensaje': 'Usuario creado con éxito.',
                'usuario': UsuarioSerializer(usuario).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CambiarRolView(APIView):
    """
    Vista exclusiva para que el administrador actualice el rol operativo de un usuario.
    Al guardar, el modelo recalculará automáticamente la matriz de accesos en cascada.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Comprobación de privilegios administrativos antes de procesar el cambio
        if request.user.rol != Usuario.Roles.ADMINISTRADOR:
            return Response({'error': 'No tienes permisos para realizar esta acción.'}, status=status.STATUS_403_FORBIDDEN)
            
        usuario = get_object_or_404(Usuario, pk=pk)
        nuevo_rol = request.data.get('rol')

        # Valida que el rol enviado pertenezca a las opciones reales del modelo
        if not nuevo_rol or nuevo_rol not in Usuario.Roles.values:
            return Response({'error': 'Rol inválido o no proporcionado.'}, status=status.HTTP_400_BAD_REQUEST)

        usuario.rol = nuevo_rol
        usuario.save() # Dispara de forma automática la lógica de permisos del modelo
        return Response({'mensaje': 'Rol y permisos actualizados correctamente.'}, status=status.HTTP_200_OK)

class SolicitarRecuperacionView(APIView):
    """
    Vista pública que inicia el proceso de recuperación de contraseña.
    Genera un token temporal y envía el enlace al correo del usuario.
    Por seguridad devuelve siempre la misma respuesta, exista o no el correo.
    """
    def post(self, request):
        serializer = SolicitudRecuperacionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        mensaje_generico = 'Si el correo está registrado, recibirás un enlace de recuperación.'

        usuario = Usuario.objects.filter(email__iexact=email).first()

        # Solo se envía el enlace a cuentas existentes y activas, sin revelar el resultado
        if usuario and usuario.is_active:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            enlace = f"{settings.FRONTEND_URL}/restablecer/{uid}/{token}"

            nombre = usuario.first_name or usuario.username

            cuerpo = (
                f"Hola {nombre},\n\n"
                "Recibimos una solicitud para restablecer la contraseña de tu cuenta "
                "en Librería Papelitos.\n\n"
                f"Ingresa al siguiente enlace para crear una nueva contraseña:\n{enlace}\n\n"
                "El enlace es válido por 1 hora y solo puede utilizarse una vez.\n\n"
                "Si no solicitaste este cambio, puedes ignorar este mensaje.\n\n"
                "Librería Papelitos"
            )

            cuerpo_html = f"""
<div style="background-color:#A3C9B8;padding:32px 16px;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"
         style="max-width:560px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.12);">
    <tr>
      <td align="center" style="background-color:#ffffff;padding:28px 24px 12px 24px;">
        <img src="{settings.LOGO_URL}" alt="Librería Papelitos" width="180"
             style="display:block;width:180px;max-width:60%;height:auto;">
      </td>
    </tr>
    <tr>
      <td style="background-color:#1E5631;height:6px;line-height:6px;font-size:0;">&nbsp;</td>
    </tr>
    <tr>
      <td style="background-color:#EAF4EC;padding:32px 32px 24px 32px;">
        <h1 style="margin:0 0 20px 0;color:#1E5631;font-size:22px;letter-spacing:1px;">
          RECUPERACIÓN DE CONTRASEÑA
        </h1>
        <p style="margin:0 0 16px 0;color:#37474F;font-size:15px;line-height:1.6;">
          Hola <strong>{nombre}</strong>,
        </p>
        <p style="margin:0 0 24px 0;color:#37474F;font-size:15px;line-height:1.6;">
          Recibimos una solicitud para restablecer la contraseña de tu cuenta.
          Presiona el botón para crear una nueva.
        </p>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"
               style="margin:0 auto 24px auto;">
          <tr>
            <td align="center" style="background-color:#1E5631;border-radius:8px;">
              <a href="{enlace}"
                 style="display:inline-block;padding:15px 38px;color:#ffffff;font-size:16px;font-weight:bold;text-decoration:none;">
                Crear Nueva Contraseña
              </a>
            </td>
          </tr>
        </table>
        <p style="margin:0 0 8px 0;color:#546E7A;font-size:13px;line-height:1.6;text-align:center;">
          El enlace es válido por <strong>1 hora</strong> y solo puede utilizarse una vez.
        </p>
        <p style="margin:0 0 10px 0;color:#78909C;font-size:12px;line-height:1.6;text-align:center;">
          ¿El botón no funciona?
          <a href="{enlace}" style="color:#1E5631;font-weight:bold;text-decoration:underline;">
            Ingresa desde aquí
          </a>
        </p>
        <p style="margin:0;color:#B0BEC5;font-size:11px;line-height:1.5;text-align:center;">
          O copia esta dirección en tu navegador:<br>
          <span style="color:#90A4AE;word-break:break-all;">{enlace}</span>
        </p>
      </td>
    </tr>
    <tr>
      <td style="background-color:#EAF4EC;padding:0 32px 28px 32px;">
        <div style="border-top:1px solid #C5DFD0;padding-top:18px;">
          <p style="margin:0;color:#78909C;font-size:12px;line-height:1.6;text-align:center;">
            Si no solicitaste este cambio, puedes ignorar este mensaje.
            Tu contraseña actual seguirá siendo válida.
          </p>
        </div>
      </td>
    </tr>
    <tr>
      <td align="center" style="background-color:#1E5631;padding:16px 24px;">
        <p style="margin:0;color:#EAF4EC;font-size:12px;letter-spacing:1px;">
          LIBRERÍA PAPELITOS
        </p>
      </td>
    </tr>
  </table>
</div>
"""

            send_mail(
                subject='Recuperación de contraseña - Librería Papelitos',
                message=cuerpo,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[usuario.email],
                html_message=cuerpo_html,
                fail_silently=True
            )

        return Response({'mensaje': mensaje_generico}, status=status.HTTP_200_OK)

class ConfirmarRecuperacionView(APIView):
    """
    Vista pública que valida el enlace de recuperación y establece la nueva contraseña.
    El token queda invalidado automáticamente al modificarse la contraseña.
    """
    def post(self, request):
        serializer = ConfirmarRecuperacionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        error_enlace = {'error': 'El enlace de recuperación es inválido o ha expirado.'}

        # Decodifica el identificador del usuario contenido en el enlace
        try:
            usuario_id = force_str(urlsafe_base64_decode(uid))
            usuario = Usuario.objects.get(pk=usuario_id)
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
            return Response(error_enlace, status=status.HTTP_400_BAD_REQUEST)

        if not usuario.is_active:
            return Response(error_enlace, status=status.HTTP_400_BAD_REQUEST)

        # Verifica la vigencia del token según PASSWORD_RESET_TIMEOUT
        if not default_token_generator.check_token(usuario, token):
            return Response(error_enlace, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(password)
        # Se libera cualquier bloqueo previo por intentos fallidos
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save()
        
        return Response(
            {'mensaje': 'Contraseña actualizada correctamente. Ya puede iniciar sesión.'},
            status=status.HTTP_200_OK
        )
    

class BitacoraBloqueoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol != Usuario.Roles.ADMINISTRADOR:
            raise PermissionDenied('Acceso denegado: solo administradores pueden ver la bitácora.')

        # Solo eventos de bloqueo real (sin intentos intermedios)
        logs = BitacoraSeguridad.objects.filter(evento__icontains='Bloqueo').order_by('-fecha_hora')
        datos = [
            {
                'id': log.id,
                'usuario': log.usuario,
                'evento': log.evento,
                'fecha_hora': timezone.localtime(log.fecha_hora).strftime('%d/%m/%Y %H:%M:%S')
            }
            for log in logs
        ]
        return Response(datos, status=status.HTTP_200_OK)