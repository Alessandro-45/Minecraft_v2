"""
Generador de mallas voxel.

En lugar de crear un nodo por bloque (muy lento con miles de bloques), cada chunk
se convierte en UNA sola malla que solo contiene las caras visibles: si una cara
toca otro bloque sólido, no se dibuja.

Convención: el bloque (x, y, z) ocupa el cubo [x, x+1] x [y, y+1] x [z, z+1].
"""

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
)

from config import BLOCK_TYPES

# Cara: nombre, normal, 4 esquinas en orden antihorario visto desde fuera
FACE_DEFS = (
    ("top", (0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ("bottom", (0, 0, -1), ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0))),
    ("front", (0, 1, 0), ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1))),
    ("back", (0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ("right", (1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ("left", (-1, 0, 0), ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1))),
)


def _tint(x, y, z):
    """Pequeña variación de brillo por bloque para que el terreno no se vea plano."""
    h = (x * 73856093 ^ y * 19349663 ^ z * 83492791) & 0xFFFF
    return 0.94 + (h / 0xFFFF) * 0.08


def build_block_mesh(name, blocks, occludes):
    """
    Construye un GeomNode con las caras visibles de `blocks` ({(x, y, z): block_id}).
    `occludes(x, y, z)` indica si hay un bloque que tapa la cara vecina.
    Devuelve None si no hay nada que dibujar.
    """
    vdata = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    vertex_writer = GeomVertexWriter(vdata, "vertex")
    normal_writer = GeomVertexWriter(vdata, "normal")
    color_writer = GeomVertexWriter(vdata, "color")
    triangles = GeomTriangles(Geom.UHStatic)
    idx = 0

    for (x, y, z), block_id in blocks.items():
        colors = BLOCK_TYPES[block_id]["colors"]
        tint = _tint(x, y, z)
        for face_id, (nx, ny, nz), corners in FACE_DEFS:
            if occludes(x + nx, y + ny, z + nz):
                continue
            r, g, b = colors[face_id]
            for cx, cy, cz in corners:
                vertex_writer.addData3(x + cx, y + cy, z + cz)
                normal_writer.addData3(nx, ny, nz)
                color_writer.addData4(r * tint, g * tint, b * tint, 1.0)
            triangles.addVertices(idx, idx + 1, idx + 2)
            triangles.addVertices(idx, idx + 2, idx + 3)
            idx += 4

    if idx == 0:
        return None

    geom = Geom(vdata)
    geom.addPrimitive(triangles)
    node = GeomNode(name)
    node.addGeom(geom)
    return node
