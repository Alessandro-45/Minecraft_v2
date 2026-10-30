"""
Constantes y parámetros globales del juego (v2).
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Mundo
# -----------------------------------------------------------------------------
CHUNK_SIZE = 16             # Cada chunk es una sola malla de 16x16 columnas
WORLD_CHUNKS = 4            # 4x4 chunks -> mapa de 64x64 columnas
WORLD_SIZE = CHUNK_SIZE * WORLD_CHUNKS
WORLD_HEIGHT = 48           # Altura máxima donde se puede construir
BASE_HEIGHT = 11            # Altura media del terreno
TERRAIN_AMPLITUDE = 14      # Variación de altura del ruido
TERRAIN_SCALE = 26.0        # Mayor valor = colinas más anchas
SAND_LEVEL = 7              # Columnas por debajo de esta altura se cubren de arena
TREE_CHANCE = 0.012         # Probabilidad de árbol por columna de hierba

SAVE_FILE = Path(__file__).resolve().parent / "mundo_guardado.json"

# -----------------------------------------------------------------------------
# Jugador
# -----------------------------------------------------------------------------
REACH_DISTANCE = 6.0
PLAYER_RADIUS = 0.3
PLAYER_HEIGHT = 1.8
CROUCH_HEIGHT = 1.5
EYE_HEIGHT = 1.62
CROUCH_EYE_HEIGHT = 1.30
WALK_SPEED = 4.5
SPRINT_SPEED = 7.2
CROUCH_SPEED = 1.8
FLY_SPEED = 12.0
FLY_SPRINT_MULT = 1.8
GRAVITY = 26.0
JUMP_FORCE = 8.6
MOUSE_SENSITIVITY = 0.18
BASE_FOV = 80.0
SPRINT_FOV = 92.0

# -----------------------------------------------------------------------------
# Ciclo Día/Noche
# -----------------------------------------------------------------------------
DAY_LENGTH = 240.0          # Segundos reales que dura un día completo
START_TIME = 0.30           # 0 = medianoche, 0.25 = amanecer, 0.5 = mediodía, 0.75 = atardecer
FAST_TIME_MULT = 30.0       # Multiplicador al mantener T

# -----------------------------------------------------------------------------
# TNT
# -----------------------------------------------------------------------------
TNT_ID = 8
TNT_FUSE = 3.0                  # Segundos de mecha al encenderla
TNT_CHAIN_FUSE = (0.4, 1.0)     # Mecha aleatoria para TNT alcanzada por otra explosión
TNT_RADIUS = 3.5
TNT_KNOCKBACK = 16.0

# Inventario inicial (modo supervivencia). Lo demás se consigue rompiendo bloques.
STARTING_INVENTORY = {TNT_ID: 5}

# -----------------------------------------------------------------------------
# Tipos de Bloques (colores RGB por cara)
# -----------------------------------------------------------------------------
FACES = ("top", "bottom", "front", "back", "right", "left")


def _uniform(color):
    return {face: color for face in FACES}


def _top_side(top, side, bottom=None):
    colors = {face: side for face in FACES}
    colors["top"] = top
    colors["bottom"] = bottom if bottom is not None else side
    return colors


BLOCK_TYPES = {
    1: {"name": "Hierba", "colors": _top_side((0.35, 0.72, 0.22), (0.45, 0.32, 0.18), (0.45, 0.30, 0.16))},
    2: {"name": "Tierra", "colors": _uniform((0.48, 0.33, 0.18))},
    3: {"name": "Piedra", "colors": _top_side((0.58, 0.58, 0.58), (0.55, 0.55, 0.55))},
    4: {"name": "Madera", "colors": _top_side((0.65, 0.50, 0.32), (0.42, 0.28, 0.15))},
    5: {"name": "Hojas", "colors": _top_side((0.18, 0.55, 0.18), (0.16, 0.52, 0.16), (0.15, 0.48, 0.15))},
    6: {"name": "Arena", "colors": _top_side((0.88, 0.82, 0.58), (0.85, 0.79, 0.55))},
    7: {"name": "Ladrillo", "colors": _top_side((0.72, 0.32, 0.24), (0.68, 0.28, 0.20))},
    TNT_ID: {"name": "TNT", "colors": _top_side((0.86, 0.84, 0.78), (0.82, 0.18, 0.14), (0.86, 0.84, 0.78))},
}
