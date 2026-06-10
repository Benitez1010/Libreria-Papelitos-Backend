from django.urls import path
from .views import (
    LoginView, UsuarioMeView, UsuarioListView, 
    DesactivarUsuarioView, ReactivarUsuarioView, RegistroUsuarioView,CambiarRolView
  
)

# Definición de rutas internas para el módulo de Autenticación y Usuarios
urlpatterns = [
    # Ruta para el inicio de sesión de usuarios (Retorna el Token y permisos)
    path('login/', LoginView.as_view(), name='login'),
    # Ruta para obtener los datos del usuario que tiene la sesión activa actualmente
    path('me/', UsuarioMeView.as_view(), name='me'),
    # Ruta para listar todos los usuarios del sistema en las tablas de gestión
    path('usuarios/', UsuarioListView.as_view(), name='usuarios-list'),
    # Rutas para dar de baja o de alta las cuentas mediante el ID (pk) del usuario
    path('usuarios/<int:pk>/desactivar/', DesactivarUsuarioView.as_view(), name='usuarios-desactivar'),
    path('usuarios/<int:pk>/reactivar/', ReactivarUsuarioView.as_view(), name='usuarios-reactivar'),
    # Ruta exclusiva para que el administrador registre nuevas cuentas en el sistema
    path('usuarios/registrar/', RegistroUsuarioView.as_view(), name='usuarios-registrar'),
    # Ruta para modificar el rol operativo de un usuario y actualizar sus accesos
    path('usuarios/<int:pk>/cambiar-rol/', CambiarRolView.as_view(), name='usuarios-cambiar-rol'), 
]