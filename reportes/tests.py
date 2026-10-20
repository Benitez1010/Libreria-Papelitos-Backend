from django.test import TestCase

# Create your tests here.

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventario.models import Categoria, Producto
from seguridad.models import Usuario


class ReporteStockCriticoTests(APITestCase):
    """
    Pruebas del reporte de productos en stock crítico (REP-06).
    Verifica el criterio de inclusión, el orden de prioridad, el filtro
    por categoría y el acceso exclusivo para administradores.
    """

    def setUp(self):
        self.url = reverse('reporte-stock-critico')
        self.administrador = Usuario.objects.create_user(
            username='AdminPrueba',
            email='admin@papelitos.com',
            password='Papelitos2026',
            first_name='Admin Prueba',
            rol=Usuario.Roles.ADMINISTRADOR
        )
        self.operador = Usuario.objects.create_user(
            username='OperadorPrueba',
            email='operador@papelitos.com',
            password='Papelitos2026',
            first_name='Operador Prueba',
            rol=Usuario.Roles.OPERADOR_BODEGA
        )

        self.cuadernos = Categoria.objects.create(nombre='Cuadernos')
        self.escritura = Categoria.objects.create(nombre='Escritura')

        self.critico = Producto.objects.create(
            nombre='Cuaderno rayado', categoria=self.cuadernos,
            stock_bodega=3, stock_vitrina=2, stock_minimo=10
        )
        self.igual_al_minimo = Producto.objects.create(
            nombre='Cuaderno cuadriculado', categoria=self.cuadernos,
            stock_bodega=6, stock_vitrina=4, stock_minimo=10
        )
        self.sobre_el_minimo = Producto.objects.create(
            nombre='Cuaderno de dibujo', categoria=self.cuadernos,
            stock_bodega=7, stock_vitrina=4, stock_minimo=10
        )
        self.agotado = Producto.objects.create(
            nombre='Lapicero azul', categoria=self.escritura,
            stock_bodega=0, stock_vitrina=0, stock_minimo=2
        )
        self.suficiente = Producto.objects.create(
            nombre='Lápiz HB', categoria=self.escritura,
            stock_bodega=50, stock_vitrina=20, stock_minimo=10
        )

    def ids_respuesta(self, respuesta):
        return [producto['id'] for producto in respuesta.data]

    def test_administrador_obtiene_solo_productos_criticos(self):
        """DATO VÁLIDO: el reporte incluye únicamente productos con stock total menor o igual al mínimo."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            self.ids_respuesta(respuesta),
            [self.critico.id, self.igual_al_minimo.id, self.agotado.id]
        )
        fila = next(p for p in respuesta.data if p['id'] == self.critico.id)
        self.assertEqual(fila['total_consolidado'], 5)
        self.assertEqual(fila['cantidad_sugerida'], 5)

    def test_stock_igual_al_minimo_se_incluye(self):
        """DATO LÍMITE: un producto con stock total exactamente igual al mínimo sí es crítico."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url)

        self.assertIn(self.igual_al_minimo.id, self.ids_respuesta(respuesta))
        fila = next(p for p in respuesta.data if p['id'] == self.igual_al_minimo.id)
        self.assertEqual(fila['cantidad_sugerida'], 0)

    def test_stock_una_unidad_sobre_el_minimo_se_excluye(self):
        """DATO LÍMITE: una sola unidad por encima del mínimo deja al producto fuera del reporte."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url)

        self.assertNotIn(self.sobre_el_minimo.id, self.ids_respuesta(respuesta))
        self.assertNotIn(self.suficiente.id, self.ids_respuesta(respuesta))

    def test_productos_agotados_aparecen_primero(self):
        """DATO VÁLIDO: los agotados encabezan la lista y luego se ordena por mayor faltante."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url)

        self.assertEqual(
            self.ids_respuesta(respuesta),
            [self.agotado.id, self.critico.id, self.igual_al_minimo.id]
        )

    def test_filtro_por_categoria(self):
        """DATO VÁLIDO: al indicar una categoría solo se listan sus productos críticos."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url, {'categoria': self.escritura.id})

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids_respuesta(respuesta), [self.agotado.id])

    def test_categoria_con_formato_invalido_es_rechazada(self):
        """DATO ERRÓNEO: un identificador de categoría no numérico se rechaza con un mensaje claro."""
        self.client.force_authenticate(user=self.administrador)
        respuesta = self.client.get(self.url, {'categoria': 'abc'})

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data['error'], 'El identificador de categoría no es válido.')

    def test_operador_no_puede_consultar_el_reporte(self):
        """DATO ERRÓNEO: un rol sin privilegios administrativos recibe acceso denegado."""
        self.client.force_authenticate(user=self.operador)
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_peticion_sin_autenticacion_es_rechazada(self):
        """DATO ERRÓNEO: sin token de sesión la petición no alcanza la vista."""
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)