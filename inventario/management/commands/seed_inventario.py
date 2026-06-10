from django.conf import settings
from django.core.management.base import BaseCommand
from inventario.models import Categoria, Producto


# =============================================================================
# Datos de ejemplo para libreria/papeleria (SOLO desarrollo).
# =============================================================================
CATALOGO = {
    'CUADERNOS Y LIBRETAS': [
        ('Cuaderno universitario 100 hojas', 50, 20, 10),
        ('Cuaderno espiral cuadriculado',    40, 15, 10),
        ('Libreta de apuntes pequeña',       30, 10, 8),
    ],
    'ESCRITURA': [
        ('Lápiz HB #2 (caja)',      100, 30, 20),
        ('Lapicero tinta azul',      80, 25, 15),
        ('Lapicero tinta negra',      5,  2, 15),   # stock critico (demo)
        ('Borrador blanco',          60, 20, 10),
    ],
    'PAPEL Y CARTULINA': [
        ('Resma papel bond carta',       40,  5, 8),
        ('Cartulina de colores (paquete)', 25, 8, 5),
        ('Papel lustre',                  3,  1, 10),  # stock critico (demo)
    ],
    'ARTE Y MANUALIDADES': [
        ('Caja de crayones 12 colores', 35, 12, 8),
        ('Témpera 6 colores',           20,  6, 5),
        ('Pinceles set x3',             18,  5, 4),
    ],
    'OFICINA Y ARCHIVO': [
        ('Folder manila carta',  200, 40, 30),
        ('Engrapadora metálica',  15,  4, 3),
        ('Caja de clips',         50, 10, 8),
    ],
    'ADHESIVOS Y PEGAMENTOS': [
        ('Pegamento en barra',            45, 15, 10),
        ('Cinta adhesiva transparente',   30, 10, 6),
        ('Silicón líquido',               22,  7, 5),
    ],
    'GEOMETRÍA Y MEDICIÓN': [
        ('Juego geométrico (regla y escuadras)', 28, 9, 6),
        ('Regla 30cm',                           60, 18, 12),
        ('Compás metálico',                      16,  5, 4),
    ],
    'MOCHILAS Y LONCHERAS': [
        ('Mochila escolar mediana', 12, 6, 3),
        ('Lonchera térmica',        10, 4, 3),
    ],
}


class Command(BaseCommand):
    help = 'Crea categorias y productos de ejemplo para la libreria (SOLO para desarrollo).'

    def handle(self, *args, **options):
        # nunca ejecutar en produccion.
        if not settings.DEBUG:
            self.stdout.write(self.style.ERROR(
                'Seed bloqueado: solo se puede ejecutar con DEBUG=True (entorno de desarrollo).'
            ))
            return

        cat_creadas = 0
        prod_creados = 0
        prod_existentes = 0

        for nombre_categoria, productos in CATALOGO.items():
            # El modelo guarda el nombre en mayusculas
            categoria, creada = Categoria.objects.get_or_create(nombre=nombre_categoria.upper())
            if creada:
                cat_creadas += 1
                self.stdout.write(self.style.SUCCESS(f'Categoria creada: {categoria.nombre}'))

            for (nombre_prod, bodega, vitrina, minimo) in productos:
                producto, creado = Producto.objects.get_or_create(
                    nombre=nombre_prod,
                    categoria=categoria,
                    defaults={
                        'stock_bodega': bodega,
                        'stock_vitrina': vitrina,
                        'stock_minimo': minimo,
                    }
                )
                if creado:
                    prod_creados += 1
                    self.stdout.write(f'   Producto: {nombre_prod} (B:{bodega} V:{vitrina})')
                else:
                    prod_existentes += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. {cat_creadas} categoria(s) y {prod_creados} producto(s) creados. '
            f'{prod_existentes} producto(s) ya existian.'
        ))