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
    # CAMPOS PARA BLOQUEO TRAS INTENTOS FALLIDOS (FUTURA IMPLEMENTACIÓN) 
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
    
