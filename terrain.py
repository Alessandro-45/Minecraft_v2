"""
Generación procedural del terreno con ruido (value noise + fBm), sin dependencias externas.
"""

import math
import random

from config import (
    BASE_HEIGHT,
    SAND_LEVEL,
    TERRAIN_AMPLITUDE,
    TERRAIN_SCALE,
    TREE_CHANCE,
    WORLD_HEIGHT,
    WORLD_SIZE,
)


def _hash2(ix, iy, seed):
    """Hash entero determinista -> valor en [0, 1]."""
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF


def value_noise(x, y, seed):
    """Ruido suave 2D en [-1, 1] interpolando valores aleatorios en una rejilla."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)

    v00 = _hash2(ix, iy, seed)
    v10 = _hash2(ix + 1, iy, seed)
    v01 = _hash2(ix, iy + 1, seed)
    v11 = _hash2(ix + 1, iy + 1, seed)

    bottom = v00 + (v10 - v00) * sx
    top = v01 + (v11 - v01) * sx
    return (bottom + (top - bottom) * sy) * 2.0 - 1.0


def fbm(x, y, seed, octaves=4):
    """Suma de varias capas de ruido (colinas grandes + detalles pequeños)."""
    total, amplitude, frequency, norm = 0.0, 1.0, 1.0, 0.0
    for octave in range(octaves):
        total += value_noise(x * frequency, y * frequency, seed + octave * 101) * amplitude
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return total / norm


def generate_terrain(seed):
    """Devuelve un diccionario {(x, y, z): block_id} con el mundo completo."""
    rng = random.Random(seed)
    blocks = {}
    trees = []

    for x in range(WORLD_SIZE):
        for y in range(WORLD_SIZE):
            n = fbm(x / TERRAIN_SCALE, y / TERRAIN_SCALE, seed)
            h = int(BASE_HEIGHT + n * TERRAIN_AMPLITUDE)
            h = max(3, min(WORLD_HEIGHT - 12, h))

            # Base rocosa, capa de tierra y superficie
            for z in range(0, h - 3):
                blocks[(x, y, z)] = 3
            for z in range(h - 3, h):
                blocks[(x, y, z)] = 2

            surface = 6 if h < SAND_LEVEL else 1
            blocks[(x, y, h)] = surface

            margin = 2 <= x < WORLD_SIZE - 2 and 2 <= y < WORLD_SIZE - 2
            if surface == 1 and margin and rng.random() < TREE_CHANCE:
                trees.append((x, y, h))

    for x, y, h in trees:
        _build_tree(blocks, x, y, h, rng)

    return blocks


def _build_tree(blocks, x, y, base_h, rng):
    trunk_height = rng.randint(3, 5)
    top = base_h + trunk_height

    # Dos capas anchas de hojas (5x5 sin esquinas)
    for lz in (top - 1, top):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) == 2 and abs(dy) == 2:
                    continue
                blocks.setdefault((x + dx, y + dy, lz), 5)

    # Cruz en la cúspide
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        blocks.setdefault((x + dx, y + dy, top + 1), 5)

    # Tronco (sobrescribe las hojas del centro)
    for z in range(base_h + 1, top + 1):
        blocks[(x, y, z)] = 4
