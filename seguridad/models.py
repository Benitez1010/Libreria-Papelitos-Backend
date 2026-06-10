from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    """
    Modelo de Usuario personalizado para el sistema.
    Hereda las funciones básicas de Django (como el manejo de contraseñas)
    y añade campos específicos para la Librería Papelitos.
    """

    # --- OPCIONES DE ROLES Y ÁREAS ---
    class Roles(models.TextChoices):
        ADMINISTRADOR = 'ADMIN', 'Administrador'
        OPERADOR_BODEGA = 'BODEGA', 'Operador de Bodega'
        OPERADOR_CAJA = 'CAJA', 'Operador de Caja'
    
    class Areas(models.TextChoices):
        GERENCIA = 'GER', 'Gerencia'
        BODEGA = 'BOD', 'Bodega'
        VITRINA = 'VIT', 'Vitrina'

    # --- CAMPOS ADICIONALES ---
    rol = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.OPERADOR_BODEGA,
        help_text="Rol asignado para el control de accesos y restricción de vistas."
    )

    #Espacio físico asignado para la procedencia de los productos.
    area = models.CharField(
        max_length=3,
        choices=Areas.choices,
        default=Areas.BODEGA)

    # --- SEGURIDAD CONTRA INTENTOS FALLIDOS ---
    # Cuenta cuántas veces consecutivas se ha equivocado el usuario al iniciar sesión.
    intentos_fallidos = models.PositiveIntegerField(
        default=0,
    )

    #Fecha y hora exacta en la que se levantará el bloqueo del usuario después de superar el límite de intentos fallidos.
    bloqueado_hasta = models.DateTimeField(
        null=True, 
        blank=True,
    )

    # --- PERMISOS PARA EL FRONTEND (REACT) ---
    configuracion_accesos = models.JSONField(
        default=dict, 
        blank=True, 
        null=True,
        help_text="Guarda los permisos de React (master, agregar, editar, etc)"
    )

    class Meta:
        db_table = 'usuarios' # Nombre asignado a la tabla en la base de datos

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribimos el método save para actualizar automáticamente los permisos 
        en la estructura JSON que lee React cada vez que se crea o modifica un usuario.
        """
        # 1. Definimos lógica de roles
        es_admin = self.rol == self.Roles.ADMINISTRADOR
        es_bodega = self.rol == self.Roles.OPERADOR_BODEGA
        # es_caja = self.rol == self.Roles.OPERADOR_CAJA # Ya implícito si no es admin ni bodega

        # 2. Roles con permiso de agregar productos
        puede_agregar_productos = es_admin or es_bodega

        # 3. Asignamos la matriz de permisos
        self.configuracion_accesos = {
            # Módulos de Inventario General
            "productos": {
                "master": True, 
                "agregar": puede_agregar_productos, 
                "editar": puede_agregar_productos, 
                "eliminar": es_admin
            },
            "categorias": {
                "master": True, 
                "agregar": es_admin, 
                "editar": es_admin, 
                "eliminar": es_admin
            },
            "almacenamiento": {
                "master": True, 
                "agregar": es_admin, 
                "editar": es_admin, 
                "eliminar": es_admin
            },
            # Módulo de Movimientos
            "movimientos": {
                "master": True, 
                "agregar": True, 
                "editar": es_admin, 
                "eliminar": es_admin
            },
            "control_inventario": {
                "master": True, 
                "agregar": es_admin, 
                "editar": es_admin, 
                "eliminar": es_admin
            },
            
            # Módulos de Seguridad: Solo el administrador tiene acceso total
            "usuarios": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin},
            "roles": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin},
            "acceso_rol": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin}
        }

        # 4. Guarda definitivamente los datos en la base de datos
        super().save(*args, **kwargs)
