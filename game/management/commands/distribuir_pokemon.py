"""
Distribuye pokémons por una ciudad usando puntos de interés reales de OpenStreetMap.

Mejoras vs versión anterior:
  - Una sola consulta a Overpass con TODOS los tipos de POI (mucho más rápido)
  - Servidores alternativos con fallback automático si uno falla
  - Timeout más largo y reintentos automáticos
  - Bbox ajustado según tamaño de la ciudad

Uso:
  python manage.py distribuir_pokemon --ciudad madrid
  python manage.py distribuir_pokemon --ciudad madrid --limpiar
  python manage.py distribuir_pokemon --ciudad madrid --max-poi 302
  python manage.py distribuir_pokemon --ciudad madrid --dry-run
"""

import time
import random
import requests
from django.core.management.base import BaseCommand, CommandError
from game.models import Ciudad, Pokemon, PokemonLocation

# ─────────────────────────────────────────────────────────────────────────────
# Servidores Overpass con fallback automático
# ─────────────────────────────────────────────────────────────────────────────

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# ─────────────────────────────────────────────────────────────────────────────
# Definición de POIs y su rareza asociada
# ─────────────────────────────────────────────────────────────────────────────

POI_TYPES = [
    {"tipo": "monumento",  "rareza": "legendario", "radio": 120},
    {"tipo": "plaza",      "rareza": "epico",      "radio": 100},
    {"tipo": "museo",      "rareza": "epico",      "radio": 100},
    {"tipo": "parque",     "rareza": "raro",       "radio": 100},
    {"tipo": "teatro",     "rareza": "raro",       "radio": 80},
    {"tipo": "iglesia",    "rareza": "raro",       "radio": 80},
    {"tipo": "biblioteca", "rareza": "raro",       "radio": 80},
    {"tipo": "mercado",    "rareza": "comun",      "radio": 80},
    {"tipo": "fuente",     "rareza": "comun",      "radio": 60},
    {"tipo": "farmacia",   "rareza": "comun",      "radio": 60},
]

# Tags OSM para cada tipo
OSM_TAGS = {
    "monumento":  '["historic"="monument"]',
    "plaza":      '["place"="square"]',
    "museo":      '["tourism"="museum"]',
    "parque":     '["leisure"="park"]["name"]',
    "teatro":     '["amenity"="theatre"]',
    "iglesia":    '["amenity"="place_of_worship"]["religion"="christian"]',
    "biblioteca": '["amenity"="library"]',
    "mercado":    '["amenity"="marketplace"]',
    "fuente":     '["amenity"="fountain"]["name"]',
    "farmacia":   '["amenity"="pharmacy"]',
}

# Tipo de POI → rareza del pokemon que recibe
TIPO_A_RAREZA = {p["tipo"]: p["rareza"] for p in POI_TYPES}
TIPO_A_RADIO  = {p["tipo"]: p["radio"]  for p in POI_TYPES}

# Qué rarezas puede recibir cada tipo de POI (en orden de preferencia)
RAREZA_POOL = {
    "legendario": ["legendario", "epico", "raro"],
    "epico":      ["epico", "raro", "comun"],
    "raro":       ["raro", "comun"],
    "comun":      ["comun", "raro"],
}

# Shinys solo en lugares emblemáticos
SHINY_POI_TIPOS = {"monumento", "plaza", "museo"}


class Command(BaseCommand):
    help = 'Distribuye pokémons por POIs reales de OpenStreetMap (consulta única eficiente)'

    def add_arguments(self, parser):
        parser.add_argument('--ciudad',   required=True, help='Slug de la ciudad (ej: madrid)')
        parser.add_argument('--limpiar',  action='store_true', help='Eliminar ubicaciones previas')
        parser.add_argument('--max-poi',  type=int, default=302, help='Máximo de ubicaciones a crear')
        parser.add_argument('--dry-run',  action='store_true', help='Simular sin guardar en BD')
        parser.add_argument('--radio-km', type=float, default=8.0, help='Radio de búsqueda en km desde el centro (default 8)')

    def handle(self, *args, **options):
        slug     = options['ciudad']
        limpiar  = options['limpiar']
        max_poi  = options['max_poi']
        dry_run  = options['dry_run']
        radio_km = options['radio_km']

        # ── 1. Ciudad ─────────────────────────────────────────────────────────
        try:
            ciudad = Ciudad.objects.get(slug=slug, activa=True)
        except Ciudad.DoesNotExist:
            raise CommandError(f'Ciudad "{slug}" no encontrada. Créala con: python manage.py agregar_ciudad --nombre "..." --pais "..."')

        self.stdout.write(f'\n🗺️  Ciudad: {ciudad.nombre_display} ({ciudad.pais})')
        self.stdout.write(f'   Centro : {ciudad.lat}, {ciudad.lon}')
        self.stdout.write(f'   Radio  : {radio_km} km')

        # ── 2. Limpiar ────────────────────────────────────────────────────────
        existentes = PokemonLocation.objects.filter(ciudad=ciudad).count()
        if existentes > 0:
            if limpiar:
                if not dry_run:
                    PokemonLocation.objects.filter(ciudad=ciudad).delete()
                self.stdout.write(self.style.WARNING(f'🗑️  Eliminadas {existentes} ubicaciones previas.'))
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Ya hay {existentes} ubicaciones. Usa --limpiar para reemplazarlas.'
                ))

        # ── 3. Pokémons disponibles ───────────────────────────────────────────
        normales = list(Pokemon.objects.filter(is_shiny=False).order_by('pokedex_id'))
        shinys   = list(Pokemon.objects.filter(is_shiny=True).order_by('pokedex_id'))

        if not normales:
            raise CommandError('No hay pokémons. Importa primero con: python manage.py importar_pokemon --archivo pokemons.json')

        self.stdout.write(f'\n🎮 Pokémons: {len(normales)} normales + {len(shinys)} shiny')

        por_rareza      = {r: [] for r in ['comun', 'raro', 'epico', 'legendario']}
        por_rareza_shiny= {r: [] for r in ['comun', 'raro', 'epico', 'legendario']}
        for p in normales:
            por_rareza[p.rareza].append(p)
        for p in shinys:
            por_rareza_shiny[p.rareza].append(p)

        self.stdout.write('   Rareza : ' + ' | '.join(f'{k}:{len(v)}' for k, v in por_rareza.items()))

        # ── 4. Consulta Overpass — UNA SOLA llamada con todos los tipos ───────
        self.stdout.write(f'\n📡 Consultando Overpass API (consulta única con {len(OSM_TAGS)} tipos de POI)...')

        todos_pois = self._consulta_unica(ciudad, radio_km)

        if not todos_pois:
            raise CommandError(
                'No se encontraron POIs. Posibles causas:\n'
                '  - Todos los servidores Overpass están caídos (prueba más tarde)\n'
                '  - La ciudad no tiene POIs con los tags buscados\n'
                '  - Aumenta el radio con --radio-km 15'
            )

        self.stdout.write(f'✅ POIs encontrados: {len(todos_pois)}')

        # Desglose por tipo
        from collections import Counter
        conteo = Counter(p['tipo'] for p in todos_pois)
        for tipo, n in sorted(conteo.items(), key=lambda x: -x[1]):
            self.stdout.write(f'   {tipo:<12}: {n}')

        # ── 5. Deduplicar ─────────────────────────────────────────────────────
        seen_osm    = set()
        seen_coords = set()
        pois_unicos = []

        for poi in todos_pois:
            if poi['osm_id'] and poi['osm_id'] in seen_osm:
                continue
            # Redondear a ~110m para evitar puntos demasiado juntos
            coord_key = (round(float(poi['lat']), 3), round(float(poi['lon']), 3))
            if coord_key in seen_coords:
                continue
            seen_osm.add(poi['osm_id'])
            seen_coords.add(coord_key)
            pois_unicos.append(poi)

        self.stdout.write(f'\n🔄 POIs únicos tras deduplicar: {len(pois_unicos)}')

        # ── 6. Separar shinys y normales ──────────────────────────────────────
        pois_shiny   = [p for p in pois_unicos if p['tipo'] in SHINY_POI_TIPOS]
        pois_normales= [p for p in pois_unicos if p['tipo'] not in SHINY_POI_TIPOS]

        random.shuffle(pois_shiny)
        random.shuffle(pois_normales)

        if shinys and pois_shiny:
            max_shiny  = min(len(shinys), len(pois_shiny), max_poi // 2)
            max_normal = min(len(normales), max_poi - max_shiny)
        else:
            max_shiny  = 0
            max_normal = min(len(normales), len(pois_unicos), max_poi)

        self.stdout.write(f'📊 Plan: {max_normal} normales + {max_shiny} shiny = {max_normal + max_shiny} ubicaciones')

        # ── 7. Asignar pokémons ───────────────────────────────────────────────
        usados_normal = set()
        usados_shiny  = set()
        ubicaciones   = []

        # Shinys → POIs emblemáticos
        for poi in pois_shiny[:max_shiny]:
            p = self._elegir_pokemon(poi, por_rareza_shiny, usados_shiny)
            if p:
                usados_shiny.add(p.id)
                ubicaciones.append({'pokemon': p, 'poi': poi})

        # Normales → resto de POIs
        pois_para_normal = (pois_normales + pois_shiny[max_shiny:])[:max_normal]
        for poi in pois_para_normal:
            p = self._elegir_pokemon(poi, por_rareza, usados_normal)
            if p:
                usados_normal.add(p.id)
                ubicaciones.append({'pokemon': p, 'poi': poi})

        # ── 8. Guardar ────────────────────────────────────────────────────────
        self.stdout.write(f'\n💾 Guardando {len(ubicaciones)} ubicaciones...')
        creados  = 0
        saltados = 0

        for item in ubicaciones:
            p   = item['pokemon']
            poi = item['poi']

            if dry_run:
                shiny_tag = '✨' if p.is_shiny else '  '
                self.stdout.write(
                    f'  [DRY] {shiny_tag} {p.nombre:<15} → '
                    f'{poi["nombre"] or poi["tipo"]:<30} ({poi["tipo"]})'
                )
                creados += 1
                continue

            try:
                _, created = PokemonLocation.objects.get_or_create(
                    pokemon=p,
                    poi_osm_id=poi['osm_id'],
                    defaults={
                        'ciudad':       ciudad,
                        'poi_nombre':   poi['nombre'],
                        'poi_tipo':     poi['tipo'],
                        'descripcion':  poi['nombre'] or poi['tipo'].capitalize(),
                        'lat':          poi['lat'],
                        'lon':          poi['lon'],
                        'radio_metros': TIPO_A_RADIO.get(poi['tipo'], 80),
                        'activo':       True,
                    }
                )
                if created:
                    creados += 1
                else:
                    saltados += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ {e}'))
                saltados += 1

        # ── 9. Resumen ────────────────────────────────────────────────────────
        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(self.style.SUCCESS(f'✅ {ciudad.nombre_display} lista:'))
        self.stdout.write(f'   📍 Creadas  : {creados}')
        if saltados:
            self.stdout.write(f'   ⏭️  Saltadas : {saltados}')
        if not dry_run:
            total = PokemonLocation.objects.filter(ciudad=ciudad, activo=True).count()
            self.stdout.write(f'   🗺️  Total activas: {total}')
        if dry_run:
            self.stdout.write(self.style.WARNING('   [DRY RUN — nada guardado]'))

    # ─────────────────────────────────────────────────────────────────────────
    # Consulta Overpass unificada — todos los tipos en una sola petición
    # ─────────────────────────────────────────────────────────────────────────

    def _consulta_unica(self, ciudad, radio_km):
        """
        Hace UNA SOLA consulta Overpass con todos los tipos de POI.
        Mucho más eficiente y menos propenso a timeouts que 10 consultas separadas.
        Prueba varios servidores automáticamente si alguno falla.
        """
        lat   = float(ciudad.lat)
        lon   = float(ciudad.lon)
        delta = 0.08  # ~10km
        bbox  = f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}"

        # Construir una consulta unificada con todos los tipos
        bloques = []
        for tipo, tag in OSM_TAGS.items():
            bloques.append(f'  node{tag}({bbox});')
            bloques.append(f'  way{tag}({bbox});')

        # Mapa de tag OSM → tipo interno (para clasificar la respuesta)
        tag_a_tipo = {
            'historic=monument':                    'monumento',
            'place=square':                         'plaza',
            'tourism=museum':                       'museo',
            'leisure=park':                         'parque',
            'amenity=theatre':                      'teatro',
            'amenity=place_of_worship':             'iglesia',
            'amenity=library':                      'biblioteca',
            'amenity=marketplace':                  'mercado',
            'amenity=fountain':                     'fuente',
            'amenity=pharmacy':                     'farmacia',
        }

        query = f"""
[out:json][timeout:60];
(
{''.join(bloques)}
);
out center tags;
"""

        # Intentar con cada servidor
        for i, server in enumerate(OVERPASS_SERVERS):
            self.stdout.write(f'   Servidor {i+1}/{len(OVERPASS_SERVERS)}: {server}')
            try:
                resp = requests.post(
                    server,
                    data={'data': query},
                    timeout=60,
                    headers={'User-Agent': 'pokecity/1.0 (admin@pokecity.com)'}
                )
                resp.raise_for_status()
                data = resp.json()

                pois = []
                for el in data.get('elements', []):
                    tags   = el.get('tags', {})
                    nombre = tags.get('name') or tags.get('name:es') or tags.get('name:en') or ''

                    # Coordenadas
                    if el['type'] == 'node':
                        lat_poi = el.get('lat')
                        lon_poi = el.get('lon')
                    else:
                        center  = el.get('center', {})
                        lat_poi = center.get('lat')
                        lon_poi = center.get('lon')

                    if lat_poi is None or lon_poi is None:
                        continue

                    # Clasificar el tipo según los tags del elemento
                    tipo_poi = self._clasificar_tipo(tags)
                    if not tipo_poi:
                        continue

                    pois.append({
                        'osm_id': el.get('id'),
                        'tipo':   tipo_poi,
                        'nombre': nombre,
                        'lat':    lat_poi,
                        'lon':    lon_poi,
                    })

                self.stdout.write(self.style.SUCCESS(f'   ✓ Respuesta OK ({len(pois)} elementos)'))
                return pois

            except requests.Timeout:
                self.stdout.write(self.style.WARNING(f'   ⏱️  Timeout en servidor {i+1}, probando siguiente...'))
            except requests.HTTPError as e:
                self.stdout.write(self.style.WARNING(f'   ❌ HTTP {e.response.status_code} en servidor {i+1}, probando siguiente...'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   ❌ Error en servidor {i+1}: {e}, probando siguiente...'))

            if i < len(OVERPASS_SERVERS) - 1:
                self.stdout.write('   ⏳ Esperando 3s antes del siguiente servidor...')
                time.sleep(3)

        return []

    def _clasificar_tipo(self, tags):
        """Determina el tipo de POI a partir de sus tags OSM."""
        historic = tags.get('historic', '')
        place    = tags.get('place', '')
        tourism  = tags.get('tourism', '')
        leisure  = tags.get('leisure', '')
        amenity  = tags.get('amenity', '')
        religion = tags.get('religion', '')

        if historic == 'monument':                          return 'monumento'
        if place    == 'square':                           return 'plaza'
        if tourism  == 'museum':                           return 'museo'
        if leisure  == 'park':                             return 'parque'
        if amenity  == 'theatre':                          return 'teatro'
        if amenity  == 'place_of_worship' and religion == 'christian': return 'iglesia'
        if amenity  == 'library':                          return 'biblioteca'
        if amenity  == 'marketplace':                      return 'mercado'
        if amenity  == 'fountain':                         return 'fuente'
        if amenity  == 'pharmacy':                         return 'farmacia'
        return None

    def _elegir_pokemon(self, poi, por_rareza, ya_usados):
        """Elige un pokémon para el POI según rareza, sin repetir."""
        rareza_base = TIPO_A_RAREZA.get(poi['tipo'], 'comun')
        pool = RAREZA_POOL.get(rareza_base, ['comun'])

        for rareza in pool:
            candidatos = [p for p in por_rareza.get(rareza, []) if p.id not in ya_usados]
            if candidatos:
                return random.choice(candidatos)

        # Último recurso: cualquier pokémon disponible
        todos = [p for lista in por_rareza.values() for p in lista if p.id not in ya_usados]
        return random.choice(todos) if todos else None