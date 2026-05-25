from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    class Roles(models.TextChoices):
        ADMINISTRADOR = 'ADMIN', 'Administrador'
        OPERADOR = 'OPERADOR', 'Operador'
    
    rol = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.OPERADOR,
        help_text="Rol asignado para el control de accesos y restricción de vistas."
    )

    # =========================================================================
    # CAMPOS PARA BLOQUEO TRAS INTENTOS FALLIDOS (FUTURA IMPLEMENTACIÓN) 
    # Se han declarado en la BD, pero NO se programará su lógica en este Sprint.
    # =========================================================================

    # NOTA: Lógica de control para sprint de seguridad avanzada
    intentos_fallidos = models.PositiveIntegerField(
        default=0,
    )

    # NOTA: Almacena penalización por ataques de fuerza bruta
    bloqueado_hasta = models.DateTimeField(
        null=True, 
        blank=True,
    )

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"