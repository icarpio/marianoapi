"""
Importa pokémons desde un JSON. Soporta dos modos:

MODO 1 — Un solo JSON con los 302 (normales + shinys mezclados):
  [
    { "id": 1, "name": "bulbasaur", "isShiny": false, "image": "...", ... },
    { "id": 1, "name": "bulbasaur", "isShiny": true,  "image": "...", ... },
    ...
  ]

MODO 2 — Un JSON con solo los 151 normales (genera los shinys automáticamente):
  [
    { "id": 1, "name": "bulbasaur", "isShiny": false, "image": "https://.../normal/bulbasaur.png", ... },
    ...
  ]

Estructura esperada de cada entrada:
  {
    "id": 1,                          ← número de pokédex
    "name": "bulbasaur",              ← nombre
    "isShiny": false,                 ← true/false
    "image": "https://...",           ← URL de la imagen
    "tipos": ["grass", "poison"],
    "habilidades": ["overgrow", "chlorophyll"],
    "estadisticas_base": {
      "hp": 45, "attack": 49, "defense": 49,
      "special-attack": 65, "special-defense": 65, "speed": 45
    }
  }

Usos:
  # Importar archivo con los 302 (normales + shinys)
  python manage.py importar_pokemon --archivo pokemons_302.json

  # Importar solo 151 normales y generar shinys automáticamente
  python manage.py importar_pokemon --archivo pokemons_151.json --generar-shinys

  # Reimportar limpiando todo primero
  python manage.py importar_pokemon --archivo pokemons.json --limpiar

  # Ver qué importaría sin guardar
  python manage.py importar_pokemon --archivo pokemons.json --dry-run

Rareza asignada automáticamente por total de stats:
  < 400  → común
  400-499→ raro
  500-599→ épico
  ≥ 600  → legendario

Los shinys heredan la misma rareza que su versión normal.
Los shinys valen el doble de puntos al capturarlos (lógica en views.py).
"""

import json
from django.core.management.base import BaseCommand, CommandError
from game.models import Pokemon, Tipo, Habilidad


# Pokédex IDs que se consideran legendarios/míticos (Gen 1)
# Estos sobreescriben el cálculo por stats si es necesario
LEGENDARIOS_IDS = {144, 145, 146, 150, 151}  # Articuno, Zapdos, Moltres, Mewtwo, Mew
EPICOS_IDS      = {130, 143}                  # Gyarados, Snorlax (semi-legendarios populares)


def calcular_rareza(pokedex_id, total_stats):
    """Determina la rareza según stats Y si es legendario conocido."""
    if pokedex_id in LEGENDARIOS_IDS:
        return 'legendario'
    if pokedex_id in EPICOS_IDS:
        return 'epico'
    if total_stats >= 600:
        return 'legendario'
    if total_stats >= 500:
        return 'epico'
    if total_stats >= 400:
        return 'raro'
    return 'comun'


def generar_imagen_shiny(imagen_normal):
    """
    Intenta derivar la URL de la imagen shiny a partir de la normal.
    Funciona con pokemondb.net y algunas otras fuentes comunes.
    """
    if not imagen_normal:
        return ''
    # pokemondb.net: /sprites/home/normal/ → /sprites/home/shiny/
    if '/normal/' in imagen_normal:
        return imagen_normal.replace('/normal/', '/shiny/')
    # Otras convenciones comunes
    if '/regular/' in imagen_normal:
        return imagen_normal.replace('/regular/', '/shiny/')
    # Si ya es shiny o no reconocemos el patrón, devolver igual
    return imagen_normal


class Command(BaseCommand):
    help = 'Importa 151 o 302 pokémons desde un JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo', type=str, required=True,
            help='Ruta al archivo JSON'
        )
        parser.add_argument(
            '--generar-shinys', action='store_true',
            help='Si el JSON solo tiene los 151 normales, genera automáticamente los 151 shinys'
        )
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Elimina TODOS los pokémons antes de importar (¡cuidado! borra colecciones)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra lo que importaría sin guardar nada en la BD'
        )

    def handle(self, *args, **options):
        ruta          = options['archivo']
        generar_shinys= options['generar_shinys']
        limpiar       = options['limpiar']
        dry_run       = options['dry_run']

        # ── 1. Leer JSON ──────────────────────────────────────────────────────
        try:
            with open(ruta, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Archivo no encontrado: {ruta}')
        except json.JSONDecodeError as e:
            raise CommandError(f'JSON inválido: {e}')

        if not isinstance(data, list) or not data:
            raise CommandError('El JSON debe ser una lista no vacía de pokémons.')

        self.stdout.write(f'\n📂 Archivo: {ruta}')
        self.stdout.write(f'   Entradas en el JSON: {len(data)}')

        # ── 2. Limpiar si se pide ─────────────────────────────────────────────
        if limpiar:
            if dry_run:
                self.stdout.write(self.style.WARNING('[DRY] Se eliminarían todos los pokémons.'))
            else:
                n = Pokemon.objects.count()
                Pokemon.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'🗑️  Eliminados {n} pokémons previos.'))

        # ── 3. Separar normales y shinys del JSON ─────────────────────────────
        normales_json = [p for p in data if not p.get('isShiny', False)]
        shinys_json   = [p for p in data if p.get('isShiny', False)]

        self.stdout.write(f'   Normales en JSON: {len(normales_json)}')
        self.stdout.write(f'   Shinys en JSON:   {len(shinys_json)}')

        # ── 4. Generar shinys si no están en el JSON ──────────────────────────
        if generar_shinys and not shinys_json:
            self.stdout.write('✨ Generando 151 shinys automáticamente...')
            for item in normales_json:
                imagen_normal = item.get('image', '')
                shinys_json.append({
                    **item,
                    'isShiny': True,
                    'image':   generar_imagen_shiny(imagen_normal),
                    # El ID de pokédex es el mismo; se distinguen por is_shiny en la BD
                })
            self.stdout.write(f'   Shinys generados: {len(shinys_json)}')
        elif generar_shinys and shinys_json:
            self.stdout.write(self.style.WARNING(
                '⚠️  --generar-shinys ignorado: el JSON ya contiene shinys.'
            ))

        todos = normales_json + shinys_json
        self.stdout.write(f'\n🎮 Total a importar: {len(todos)} pokémons\n')

        # ── 5. Importar ───────────────────────────────────────────────────────
        creados      = 0
        actualizados = 0
        errores      = 0

        for item in todos:
            try:
                stats = item.get('estadisticas_base', {})
                if not isinstance(stats, dict):
                    stats = {}

                total_stats = sum(stats.values()) if stats else 0
                pokedex_id  = int(item['id'])
                is_shiny    = bool(item.get('isShiny', False))
                nombre      = item.get('name', '').strip().lower()

                if not nombre:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  Entrada sin nombre (id={pokedex_id}), saltando.'))
                    errores += 1
                    continue

                imagen_normal = item.get('image', '')
                if is_shiny:
                    # Si es shiny, la imagen del campo image ya debería ser la shiny
                    imagen       = imagen_normal
                    imagen_shiny = imagen_normal
                else:
                    imagen       = imagen_normal
                    imagen_shiny = generar_imagen_shiny(imagen_normal)

                rareza = calcular_rareza(pokedex_id, total_stats)

                # En la BD distinguimos normal vs shiny con un pokedex_id especial:
                # normales: pokedex_id = id real (1-151)
                # shinys:   pokedex_id = id real + 1000  (1001-1151)
                # Así ambos conviven sin conflicto de unique_together
                db_pokedex_id = pokedex_id + 1000 if is_shiny else pokedex_id

                defaults = {
                    'nombre':          nombre,
                    'imagen':          imagen,
                    'imagen_shiny':    imagen_shiny,
                    'is_shiny':        is_shiny,
                    'hp':              stats.get('hp', 0),
                    'attack':          stats.get('attack', 0),
                    'defense':         stats.get('defense', 0),
                    'special_attack':  stats.get('special-attack', 0),
                    'special_defense': stats.get('special-defense', 0),
                    'speed':           stats.get('speed', 0),
                    'rareza':          rareza,
                }

                if dry_run:
                    shiny_tag = '✨ SHINY' if is_shiny else '      '
                    self.stdout.write(
                        f'  [DRY] #{db_pokedex_id:04d} {shiny_tag} {nombre:<15} '
                        f'stats={total_stats} rareza={rareza}'
                    )
                    creados += 1
                    continue

                poke, created = Pokemon.objects.update_or_create(
                    pokedex_id=db_pokedex_id,
                    defaults=defaults,
                )

                # Tipos
                poke.tipos.clear()
                for t in item.get('tipos', []):
                    tipo, _ = Tipo.objects.get_or_create(nombre=t.strip().lower())
                    poke.tipos.add(tipo)

                # Habilidades
                poke.habilidades.clear()
                for h in item.get('habilidades', []):
                    hab, _ = Habilidad.objects.get_or_create(nombre=h.strip().lower())
                    poke.habilidades.add(hab)

                if created:
                    creados += 1
                    shiny_tag = ' ✨' if is_shiny else ''
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ #{db_pokedex_id:04d} {nombre}{shiny_tag} '
                            f'[{rareza}] stats={total_stats}'
                        )
                    )
                else:
                    actualizados += 1

            except (KeyError, ValueError, TypeError) as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error en entrada {item}: {e}'))
                errores += 1

        # ── 6. Resumen ────────────────────────────────────────────────────────
        self.stdout.write('\n' + '─' * 50)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Se importarían {creados} pokémons. Nada guardado.'
            ))
            return

        total_bd = Pokemon.objects.count()
        normales_bd = Pokemon.objects.filter(is_shiny=False).count()
        shinys_bd   = Pokemon.objects.filter(is_shiny=True).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Importación completada:'
        ))
        self.stdout.write(f'   ✓ Creados:      {creados}')
        self.stdout.write(f'   ↺ Actualizados: {actualizados}')
        if errores:
            self.stdout.write(self.style.WARNING(f'   ✗ Errores:      {errores}'))

        self.stdout.write(f'\n📊 Total en BD:')
        self.stdout.write(f'   Normales: {normales_bd}')
        self.stdout.write(f'   Shinys:   {shinys_bd}  ✨')
        self.stdout.write(f'   Total:    {total_bd}')

        # Desglose por rareza
        self.stdout.write(f'\n🏅 Por rareza:')
        for rareza in ['comun', 'raro', 'epico', 'legendario']:
            n = Pokemon.objects.filter(rareza=rareza).count()
            emoji = {'comun':'⚪','raro':'🔵','epico':'🟣','legendario':'🟡'}[rareza]
            self.stdout.write(f'   {emoji} {rareza:<12}: {n}')

        if total_bd > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n🚀 Listo. Ahora distribuye con:'
                f'\n   python manage.py distribuir_pokemon --ciudad <slug> --max-poi {total_bd}'
            ))