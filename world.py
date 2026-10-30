"""
Mundo voxel dividido en chunks. Guarda los bloques, reconstruye solo las mallas
modificadas y resuelve el raycasting por recorrido de rejilla (DDA).
"""

import math

from config import CHUNK_SIZE, WORLD_HEIGHT
from mesher import build_block_mesh


class World:
    def __init__(self, parent):
        self.root = parent.attachNewNode("world")
        self.chunks = {}       # (cx, cy) -> {(x, y, z): block_id}
        self.chunk_nodes = {}  # (cx, cy) -> NodePath con la malla del chunk
        self.dirty = set()     # Chunks que hay que volver a mallar
        self.seed = 0

    # -------------------------------------------------------------------------
    # Consulta y edición de bloques
    # -------------------------------------------------------------------------
    @staticmethod
    def chunk_key(x, y):
        return (x // CHUNK_SIZE, y // CHUNK_SIZE)

    def get(self, x, y, z):
        chunk = self.chunks.get((x // CHUNK_SIZE, y // CHUNK_SIZE))
        return chunk.get((x, y, z)) if chunk else None

    def is_solid(self, x, y, z):
        return self.get(x, y, z) is not None

    def block_count(self):
        return sum(len(chunk) for chunk in self.chunks.values())

    def set_block(self, x, y, z, block_id):
        if not 0 <= z < WORLD_HEIGHT:
            return False
        self.chunks.setdefault(self.chunk_key(x, y), {})[(x, y, z)] = block_id
        self._mark_dirty(x, y)
        return True

    def remove_block(self, x, y, z):
        """Elimina el bloque y devuelve su tipo (o None si no había nada)."""
        chunk = self.chunks.get(self.chunk_key(x, y))
        if not chunk:
            return None
        block_id = chunk.pop((x, y, z), None)
        if block_id is not None:
            self._mark_dirty(x, y)
        return block_id

    def _mark_dirty(self, x, y):
        cx, cy = self.chunk_key(x, y)
        self.dirty.add((cx, cy))

        # Si el bloque está en el borde, el chunk vecino también cambia de caras visibles
        lx, ly = x % CHUNK_SIZE, y % CHUNK_SIZE
        if lx == 0:
            self.dirty.add((cx - 1, cy))
        elif lx == CHUNK_SIZE - 1:
            self.dirty.add((cx + 1, cy))
        if ly == 0:
            self.dirty.add((cx, cy - 1))
        elif ly == CHUNK_SIZE - 1:
            self.dirty.add((cx, cy + 1))

    # -------------------------------------------------------------------------
    # Carga completa y mallado
    # -------------------------------------------------------------------------
    def load_blocks(self, blocks, seed):
        for node in self.chunk_nodes.values():
            node.removeNode()
        self.chunk_nodes.clear()
        self.chunks.clear()
        self.seed = seed

        for (x, y, z), block_id in blocks.items():
            self.chunks.setdefault(self.chunk_key(x, y), {})[(x, y, z)] = block_id

        self.dirty = set(self.chunks.keys())
        self.rebuild_dirty()

    def rebuild_dirty(self):
        for key in self.dirty:
            self._build_chunk(key)
        self.dirty.clear()

    def _build_chunk(self, key):
        old = self.chunk_nodes.pop(key, None)
        if old is not None:
            old.removeNode()

        blocks = self.chunks.get(key)
        if not blocks:
            return
        node = build_block_mesh(f"chunk_{key[0]}_{key[1]}", blocks, self._occludes)
        if node is not None:
            self.chunk_nodes[key] = self.root.attachNewNode(node)

    def _occludes(self, x, y, z):
        # Debajo de la capa 0 nunca se ve nada: no dibujamos esas caras
        return z < 0 or self.is_solid(x, y, z)

    # -------------------------------------------------------------------------
    # Raycasting voxel (Amanatides & Woo)
    # -------------------------------------------------------------------------
    def raycast(self, origin, direction, max_dist):
        """
        Recorre las celdas que atraviesa el rayo. Devuelve (bloque, normal_de_cara)
        del primer bloque sólido, o (None, None) si no hay nada al alcance.
        `direction` debe estar normalizada.
        """
        pos = [math.floor(origin[0]), math.floor(origin[1]), math.floor(origin[2])]
        step = [0, 0, 0]
        t_max = [math.inf] * 3
        t_delta = [math.inf] * 3

        for i in range(3):
            d = direction[i]
            if d > 0:
                step[i] = 1
                t_delta[i] = 1.0 / d
                t_max[i] = (pos[i] + 1 - origin[i]) / d
            elif d < 0:
                step[i] = -1
                t_delta[i] = -1.0 / d
                t_max[i] = (origin[i] - pos[i]) / -d

        normal = (0, 0, 0)
        t = 0.0
        while t <= max_dist:
            if self.is_solid(*pos):
                return tuple(pos), normal
            axis = min(range(3), key=t_max.__getitem__)
            t = t_max[axis]
            pos[axis] += step[axis]
            t_max[axis] += t_delta[axis]
            n = [0, 0, 0]
            n[axis] = -step[axis]
            normal = tuple(n)

        return None, None

    # -------------------------------------------------------------------------
    # Guardado
    # -------------------------------------------------------------------------
    def serialize(self):
        return {
            "seed": self.seed,
            "blocks": [[x, y, z, b] for chunk in self.chunks.values() for (x, y, z), b in chunk.items()],
        }

    def deserialize(self, data):
        blocks = {(x, y, z): b for x, y, z, b in data["blocks"]}
        self.load_blocks(blocks, data.get("seed", 0))
