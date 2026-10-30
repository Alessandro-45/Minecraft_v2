"""
Inventario con conteo: lo que rompes se suma, lo que colocas se resta.
En modo vuelo (creativo) la app no consume bloques.
"""

from config import BLOCK_TYPES


class Inventory:
    def __init__(self, initial=None):
        self.reset(initial)

    def reset(self, initial=None):
        self.counts = {block_id: 0 for block_id in BLOCK_TYPES}
        for block_id, amount in (initial or {}).items():
            self.counts[block_id] = amount

    def count(self, block_id):
        return self.counts.get(block_id, 0)

    def add(self, block_id, amount=1):
        if block_id in self.counts:
            self.counts[block_id] += amount

    def take(self, block_id):
        if self.counts.get(block_id, 0) <= 0:
            return False
        self.counts[block_id] -= 1
        return True

    def serialize(self):
        return {str(k): v for k, v in self.counts.items()}

    def deserialize(self, data):
        self.reset({int(k): v for k, v in data.items()})
