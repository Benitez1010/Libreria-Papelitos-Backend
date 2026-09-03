from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from inventario.models import Categoria, Producto

class CategoriaEliminacionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat_vacia = Categoria.objects.create(nombre="OFICINA")
        self.cat_con_producto = Categoria.objects.create(nombre="LIBROS")
        self.producto = Producto.objects.create(
            nombre="Cuaderno Espiral",
            categoria=self.cat_con_producto,
            stock_bodega=10,
            stock_vitrina=5,
            stock_minimo=3
        )

    def test_01_bloquear_eliminacion_modelo_con_productos(self):
        """Verifica que el método delete del modelo bloquea y lanza ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.cat_con_producto.delete()
        self.assertIn("No se puede eliminar: existen productos bajo esta categoría.", str(ctx.exception))

    def test_02_eliminar_modelo_categoria_vacia(self):
        """Verifica que el modelo permite la eliminación física si no tiene productos."""
        id_categoria = self.cat_vacia.id
        self.cat_vacia.delete()
        self.assertFalse(Categoria.objects.filter(id=id_categoria).exists())

    def test_03_api_bloquear_eliminacion_categoria_con_productos(self):
        """Verifica que la API retorne 400 y el mensaje exacto para categoría ocupada."""
        response = self.client.delete(f"/api/categorias/{self.cat_con_producto.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data.get("message"),
            "No se puede eliminar: existen productos bajo esta categoría."
        )

    def test_04_api_eliminar_categoria_vacia_exitosamente(self):
        """Verifica que la API elimine correctamente con status 200."""
        response = self.client.delete(f"/api/categorias/{self.cat_vacia.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Categoria.objects.filter(id=self.cat_vacia.id).exists())

    def test_05_api_eliminar_categoria_inexistente(self):
        """Verifica el comportamiento de la API frente a un ID no registrado (404)."""
        response = self.client.delete("/api/categorias/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)