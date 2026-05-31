from django.urls import path
from .views import (
    LoginView, UsuarioMeView, UsuarioListView, 
    DesactivarUsuarioView, ReactivarUsuarioView,
   UsuarioPermisosView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UsuarioMeView.as_view(), name='me'),
    path('usuarios/', UsuarioListView.as_view(), name='usuarios-list'),
    path('usuarios/<int:pk>/desactivar/', DesactivarUsuarioView.as_view(), name='usuarios-desactivar'),
    path('usuarios/<int:pk>/reactivar/', ReactivarUsuarioView.as_view(), name='usuarios-reactivar'),
   path('usuarios/<int:pk>/permisos/', UsuarioPermisosView.as_view(), name='usuarios-permisos'),
]
