from django.contrib.auth.models import AbstractUser
from django.db import models



class Usuario(AbstractUser):
    class Roles(models.TextChoices):
        ADMINISTRADOR = 'ADMIN', 'Administrador'
        OPERADOR_BODEGA = 'BODEGA', 'Operador de Bodega'
        OPERADOR_CAJA = 'CAJA', 'Operador de Caja'
    
    class Areas(models.TextChoices):
        GERENCIA = 'GER', 'Gerencia'
        BODEGA = 'BOD', 'Bodega'
        VITRINA = 'VIT', 'Vitrina'

    
    rol = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.OPERADOR_BODEGA,
        help_text="Rol asignado para el control de accesos y restricción de vistas."
    )
    area = models.CharField(
        max_length=3,
        choices=Areas.choices,
        default=Areas.BODEGA)

    # =========================================================================
    # CAMPOS PARA BLOQUEO TRAS INTENTOS FALLIDOS 
    # =========================================================================
    intentos_fallidos = models.PositiveIntegerField(
        default=0,
    )

    bloqueado_hasta = models.DateTimeField(
        null=True, 
        blank=True,
    )

    configuracion_accesos = models.JSONField(
        default=dict, 
        blank=True, 
        null=True,
        help_text="Guarda los permisos de React (master, agregar, editar, etc)"
    )

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"
    
    # Sobrescribimos el método save para actualizar automáticamente los permisos según el rol asignado
    def save(self, *args, **kwargs):
        # 1. Definimos si es un rol operativo (Bodega o Caja)
        es_operativo = self.rol in [self.Roles.OPERADOR_BODEGA, self.Roles.OPERADOR_CAJA]
        es_admin = self.rol == self.Roles.ADMINISTRADOR

        # 2. Reconstruimos los permisos automáticamente al guardar
        # IMPORTANTE: Cambiado 'articulos' a 'productos' para sincronizarlo con tu Frontend
        self.configuracion_accesos = {
            "productos": {"master": True, "agregar": not es_operativo, "editar": not es_operativo, "eliminar": not es_operativo},
            "categorias": {"master": True, "agregar": not es_operativo, "editar": not es_operativo, "eliminar": not es_operativo},
            "almacenamiento": {"master": True, "agregar": not es_operativo, "editar": not es_operativo, "eliminar": not es_operativo},
            "movimientos": {"master": True, "agregar": True, "editar": not es_operativo, "eliminar": not es_operativo},
            "control_inventario": {"master": True, "agregar": not es_operativo, "editar": not es_operativo, "eliminar": not es_operativo},
            
            # Configuración administrativa protegida
            "usuarios": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin},
            "roles": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin},
            "acceso_rol": {"master": es_admin, "agregar": es_admin, "editar": es_admin, "eliminar": es_admin}
        }
        
        super().save(*args, **kwargs)
    
