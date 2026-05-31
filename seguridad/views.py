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
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)

            # --- RECUPERAMOS TUS PERMISOS ---
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        # --- ADJUNTAMOS TUS PERMISOS AL PERFIL ---
        datos = serializer.data
        datos['permisos'] = request.user.configuracion_accesos if request.user.configuracion_accesos else {}
        return Response(datos)

class UsuarioListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuarios = Usuario.objects.all().order_by('id')
        serializer = UsuarioSerializer(usuarios, many=True)
        return Response(serializer.data)

class DesactivarUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            usuario = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.id == usuario.id:
            return Response({'error': 'No puede desactivar su propia cuenta.'}, status=status.HTTP_403_FORBIDDEN)

        if usuario.rol == Usuario.Roles.ADMINISTRADOR and request.user.id != usuario.id:
            return Response({'error': 'No puede desactivar a otro administrador.'}, status=status.HTTP_403_FORBIDDEN)

        usuario.is_active = False
        usuario.save()

        return Response({
            'mensaje': f'Usuario {usuario.username} desactivado exitosamente.',
            'usuario': UsuarioSerializer(usuario).data
        }, status=status.HTTP_200_OK)

class ReactivarUsuarioView(APIView):
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.rol != Usuario.Roles.ADMINISTRADOR:
            raise PermissionDenied('Solo los administradores pueden registrar nuevos usuarios.')

        serializer = RegistroUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response({
                'mensaje': 'Usuario creado con éxito.',
                'usuario': UsuarioSerializer(usuario).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UsuarioPermisosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        usuario = Usuario.objects.get(pk=pk)
        config = usuario.configuracion_accesos if usuario.configuracion_accesos else {}
        return Response({"configuracion": config}, status=status.HTTP_200_OK)

    def post(self, request, pk):
        usuario = Usuario.objects.get(pk=pk)
        nueva_configuracion = request.data.get('configuracion', {})
        usuario.configuracion_accesos = nueva_configuracion
        usuario.save()
        return Response({"mensaje": "Permisos guardados."}, status=status.HTTP_200_OK)