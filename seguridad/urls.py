from django.urls import path
from .views import LoginView, UsuarioMeView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UsuarioMeView.as_view(), name='me'),
]