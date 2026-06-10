"""
URL configuration for libreria_papelitos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# Lista de rutas globales del proyecto 'libreria_papelitos'
urlpatterns = [
    # Interfaz de administración nativa de Django para la gestión interna de datos por superusuarios
    path('admin/', admin.site.urls),
    # --- ENRUTAMIENTO CENTRALIZADO DE LA API REST ---
    # Enlazamos los archivos de urls internos de cada aplicación del sistema.
    # El uso del prefijo 'api/' unifica todos los endpoints bajo el mismo árbol jerárquico.
    path('api/', include('inventario.urls')), # Endpoints del módulo de Inventario (productos, categorías, transacciones de stock, etc.)
    path('api/', include('seguridad.urls')),  # Endpoints del módulo de Seguridad (autenticación, gestión de usuarios, etc.)
]
