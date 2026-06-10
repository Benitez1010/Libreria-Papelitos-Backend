from django.conf import settings
from django.core.management.base import BaseCommand
from seguridad.models import Usuario


# =============================================================================
# usuarios del equipo (SOLO desarrollo).
# =============================================================================
USUARIOS_ADMIN = [
    {'username': 'Rodrigo',   'nombre': 'Rodrigo Benítez',  'email': 'bh22010@ues.edu.sv', 'password': 'rodrigo12345'},
    {'username': 'Moises',    'nombre': 'Moises Cruz',      'email': 'cp17059@ues.edu.sv', 'password': 'moises12345'},
    {'username': 'Bryan',     'nombre': 'Bryan Díaz',       'email': 'dv21005@ues.edu.sv', 'password': 'bryan12345'},
    {'username': 'Crhistian', 'nombre': 'Crhistian Gómez',  'email': 'gd23017@ues.edu.sv', 'password': 'crhistian12345'},
    {'username': 'Jonathan',  'nombre': 'Jonathan Gómez',   'email': 'gd23016@ues.edu.sv', 'password': 'jonathan12345'},
]

# Operadores de prueba internos (referencia para el equipo).
# 'rol': 'BODEGA' (operador de bodega) o 'CAJA' (operador de caja)
# 'area': 'BOD' (Bodega) o 'VIT' (Vitrina)
USUARIOS_OPERADORES = [
    {'username': 'Operador1Test', 'nombre': 'Operador1Test', 'email': 'operador1@papelitos.com', 'password': 'operador112345', 'rol': 'BODEGA', 'area': 'BOD'},
    {'username': 'Operador2Test', 'nombre': 'Operador2Test', 'email': 'operador2@papelitos.com', 'password': 'operador212345', 'rol': 'CAJA',   'area': 'VIT'},
]


class Command(BaseCommand):
    help = 'Crea los usuarios de prueba del equipo (SOLO para desarrollo).'

    def handle(self, *args, **options):
        # nunca ejecutar en produccion.
        if not settings.DEBUG:
            self.stdout.write(self.style.ERROR(
                'Seed bloqueado: solo se puede ejecutar con DEBUG=True (entorno de desarrollo).'
            ))
            return

        creados = 0
        existentes = 0

        # ---- Administradores ----
        for data in USUARIOS_ADMIN:
            usuario, creado = Usuario.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['nombre'],
                    'rol': 'ADMIN',
                    'area': 'GER',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if creado:
                usuario.set_password(data['password'])
                usuario.save()
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'Creado: {data["username"]} (ADMIN)'))
            else:
                existentes += 1
                self.stdout.write(f'Ya existia: {data["username"]} (no se modifico)')

        # ---- Operadores de prueba ----
        for data in USUARIOS_OPERADORES:
            usuario, creado = Usuario.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['nombre'],
                    'rol': data['rol'],
                    'area': data['area'],
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if creado:
                usuario.set_password(data['password'])
                usuario.save()
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'Creado: {data["username"]} ({data["rol"]})'))
            else:
                existentes += 1
                self.stdout.write(f'Ya existia: {data["username"]} (no se modifico)')

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. {creados} usuario(s) creado(s), {existentes} ya existian.'
        ))