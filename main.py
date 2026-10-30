"""
Minecraft Prototype v2 - Python & Panda3D
=========================================
Mejoras sobre la versión original:
- Mundo de 64x64 con terreno por ruido, dividido en chunks (una malla por chunk,
  solo caras visibles) -> mucho más rápido que un nodo por bloque.
- Ciclo día/noche: sol y luna que giran, cielo/niebla dinámicos y estrellas.
- Bloque TNT (8): se enciende con E, parpadea y explota en cadena.
- Sprint (Ctrl) con cambio de FOV y agacharse (Shift) sin caer de los bordes.
- Inventario con conteo en supervivencia (en vuelo/creativo es infinito).
- Guardar (F5) y cargar (F9) el mundo en JSON.

Ejecutar desde esta carpeta:  python main.py
"""

import json
import math
import random

from panda3d.core import loadPrcFileData

loadPrcFileData("", "window-title Minecraft Prototype v2 - Python & Panda3D\nwin-size 1280 720\nsync-video true")

from direct.showbase.ShowBase import ShowBase  # noqa: E402
from panda3d.core import (  # noqa: E402
    ClockObject,
    KeyboardButton,
    LineSegs,
    ModifierButtons,
    WindowProperties,
)

from config import (  # noqa: E402
    BASE_FOV,
    BLOCK_TYPES,
    FAST_TIME_MULT,
    MOUSE_SENSITIVITY,
    REACH_DISTANCE,
    SAVE_FILE,
    SPRINT_FOV,
    STARTING_INVENTORY,
    TNT_ID,
    TNT_KNOCKBACK,
    TNT_RADIUS,
    WORLD_SIZE,
)
from daynight import DayNightCycle  # noqa: E402
from hud import HUD  # noqa: E402
from inventory import Inventory  # noqa: E402
from player import Player  # noqa: E402
from terrain import generate_terrain  # noqa: E402
from tnt import TNTManager  # noqa: E402
from world import World  # noqa: E402

globalClock = ClockObject.getGlobalClock()
INPUT_KEYS = ("forward", "backward", "left", "right", "jump", "crouch", "sprint", "fast_time")


class MinecraftApp(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camLens.setFov(BASE_FOV)
        self.camLens.setNearFar(0.05, 500)

        # Sin esto, mantener Shift/Ctrl convierte "1" en "shift-1", "mouse1" en "control-mouse1", etc.
        self.mouseWatcherNode.setModifierButtons(ModifierButtons())
        self.buttonThrowers[0].node().setModifierButtons(ModifierButtons())

        self.world = World(self.render)
        self.player = Player(self.world)
        self.inventory = Inventory(STARTING_INVENTORY)
        self.daynight = DayNightCycle(self)
        self.hud = HUD(self)
        self.tnt = TNTManager(self.render, self.world, self.on_explosion)

        self.current_block = 1
        self.selection_box = self.create_selection_box()
        self.targeted_block = None
        self.targeted_normal = None

        self.eye_height = self.player.eye_height
        self.fov = BASE_FOV
        self.shake = 0.0
        self.status_timer = 0.0
        self.mouse_locked = False

        self.setup_controls()
        self.new_world()
        self.set_mouse_lock(True)
        self.taskMgr.add(self.update, "game_update_task")

    # -------------------------------------------------------------------------
    # Mundo
    # -------------------------------------------------------------------------
    def new_world(self, seed=None):
        seed = random.randrange(1 << 30) if seed is None else seed
        self.tnt.clear()
        self.world.load_blocks(generate_terrain(seed), seed)
        self.player.spawn(WORLD_SIZE // 2, WORLD_SIZE // 2)
        self.inventory.reset(STARTING_INVENTORY)
        self.refresh_hotbar()
        self.hud.show_message(f"Mundo nuevo (semilla {seed})")

    def create_selection_box(self):
        """Contorno de alambre ligeramente mayor que un bloque (que ocupa [0, 1])."""
        lines = LineSegs("block_selection_outline")
        lines.setColor(0.05, 0.05, 0.05, 1.0)
        lines.setThickness(2.2)
        lo, hi = -0.005, 1.005

        for z in (lo, hi):
            lines.moveTo(lo, lo, z)
            lines.drawTo(hi, lo, z)
            lines.drawTo(hi, hi, z)
            lines.drawTo(lo, hi, z)
            lines.drawTo(lo, lo, z)
        for x, y in ((lo, lo), (hi, lo), (hi, hi), (lo, hi)):
            lines.moveTo(x, y, lo)
            lines.drawTo(x, y, hi)

        np = self.render.attachNewNode(lines.create())
        np.setLightOff()
        np.hide()
        return np

    # -------------------------------------------------------------------------
    # Controles
    # -------------------------------------------------------------------------
    def setup_controls(self):
        self.accept("f", self.toggle_fly_mode)
        self.accept("r", self.new_world)
        self.accept("e", self.ignite_targeted_tnt)
        self.accept("f5", self.save_game)
        self.accept("f9", self.load_game)
        self.accept("escape", self.toggle_mouse_lock)

        for block_id in BLOCK_TYPES:
            self.accept(str(block_id), self.select_block, [block_id])
        self.accept("wheel_up", self.cycle_block, [-1])
        self.accept("wheel_down", self.cycle_block, [1])

        self.accept("mouse1", self.on_left_click)
        self.accept("mouse3", self.on_right_click)

    def read_input(self):
        """Lee el teclado por sondeo (más fiable que eventos al combinar Shift/Ctrl)."""
        if not self.mouse_locked or not self.mouseWatcherNode.hasMouse():
            return dict.fromkeys(INPUT_KEYS, False)

        is_down = self.mouseWatcherNode.isButtonDown

        def key(char):
            return is_down(KeyboardButton.asciiKey(char))

        def any_down(*buttons):
            return any(is_down(b) for b in buttons)

        return {
            "forward": key("w"),
            "backward": key("s"),
            "left": key("a"),
            "right": key("d"),
            "jump": is_down(KeyboardButton.space()),
            "crouch": any_down(KeyboardButton.shift(), KeyboardButton.lshift(), KeyboardButton.rshift()),
            "sprint": any_down(KeyboardButton.control(), KeyboardButton.lcontrol(), KeyboardButton.rcontrol()),
            "fast_time": key("t"),
        }

    def select_block(self, block_id):
        self.current_block = block_id
        self.refresh_hotbar()

    def cycle_block(self, step):
        keys = list(BLOCK_TYPES.keys())
        idx = (keys.index(self.current_block) + step) % len(keys)
        self.select_block(keys[idx])

    def toggle_fly_mode(self):
        self.player.fly = not self.player.fly
        self.player.vel = [0.0, 0.0, 0.0]
        self.refresh_hotbar()
        self.hud.show_message("Modo vuelo (creativo)" if self.player.fly else "Modo supervivencia")

    def toggle_mouse_lock(self):
        self.set_mouse_lock(not self.mouse_locked)

    def set_mouse_lock(self, locked):
        self.mouse_locked = locked
        props = WindowProperties()
        props.setCursorHidden(locked)
        self.win.requestProperties(props)
        if locked:
            self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)

    def refresh_hotbar(self):
        self.hud.set_hotbar(self.current_block, self.inventory, creative=self.player.fly)

    # -------------------------------------------------------------------------
    # Acciones con bloques
    # -------------------------------------------------------------------------
    def on_left_click(self):
        if not self.mouse_locked:
            self.set_mouse_lock(True)
            return
        if not self.targeted_block:
            return

        x, y, z = self.targeted_block
        if z == 0:
            self.hud.show_message("La roca base es indestructible", 1.5)
            return

        block_id = self.world.remove_block(x, y, z)
        if block_id is not None and not self.player.fly:
            self.inventory.add(block_id)
            self.refresh_hotbar()

    def on_right_click(self):
        if not self.mouse_locked:
            self.set_mouse_lock(True)
            return
        if not self.targeted_block:
            return

        target = tuple(b + n for b, n in zip(self.targeted_block, self.targeted_normal))
        if self.world.is_solid(*target) or self.player.intersects_block(*target):
            return

        creative = self.player.fly
        if not creative and not self.inventory.take(self.current_block):
            name = BLOCK_TYPES[self.current_block]["name"]
            self.hud.show_message(f"No tienes {name}. Rompe bloques para conseguirlos.", 1.8)
            return

        if not self.world.set_block(*target, self.current_block) and not creative:
            self.inventory.add(self.current_block)  # Fuera de límites: devolver el bloque
        self.refresh_hotbar()

    def ignite_targeted_tnt(self):
        if self.targeted_block and self.world.get(*self.targeted_block) == TNT_ID:
            self.tnt.ignite(self.targeted_block)
            self.hud.show_message("TNT encendida! Corre!", 1.5)

    def on_explosion(self, center):
        cx, cy, cz = (c + 0.5 for c in center)
        px, py, pz = self.player.pos
        pz += self.player.height / 2
        dx, dy, dz = px - cx, py - cy, pz - cz
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        blast_reach = TNT_RADIUS * 2.5
        if dist < blast_reach:
            strength = 1.0 - dist / blast_reach
            if dist > 0.01:
                dx, dy = dx / dist, dy / dist
            self.player.knockback(dx * TNT_KNOCKBACK * strength, dy * TNT_KNOCKBACK * strength,
                                  6.0 + 6.0 * strength)
        self.shake = max(self.shake, max(0.15, 0.8 * (1.0 - dist / 30.0)))
        self.hud.show_message("BOOM!", 1.0)

    # -------------------------------------------------------------------------
    # Guardar / Cargar
    # -------------------------------------------------------------------------
    def save_game(self):
        data = {
            "version": 2,
            "world": self.world.serialize(),
            "player": self.player.serialize(),
            "inventory": self.inventory.serialize(),
            "time": self.daynight.time,
            "current_block": self.current_block,
        }
        try:
            SAVE_FILE.write_text(json.dumps(data))
            self.hud.show_message(f"Mundo guardado en {SAVE_FILE.name}")
        except OSError as err:
            self.hud.show_message(f"Error al guardar: {err}")

    def load_game(self):
        if not SAVE_FILE.exists():
            self.hud.show_message("No hay partida guardada (usa F5)")
            return
        try:
            data = json.loads(SAVE_FILE.read_text())
            self.tnt.clear()
            self.world.deserialize(data["world"])
            self.player.deserialize(data["player"])
            self.inventory.deserialize(data["inventory"])
            self.daynight.time = data.get("time", self.daynight.time)
            self.current_block = data.get("current_block", 1)
        except (OSError, ValueError, KeyError, TypeError) as err:
            self.hud.show_message(f"Error al cargar: {err}")
            return
        self.refresh_hotbar()
        self.hud.show_message("Partida cargada")

    # -------------------------------------------------------------------------
    # Game Loop
    # -------------------------------------------------------------------------
    def update_mouse_look(self):
        if not (self.mouse_locked and self.mouseWatcherNode.hasMouse()):
            return
        md = self.win.getPointer(0)
        cx, cy = self.win.getXSize() // 2, self.win.getYSize() // 2
        self.player.h -= (md.getX() - cx) * MOUSE_SENSITIVITY
        self.player.p -= (md.getY() - cy) * MOUSE_SENSITIVITY
        self.player.p = max(-89.0, min(89.0, self.player.p))
        self.win.movePointer(0, cx, cy)

    def update_target(self, eye):
        block, normal = self.world.raycast(eye, self.player.look_direction(), REACH_DISTANCE)
        self.targeted_block, self.targeted_normal = block, normal
        if block:
            self.selection_box.setPos(*block)
            self.selection_box.show()
        else:
            self.selection_box.hide()

    def update(self, task):
        dt = min(globalClock.getDt(), 0.05)  # Evita saltos físicos con tirones

        self.update_mouse_look()
        inp = self.read_input()
        self.player.update(dt, inp)
        self.tnt.update(dt)
        self.world.rebuild_dirty()  # Solo re-malla los chunks modificados este cuadro
        self.daynight.update(dt * (FAST_TIME_MULT if inp["fast_time"] else 1.0))

        # Transiciones suaves de altura de ojos (agacharse) y FOV (sprint)
        blend = min(1.0, dt * 12.0)
        self.eye_height += (self.player.eye_height - self.eye_height) * blend
        target_fov = SPRINT_FOV if self.player.sprinting else BASE_FOV
        self.fov += (target_fov - self.fov) * min(1.0, dt * 8.0)
        self.camLens.setFov(self.fov)

        px, py, pz = self.player.pos
        eye = (px, py, pz + self.eye_height)

        # Temblor de cámara por explosiones
        sx = sy = sz = 0.0
        if self.shake > 0:
            sx, sy, sz = (random.uniform(-1, 1) * self.shake * 0.3 for _ in range(3))
            self.shake = max(0.0, self.shake - dt * 1.5)

        self.camera.setPos(eye[0] + sx, eye[1] + sy, eye[2] + sz)
        self.camera.setHpr(self.player.h, self.player.p, 0)
        self.update_target(eye)

        # HUD (el texto de estado se refresca 5 veces por segundo)
        self.hud.update(dt)
        self.status_timer -= dt
        if self.status_timer <= 0:
            self.status_timer = 0.2
            if self.player.fly:
                mode = "Vuelo (creativo)"
            elif self.player.crouching:
                mode = "Supervivencia - agachado"
            elif self.player.sprinting:
                mode = "Supervivencia - corriendo"
            else:
                mode = "Supervivencia"
            self.hud.set_status(
                f"Modo: {mode} | Hora: {self.daynight.clock_string()} | "
                f"Bloques: {self.world.block_count()} | Pos: ({px:.1f}, {py:.1f}, {pz:.1f}) | "
                f"FPS: {globalClock.getAverageFrameRate():.0f}"
            )
        return task.cont


if __name__ == "__main__":
    app = MinecraftApp()
    app.run()
