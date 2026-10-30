"""
Física del jugador: caja de colisión (AABB) contra la rejilla de bloques,
gravedad, salto, sprint, agacharse (sin caerse de los bordes) y modo vuelo.

`pos` es el centro de los pies del jugador.
"""

import math

from config import (
    CROUCH_EYE_HEIGHT,
    CROUCH_HEIGHT,
    CROUCH_SPEED,
    EYE_HEIGHT,
    FLY_SPEED,
    FLY_SPRINT_MULT,
    GRAVITY,
    JUMP_FORCE,
    PLAYER_HEIGHT,
    PLAYER_RADIUS,
    SPRINT_SPEED,
    WALK_SPEED,
    WORLD_HEIGHT,
)

EPS = 1e-3


class Player:
    def __init__(self, world):
        self.world = world
        self.pos = [0.0, 0.0, 0.0]
        self.vel = [0.0, 0.0, 0.0]  # x/y: empuje de explosiones, z: velocidad vertical
        self.h = 0.0                # Heading (giro horizontal)
        self.p = -10.0              # Pitch (mirar arriba/abajo)
        self.grounded = False
        self.fly = False
        self.crouching = False
        self.sprinting = False

    @property
    def height(self):
        return CROUCH_HEIGHT if self.crouching else PLAYER_HEIGHT

    @property
    def eye_height(self):
        return CROUCH_EYE_HEIGHT if self.crouching else EYE_HEIGHT

    def spawn(self, x, y):
        z = WORLD_HEIGHT
        while z > 0 and not self.world.is_solid(x, y, z - 1):
            z -= 1
        self.pos = [x + 0.5, y + 0.5, float(z)]
        self.vel = [0.0, 0.0, 0.0]

    def look_direction(self):
        h, p = math.radians(self.h), math.radians(self.p)
        return (-math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p))

    def knockback(self, vx, vy, vz):
        if self.fly:
            return
        self.vel[0] += vx
        self.vel[1] += vy
        self.vel[2] = max(self.vel[2], 0.0) + vz
        self.grounded = False

    # -------------------------------------------------------------------------
    # Colisiones
    # -------------------------------------------------------------------------
    def _collides(self, x, y, z, height):
        r = PLAYER_RADIUS
        for bx in range(math.floor(x - r), math.floor(x + r) + 1):
            for by in range(math.floor(y - r), math.floor(y + r) + 1):
                for bz in range(math.floor(z), math.floor(z + height - 1e-6) + 1):
                    if self.world.is_solid(bx, by, bz):
                        return True
        return False

    def intersects_block(self, bx, by, bz):
        x, y, z = self.pos
        r = PLAYER_RADIUS
        return (x - r < bx + 1 and x + r > bx and
                y - r < by + 1 and y + r > by and
                z < bz + 1 and z + self.height > bz)

    def _has_ground(self, x, y):
        return self._collides(x, y, self.pos[2] - 0.1, 0.1)

    def _move_axis(self, axis, delta):
        """Mueve en un eje; si choca, se pega al borde del bloque. Devuelve True si chocó."""
        if delta == 0:
            return False
        new = list(self.pos)
        new[axis] += delta
        height = self.height
        if not self._collides(new[0], new[1], new[2], height):
            self.pos[axis] = new[axis]
            return False

        r = PLAYER_RADIUS
        if axis < 2:
            if delta > 0:
                self.pos[axis] = math.floor(new[axis] + r) - r - EPS
            else:
                self.pos[axis] = math.floor(new[axis] - r) + 1 + r + EPS
        else:
            if delta > 0:
                self.pos[2] = math.floor(new[2] + height) - height - EPS
            else:
                self.pos[2] = math.floor(new[2]) + 1.0
        return True

    # -------------------------------------------------------------------------
    # Actualización por cuadro
    # -------------------------------------------------------------------------
    def update(self, dt, inp):
        forward = inp["forward"] - inp["backward"]
        strafe = inp["right"] - inp["left"]
        h = math.radians(self.h)
        mx = -math.sin(h) * forward + math.cos(h) * strafe
        my = math.cos(h) * forward + math.sin(h) * strafe
        length = math.hypot(mx, my)
        if length > 0:
            mx, my = mx / length, my / length

        if self.fly:
            self._update_fly(dt, inp, mx, my, length > 0)
        else:
            self._update_walk(dt, inp, mx, my, forward)

        # Red de seguridad para no caer al vacío
        if self.pos[2] < -20.0:
            self.spawn(int(self.pos[0]), int(self.pos[1]))

    def _update_fly(self, dt, inp, mx, my, moving):
        self.crouching = False
        self.sprinting = inp["sprint"] and moving
        speed = FLY_SPEED * (FLY_SPRINT_MULT if self.sprinting else 1.0)
        vz = (inp["jump"] - inp["crouch"]) * FLY_SPEED
        self._move_axis(0, mx * speed * dt)
        self._move_axis(1, my * speed * dt)
        self._move_axis(2, vz * dt)
        self.vel = [0.0, 0.0, 0.0]

    def _update_walk(self, dt, inp, mx, my, forward):
        # Agacharse: solo se puede levantar si hay espacio encima
        if inp["crouch"]:
            self.crouching = True
        elif self.crouching and not self._collides(*self.pos, PLAYER_HEIGHT):
            self.crouching = False

        self.sprinting = inp["sprint"] and forward > 0 and not self.crouching
        if self.crouching:
            speed = CROUCH_SPEED
        elif self.sprinting:
            speed = SPRINT_SPEED
        else:
            speed = WALK_SPEED

        # El empuje de explosiones se frena poco a poco
        damping = max(0.0, 1.0 - (6.0 if self.grounded else 1.5) * dt)
        self.vel[0] *= damping
        self.vel[1] *= damping

        dx = (mx * speed + self.vel[0]) * dt
        dy = (my * speed + self.vel[1]) * dt

        # Agachado sobre el suelo: no te deja caer por los bordes
        edge_guard = self.crouching and self.grounded
        if not (edge_guard and not self._has_ground(self.pos[0] + dx, self.pos[1])):
            if self._move_axis(0, dx):
                self.vel[0] = 0.0
        if not (edge_guard and not self._has_ground(self.pos[0], self.pos[1] + dy)):
            if self._move_axis(1, dy):
                self.vel[1] = 0.0

        # Gravedad y suelo
        self.vel[2] -= GRAVITY * dt
        if self._move_axis(2, self.vel[2] * dt):
            self.grounded = self.vel[2] < 0
            self.vel[2] = 0.0
        else:
            self.grounded = False

        if inp["jump"] and self.grounded:
            self.vel[2] = JUMP_FORCE
            self.grounded = False

    # -------------------------------------------------------------------------
    # Guardado
    # -------------------------------------------------------------------------
    def serialize(self):
        return {"pos": self.pos, "h": self.h, "p": self.p, "fly": self.fly}

    def deserialize(self, data):
        self.pos = [float(v) for v in data["pos"]]
        self.h = data.get("h", 0.0)
        self.p = data.get("p", 0.0)
        self.fly = data.get("fly", False)
        self.vel = [0.0, 0.0, 0.0]
        self.crouching = False
