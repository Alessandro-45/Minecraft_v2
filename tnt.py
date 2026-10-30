"""
TNT: al encenderla parpadea durante la mecha y luego explota, destruyendo una
esfera de bloques. La TNT alcanzada por la explosión se enciende en cadena.
"""

import math
import random

from panda3d.core import NodePath

from config import TNT_CHAIN_FUSE, TNT_FUSE, TNT_ID, TNT_RADIUS
from mesher import build_block_mesh


class TNTManager:
    def __init__(self, parent, world, on_explode):
        self.parent = parent
        self.world = world
        self.on_explode = on_explode  # Callback(centro) para efectos: empuje, temblor, mensaje
        self.active = []
        self._model = NodePath(build_block_mesh("tnt_model", {(0, 0, 0): TNT_ID}, lambda *_: False))

    def ignite(self, pos, fuse=TNT_FUSE):
        self.world.remove_block(*pos)

        # Nodo centrado en el bloque para poder escalarlo desde el centro
        holder = self.parent.attachNewNode("tnt_activa")
        holder.setPos(pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5)
        model = self._model.copyTo(holder)
        model.setPos(-0.5, -0.5, -0.5)
        self.active.append({"pos": pos, "timer": fuse, "np": holder})

    def clear(self):
        for tnt in self.active:
            tnt["np"].removeNode()
        self.active.clear()

    def update(self, dt):
        exploding = []
        for tnt in self.active:
            tnt["timer"] -= dt
            t = tnt["timer"]
            if t <= 0:
                exploding.append(tnt)
                continue

            # Parpadeo blanco cada vez más rápido y se "hincha" al final
            rate = 4 if t > 1.0 else 10
            flash = int(t * rate) % 2 == 0
            tnt["np"].setColorScale((2.2, 2.2, 2.2, 1) if flash else (1, 1, 1, 1))
            tnt["np"].setScale(1.0 + (0.15 * (1.0 - t) if t < 1.0 else 0.0))

        for tnt in exploding:
            self.active.remove(tnt)
            tnt["np"].removeNode()
            self._explode(tnt["pos"])

    def _explode(self, center):
        cx, cy, cz = center
        reach = math.ceil(TNT_RADIUS)
        r2 = TNT_RADIUS * TNT_RADIUS

        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                for dz in range(-reach, reach + 1):
                    if dx * dx + dy * dy + dz * dz > r2:
                        continue
                    x, y, z = cx + dx, cy + dy, cz + dz
                    if z <= 0:
                        continue  # La roca base es indestructible
                    block_id = self.world.remove_block(x, y, z)
                    if block_id == TNT_ID:
                        self.ignite((x, y, z), random.uniform(*TNT_CHAIN_FUSE))

        self.on_explode(center)
