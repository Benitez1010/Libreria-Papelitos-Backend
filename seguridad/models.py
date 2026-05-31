from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    class Roles(models.TextChoices):
        ADMINISTRADOR = 'ADMIN', 'Administrador'
        OPERADOR_BODEGA = 'BODEGA', 'Operador de Bodega'
        OPERADOR_CAJA = 'CAJA', 'Operador de Caja'
    
    rol = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.OPERADOR_BODEGA,
        help_text="Rol asignado para el control de accesos y restricción de vistas."
    )

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

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"