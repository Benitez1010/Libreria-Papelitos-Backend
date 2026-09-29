from django.test import override_settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SolicitudRecuperacionTests(APITestCase):
    """
    Pruebas del endpoint que inicia la recuperación de contraseña.
    Verifica el envío del enlace y la confidencialidad de las cuentas registradas.
    """
    MENSAJE_GENERICO = 'Si el correo está registrado, recibirás un enlace de recuperación.'

    def setUp(self):
        self.url = reverse('recuperar-password')
        self.usuario = Usuario.objects.create_user(
            username='UsuarioPrueba',
            email='prueba@papelitos.com',
            password='Papelitos2026',
            first_name='Usuario Prueba',
            rol=Usuario.Roles.OPERADOR_CAJA
        )
        self.inactivo = Usuario.objects.create_user(
            username='UsuarioInactivo',
            email='inactivo@papelitos.com',
            password='Papelitos2026',
            first_name='Usuario Inactivo',
            rol=Usuario.Roles.OPERADOR_BODEGA
        )
        self.inactivo.is_active = False
        self.inactivo.save()

    def test_correo_registrado_envia_enlace(self):
        """DATO VÁLIDO: un correo existente y activo recibe el enlace de recuperación."""
        respuesta = self.client.post(self.url, {'email': 'prueba@papelitos.com'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['mensaje'], self.MENSAJE_GENERICO)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/restablecer/', mail.outbox[0].body)

    def test_correo_inexistente_no_revela_informacion(self):
        """DATO ERRÓNEO: un correo no registrado responde igual pero sin enviar nada."""
        respuesta = self.client.post(self.url, {'email': 'fantasma@papelitos.com'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['mensaje'], self.MENSAJE_GENERICO)
        self.assertEqual(len(mail.outbox), 0)

    def test_usuario_desactivado_no_recibe_enlace(self):
        """DATO LÍMITE: una cuenta suspendida no recibe enlace y tampoco se delata."""
        respuesta = self.client.post(self.url, {'email': 'inactivo@papelitos.com'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['mensaje'], self.MENSAJE_GENERICO)
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_con_formato_invalido_es_rechazado(self):
        """DATO ERRÓNEO: una cadena sin formato de correo no supera la validación."""
        respuesta = self.client.post(self.url, {'email': 'correo-sin-arroba'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', respuesta.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_en_mayusculas_encuentra_la_cuenta(self):
        """DATO LÍMITE: la búsqueda del correo ignora diferencias de mayúsculas."""
        respuesta = self.client.post(self.url, {'email': 'PRUEBA@PAPELITOS.COM'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ConfirmacionRecuperacionTests(APITestCase):
    """
    Pruebas del endpoint que valida el enlace y establece la nueva contraseña.
    Verifica la vigencia del token y las reglas de seguridad de la contraseña.
    """
    ERROR_ENLACE = 'El enlace de recuperación es inválido o ha expirado.'

    def setUp(self):
        self.url = reverse('restablecer-password')
        self.usuario = Usuario.objects.create_user(
            username='UsuarioPrueba',
            email='prueba@papelitos.com',
            password='Papelitos2026',
            first_name='Usuario Prueba',
            rol=Usuario.Roles.OPERADOR_CAJA
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        self.token = default_token_generator.make_token(self.usuario)

    def test_restablecimiento_exitoso_actualiza_contrasena(self):
        """DATO VÁLIDO: un enlace vigente permite establecer la nueva contraseña."""
        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': 'NuevaClave2026'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('NuevaClave2026'))

    def test_token_no_puede_reutilizarse(self):
        """DATO ERRÓNEO: el enlace queda invalidado después del primer uso."""
        self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': 'NuevaClave2026'
        }, format='json')

        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': 'OtraClave2026'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data['error'], self.ERROR_ENLACE)

    def test_token_falso_es_rechazado(self):
        """DATO ERRÓNEO: un token inventado no supera la verificación."""
        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': 'token-falso-123456',
            'password': 'NuevaClave2026'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Papelitos2026'))

    def test_identificador_invalido_es_rechazado(self):
        """DATO ERRÓNEO: un uid que no corresponde a ningún usuario se rechaza."""
        respuesta = self.client.post(self.url, {
            'uid': 'uid-invalido',
            'token': self.token,
            'password': 'NuevaClave2026'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data['error'], self.ERROR_ENLACE)

    def test_contrasena_de_ocho_caracteres_es_aceptada(self):
        """DATO LÍMITE: ocho caracteres es la longitud mínima permitida."""
        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': 'Clave26x'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_contrasena_de_siete_caracteres_es_rechazada(self):
        """DATO LÍMITE: siete caracteres queda por debajo del mínimo exigido."""
        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': 'Clav26x'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', respuesta.data)

    def test_contrasena_comun_es_rechazada(self):
        """DATO ERRÓNEO: las contraseñas de uso masivo no superan los validadores."""
        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'password': '12345678'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', respuesta.data)

    def test_restablecimiento_libera_bloqueo_por_intentos_fallidos(self):
        """DATO VÁLIDO: recuperar la contraseña levanta el bloqueo previo de la cuenta."""
        from django.utils import timezone
        from datetime import timedelta

        self.usuario.intentos_fallidos = 4
        self.usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
        self.usuario.save()
        token = default_token_generator.make_token(self.usuario)

        respuesta = self.client.post(self.url, {
            'uid': self.uid,
            'token': token,
            'password': 'NuevaClave2026'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueado_hasta)