"""
Interfaz en pantalla: punto de mira, controles, hotbar con conteo, estado y mensajes.
(Se evitan tildes porque la fuente por defecto de Panda3D no siempre las incluye.)
"""

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

from config import BLOCK_TYPES

CONTROLS_TEXT = (
    "WASD: Moverse | Espacio: Saltar | Shift: Agacharse/Bajar | Ctrl: Correr\n"
    "Clic Izq: Romper | Clic Der: Colocar | E: Encender TNT | 1-8 o Rueda: Bloque\n"
    "F: Vuelo (creativo) | T: Acelerar tiempo | F5: Guardar | F9: Cargar | R: Mundo nuevo | ESC: Raton"
)


class HUD:
    def __init__(self, base):
        shadow = (0, 0, 0, 0.6)
        self.crosshair = OnscreenText(
            text="+", pos=(0, -0.02), scale=0.08, fg=(1, 1, 1, 0.85),
            align=TextNode.ACenter, mayChange=False,
        )
        self.controls = OnscreenText(
            text=CONTROLS_TEXT, parent=base.a2dTopLeft, pos=(0.05, -0.08), scale=0.042,
            fg=(1, 1, 1, 0.95), shadow=shadow, align=TextNode.ALeft, mayChange=False,
        )
        self.hotbar = OnscreenText(
            text="", parent=base.a2dBottomCenter, pos=(0, 0.14), scale=0.046,
            fg=(1, 1, 0.3, 1), shadow=shadow, align=TextNode.ACenter, mayChange=True,
        )
        self.status = OnscreenText(
            text="", parent=base.a2dBottomLeft, pos=(0.05, 0.05), scale=0.042,
            fg=(0.9, 0.9, 0.9, 0.95), shadow=shadow, align=TextNode.ALeft, mayChange=True,
        )
        self.message = OnscreenText(
            text="", pos=(0, 0.3), scale=0.07, fg=(1, 0.85, 0.3, 1), shadow=shadow,
            align=TextNode.ACenter, mayChange=True,
        )
        self.message_timer = 0.0

    def show_message(self, text, seconds=2.5):
        self.message.setText(text)
        self.message_timer = seconds

    def set_hotbar(self, current_block, inventory, creative):
        items = []
        for block_id, data in BLOCK_TYPES.items():
            amount = "--" if creative else str(inventory.count(block_id))
            label = f"{block_id} {data['name']} x{amount}"
            items.append(f"[{label}]" if block_id == current_block else label)
        self.hotbar.setText("   ".join(items))

    def set_status(self, text):
        self.status.setText(text)

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message.setText("")
