"""
Ciclo día/noche: el sol y la luna giran alrededor del mundo, cambian la luz,
el color del cielo y la niebla, y de noche aparecen las estrellas.
"""

import math
import random

from panda3d.core import (
    AmbientLight,
    CardMaker,
    DirectionalLight,
    Fog,
    Geom,
    GeomNode,
    GeomPoints,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    Point3,
    TransparencyAttrib,
    Vec3,
    Vec4,
)

from config import DAY_LENGTH, START_TIME

DAY_SKY = (0.53, 0.81, 0.98)
NIGHT_SKY = (0.02, 0.03, 0.08)
SUNSET_SKY = (0.98, 0.55, 0.30)
DAY_AMBIENT = (0.40, 0.40, 0.43)
NIGHT_AMBIENT = (0.07, 0.07, 0.13)
SKY_RADIUS = 70.0


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


class DayNightCycle:
    def __init__(self, base):
        self.base = base
        self.time = START_TIME  # 0..1 (fracción del día)
        render = base.render

        self.sun = DirectionalLight("sol")
        self.sun_np = render.attachNewNode(self.sun)
        render.setLight(self.sun_np)

        self.moon = DirectionalLight("luna")
        self.moon_np = render.attachNewNode(self.moon)
        render.setLight(self.moon_np)

        self.ambient = AmbientLight("ambiente")
        render.setLight(render.attachNewNode(self.ambient))

        self.fog = Fog("niebla")
        self.fog.setExpDensity(0.018)
        render.setFog(self.fog)

        self._build_sky()
        self.update(0.0)

    # -------------------------------------------------------------------------
    # Cielo: estrellas, sol y luna (siguen a la cámara pero no rotan con ella)
    # -------------------------------------------------------------------------
    def _build_sky(self):
        self.sky = self.base.camera.attachNewNode("cielo")
        self.sky.setCompass()
        self.sky.setBin("background", 0)
        self.sky.setDepthWrite(False)
        self.sky.setDepthTest(False)
        self.sky.setLightOff()
        self.sky.setFogOff()

        self.stars = self.sky.attachNewNode(self._make_stars(450))
        self.stars.setTransparency(TransparencyAttrib.MAlpha)
        self.stars.setRenderModeThickness(2)

        self.sun_disc = self._make_disc(5.0, (1.0, 0.95, 0.6, 1.0))
        self.moon_disc = self._make_disc(3.5, (0.88, 0.90, 1.0, 1.0))

    def _make_stars(self, count):
        rng = random.Random(7)
        vdata = GeomVertexData("estrellas", GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex_writer = GeomVertexWriter(vdata, "vertex")
        color_writer = GeomVertexWriter(vdata, "color")
        points = GeomPoints(Geom.UHStatic)

        for i in range(count):
            # Punto aleatorio sobre la esfera, sobre todo en la mitad superior
            z = rng.uniform(-0.15, 1.0)
            angle = rng.uniform(0, 2 * math.pi)
            ring = math.sqrt(1 - z * z)
            vertex_writer.addData3(ring * math.cos(angle) * SKY_RADIUS, ring * math.sin(angle) * SKY_RADIUS, z * SKY_RADIUS)
            brightness = rng.uniform(0.6, 1.0)
            color_writer.addData4(brightness, brightness, brightness, 1.0)
            points.addVertex(i)

        geom = Geom(vdata)
        geom.addPrimitive(points)
        node = GeomNode("estrellas")
        node.addGeom(geom)
        return node

    def _make_disc(self, size, color):
        cm = CardMaker("disco")
        cm.setFrame(-size, size, -size, size)
        disc = self.sky.attachNewNode(cm.generate())
        disc.setColor(*color)
        disc.setBillboardPointEye()
        return disc

    # -------------------------------------------------------------------------
    # Actualización
    # -------------------------------------------------------------------------
    def clock_string(self):
        minutes = int(self.time * 24 * 60) % (24 * 60)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def update(self, dt):
        self.time = (self.time + dt / DAY_LENGTH) % 1.0

        angle = (self.time - 0.25) * 2 * math.pi  # 0 = amanecer por el este
        sun_dir = Vec3(math.cos(angle), 0.25, math.sin(angle))
        sun_dir.normalize()
        elevation = sun_dir.z

        day = _smoothstep(-0.12, 0.25, elevation)
        dusk = max(0.0, 1.0 - abs(elevation) / 0.25)  # Cerca del horizonte

        sky = _lerp(NIGHT_SKY, DAY_SKY, day)
        sky = _lerp(sky, SUNSET_SKY, dusk * 0.55)
        self.base.setBackgroundColor(*sky)
        self.fog.setColor(*sky)

        sun_strength = _smoothstep(-0.05, 0.3, elevation)
        self.sun.setColor(Vec4(0.95 * sun_strength,
                               (0.90 - 0.25 * dusk) * sun_strength,
                               (0.80 - 0.40 * dusk) * sun_strength, 1.0))
        self.sun_np.lookAt(Point3(-sun_dir))   # La luz viaja del sol hacia el mundo

        moon_strength = _smoothstep(-0.05, 0.3, -elevation)
        self.moon.setColor(Vec4(0.10 * moon_strength, 0.12 * moon_strength, 0.22 * moon_strength, 1.0))
        self.moon_np.lookAt(Point3(sun_dir))   # La luna está en el lado opuesto

        self.ambient.setColor(Vec4(*_lerp(NIGHT_AMBIENT, DAY_AMBIENT, day), 1.0))

        self.stars.setAlphaScale(1.0 - day)
        self.sun_disc.setPos(sun_dir * SKY_RADIUS)
        self.moon_disc.setPos(-sun_dir * SKY_RADIUS)
