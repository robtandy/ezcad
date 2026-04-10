"""World — exact CAD kernel + domain objects, owned exclusively by the RPC thread."""

import math
import uuid
import rpyc

import numpy as np
from shapely.geometry import Polygon

from build123d import (
    Box,
    Sphere,
    Cylinder,
    Cone,
    Torus,
    Plane,
    Location,
    Axis,
    Shape,
    section as b123_section,
)
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_UniformAbscissa

from .messages import Viewable

# ─── Visual defaults ─────────────────────────────────────────────────────────

DEFAULT_ALPHA_MODE = "auto"


def _resolve_alpha(global_alpha: str, override: str | None) -> str:
    """Return the effective alpha mode: override if set, else global."""
    return override if override is not None else global_alpha


def _tessellate_solid(shape):
    """Tessellate a build123d Shape into positions/faces/normals arrays.

    build123d's .tessellate(deflection) returns (vertices, faces).
    Each face is a tuple of 3 indices into the vertex list.
    Also computes flat face normals from the triangle winding.
    """
    verts, faces = shape.tessellate(0.01)
    if not verts:
        return [], [], []
    positions = np.array([[v.X, v.Y, v.Z] for v in verts], dtype=np.float32)
    indices = np.array(faces, dtype=np.uint32)

    # Compute flat normals: one 3D normal per face, repeated 3 times
    face_normals = np.zeros((len(faces) * 3, 3), dtype=np.float32)
    for i, (a, b, c) in enumerate(faces):
        v0, v1, v2 = positions[a], positions[b], positions[c]
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)
        if norm > 1e-12:
            normal /= norm
        face_normals[i * 3] = face_normals[i * 3 + 1] = face_normals[i * 3 + 2] = normal

    return positions, indices, face_normals


class Solid:
    """Exact solid backed by build123d Shape."""

    def __init__(self, uid: str, shape: Shape):
        self.uid = uid
        self._shape = shape
        self.visible = True
        self.color = 0.13, 0.26, 0.52, 0.5
        self.visual_alpha_mode: str | None = None  # None ⇒ inherit global

    @property
    @rpyc.exposed
    def position(self) -> tuple[int | float, int | float, int | float]:
        return self._shape.position.to_tuple()

    @property
    def mesh(self):
        """Lazily tessellate to (positions, indices, face_normals) for pygfx."""
        return _tessellate_solid(self._shape)

    @rpyc.exposed
    def translate(self, vec):
        loc = Location(tuple(vec))
        self._shape = self._shape.move(loc)
        self.pos = [self.pos[i] + vec[i] for i in range(3)]

    @rpyc.exposed
    def rotate(self, axis, degrees=0, radians=0):
        rad = radians if radians != 0 else math.radians(degrees)
        deg = math.degrees(rad)
        axes = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
        if isinstance(axis, str):
            axis = axes[axis]
        ax = Axis(origin=(0, 0, 0), direction=(*axis,))
        self._shape = self._shape.rotate(ax, deg)

    @rpyc.exposed
    def scale(self, factor):
        from build123d import scale as b123d_scale

        self._shape = b123d_scale(self._shape, by=factor)

    @rpyc.exposed
    def mirror(self, plane="xy"):
        plane_map = {
            "xy": Plane((0, 0, 0), z_dir=(0, 0, 1)),
            "yz": Plane((0, 0, 0), z_dir=(1, 0, 0)),
            "xz": Plane((0, 0, 0), z_dir=(0, 1, 0)),
        }
        self._shape = self._shape.mirror(plane_map[plane])

    @rpyc.exposed
    def union(self, other_uid, world):
        other = world.solids[other_uid]
        self._shape = self._shape.fuse(other._shape)

    @rpyc.exposed
    def difference(self, other_uid, world):
        other = world.solids[other_uid]
        self._shape = self._shape.cut(other._shape)

    @rpyc.exposed
    def intersection(self, other_uid, world):
        other = world.solids[other_uid]
        self._shape = self._shape.intersect(other._shape)

    @property
    @rpyc.exposed
    def volume(self):
        return self._shape.volume

    @property
    @rpyc.exposed
    def area(self):
        return self._shape.area

    @property
    @rpyc.exposed
    def bounds(self):
        bb = self._shape.bounding_box()
        return [[bb.min.X, bb.min.Y, bb.min.Z], [bb.max.X, bb.max.Y, bb.max.Z]]

    @rpyc.exposed
    def section(self, plane="z", value=0.0):
        normal = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[plane]
        origin_pt = {"x": [value, 0, 0], "y": [0, value, 0], "z": [0, 0, value]}[plane]
        cut = b123_section(self._shape, Plane((*origin_pt,), z_dir=(*normal,)))
        if cut is None or list(cut.edges()) == []:
            return None
        coords = []
        for edge in cut.edges():
            curve = BRepAdaptor_Curve(edge.wrapped)
            pts = GCPnts_UniformAbscissa(curve, 16)
            for i in range(1, pts.NbPoints() + 1):
                v = curve.Value(pts.Parameter(i))
                coords.append((v.X(), v.Y()))
        if not coords:
            return None
        return coords

    def to_viewable(self) -> Viewable:
        positions, indices, normals = _tessellate_solid(self._shape)
        return Viewable(
            uid=self.uid,
            positions=positions,
            indices=indices,
            normals=normals,
            pos=self.pos,
            visible=self.visible,
            color=self.color,
            visible_alpha_mode=self.visible.alpha_mode,
        )


class ProfileImpl:
    """Full 2D profile backed by vertex list."""

    def __init__(self, uid: str, verts):
        self.uid = uid
        self._verts = verts  # Nx2 numpy array

    @property
    def area(self):
        return float(Polygon(self._verts).area)

    @property
    def bounds(self):
        return tuple(float(x) for x in Polygon(self._verts).bounds)

    def as_list(self):
        return self._verts.tolist()


@rpyc.service
class World(rpyc.Service):
    """Container for all domain objects.  Only accessed from RPC thread."""

    def __init__(self, rworld):  # note what is the type of rworld?
        self.solids: dict[str, Solid] = {}
        self.profiles: dict[str, ProfileImpl] = {}
        self.visual_alpha_mode: str = DEFAULT_ALPHA_MODE
        self.rworld = rworld

    def add_solid(self, shape: Shape):
        uid = _uid()
        solid = Solid(uid, shape)
        self.solids[uid] = solid
        self.rworld.add(solid.to_viewable())
        return solid

    @rpyc.exposed
    def box(self, extents):
        return self.add_solid(Box(*extents))

    @rpyc.exposed
    def sphere(self, radius=1.0):
        return self.add_solid(Sphere(radius))

    @rpyc.exposed
    def cylinder(self, radius=1.0, height=1.0):
        return self.add_solid(Cylinder(radius, height))

    @rpyc.exposed
    def cone(self, radius=1.0, height=1.0):
        return self.add_solid(Cone(radius, 0, height))

    @rpyc.exposed
    def torus(self, major_radius=1.0, minor_radius=0.25):
        return self.add_solid(Torus(major_radius, minor_radius))

    @rpyc.exposed
    def delete(self, uid):
        self.solids.pop(uid, None)


def _uid():
    return str(uuid.uuid4())[:8]
