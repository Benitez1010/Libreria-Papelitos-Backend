from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .serializers import LoginSerializer, UsuarioSerializer, RegistroUsuarioSerializer
from .models import Usuario
from django.shortcuts import get_object_or_404 

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