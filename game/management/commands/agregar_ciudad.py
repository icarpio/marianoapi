"""
Añade una ciudad consultando Nominatim (OpenStreetMap) para obtener las coordenadas.

Uso:
  python manage.py añadir_ciudad --nombre "Buenos Aires" --pais "Argentina"
  python manage.py añadir_ciudad --nombre "Tokyo" --pais "Japan"
  python manage.py añadir_ciudad --nombre "Madrid" --pais "España"
"""
import time
import requests
from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from game.models import Ciudad


class Command(BaseCommand):
    help = 'Añade una ciudad nueva obteniendo sus coordenadas automáticamente'

    def add_arguments(self, parser):
        parser.add_argument('--nombre', required=True,  help='Nombre de la ciudad, ej: "Buenos Aires"')
        parser.add_argument('--pais',   required=False, default='', help='País, ej: "Argentina"')
        parser.add_argument('--zoom',   type=int, default=15, help='Zoom inicial del mapa (default 15)')

    def handle(self, *args, **options):
        nombre = options['nombre'].strip()
        pais   = options['pais'].strip()
        zoom   = options['zoom']
        slug   = slugify(nombre)

        if Ciudad.objects.filter(slug=slug).exists():
            raise CommandError(f'La ciudad "{nombre}" ya existe (slug: {slug}).')

        # Consultar Nominatim
        query = f"{nombre}, {pais}" if pais else nombre
        self.stdout.write(f'Buscando coordenadas para "{query}"...')

        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'pokecity/1.0 (admin@pokecity.com)'},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise CommandError(f'Error consultando Nominatim: {e}')

        if not data:
            raise CommandError(f'No se encontraron coordenadas para "{query}". Prueba con otro nombre.')

        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        self.stdout.write(f'  Coordenadas: {lat}, {lon}')

        ciudad = Ciudad.objects.create(
            nombre_display=nombre,
            slug=slug,
            pais=pais,
            lat=lat,
            lon=lon,
            zoom_inicial=zoom,
            activa=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Ciudad creada: {ciudad} (id={ciudad.id}, slug={ciudad.slug})'
        ))
        self.stdout.write(f'   Los pokémons de esta ciudad se añaden desde el admin o con ubicar_pokemon.')

        time.sleep(1)  # respetar rate limit de Nominatim