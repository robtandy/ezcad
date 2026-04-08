import math
import uuid
from contextlib import contextmanager
from typing import Self
import numpy as np
import trimesh

from ..commands import AddCmd, SyncCmd, VisibilityCmd


class Mesh:
    """A 3D solid backed by trimesh, displayed via a :class:`~ezcad.View`.

    Every mutating method auto-updates the viewer **eagerly**.
    Wrap many operations in ``with mesh.frozen():`` to batch them.
    """

    def __init__(self, mesh: trimesh.Trimesh):
        self._mesh = mesh
        self.uuid = str(uuid.uuid4())
        self.pos = [0.0, 0.0, 0.0]
        self.visible = True
        self.color = "#336699"
        self._view = None
        self._frozen = False
        self._batched = []

    # -- view plumbing -------------------------------------------------------

    def _notify(self, cmd):
        """Send a command to the viewer, or batch it if frozen."""
        if self._frozen:
            self._batched.append(cmd)
        elif self._view is not None:
            self._view.queue.put(cmd)

    def show_in(self, view):
        """Register this mesh with a viewer and render it."""
        self._view = view
        self._view.queue.put(AddCmd(self))
        return self

    def hide(self):
        """Remove from the scene."""
        self.visible = False
        self._notify(VisibilityCmd(self.uuid, False))
        return self

    def unhide(self):
        """Add back to the scene."""
        self.visible = True
        self._notify(VisibilityCmd(self.uuid, True))
        return self

    @contextmanager
    def frozen(self):
        """Batch updates until the context exits.

        Use for loops or programmatic generation to avoid flooding the queue::

            with mesh.frozen():
                for i in range(100):
                    mesh.rotate("z", 3.6)
        """
        self._frozen = True
        try:
            yield
        finally:
            self._frozen = False
            if self._view is not None:
                for cmd in self._batched:
                    self._view.queue.put(cmd)
            self._batched.clear()

    # -- CSG -----------------------------------------------------------------

    def union(self, other: Self) -> Self:
        """Boolean union of this shape with *other*."""
        self._mesh = self._mesh.union(other._mesh)
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    def difference(self, other: Self) -> Self:
        """Subtract *other* from this shape."""
        self._mesh = self._mesh.difference(other._mesh)
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    def intersection(self, other: Self) -> Self:
        """Boolean intersection with *other*."""
        self._mesh = self._mesh.intersection(other._mesh)
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    # -- transforms ----------------------------------------------------------

    def translate(self, direction: list[float]) -> Self:
        """Translate by a 3-vector."""
        tm = trimesh.transformations.translation_matrix(direction)
        self._mesh.apply_transform(tm)
        self.pos = [
            self.pos[0] + direction[0],
            self.pos[1] + direction[1],
            self.pos[2] + direction[2],
        ]
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    def rotate(self, axis: str, degrees: float = 0, radians: float = 0) -> Self:
        """Rotate about ``axis`` ('x', 'y', 'z', or a 3-vector)."""
        rad = radians if radians != 0 else degrees * math.pi / 180.0
        axis_vec = _axis_vec(axis)
        tm = trimesh.transformations.rotation_matrix(rad, axis_vec)
        self._mesh.apply_transform(tm)
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    def scale(self, factor: float | list[float]) -> Self:
        """Uniform or per-axis scale."""
        if isinstance(factor, (int, float)):
            factor = [factor, factor, factor]
        sm = np.eye(4)
        sm[0, 0] = factor[0]
        sm[1, 1] = factor[1]
        sm[2, 2] = factor[2]
        self._mesh.apply_transform(sm)
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    def mirror(self, plane: str = "xy") -> Self:
        """Reflect across a plane ('xy', 'yz', 'xz')."""
        axes = {"xy": [0, 0, 1], "yz": [1, 0, 0], "xz": [0, 1, 0]}
        normal = axes[plane]
        tm = np.eye(4)
        tm[3, 3] = 1
        for i in range(3):
            tm[i, i] = -1 if normal[i] else 1
        # Simpler: just negate the normal component of every vertex
        verts = self._mesh.vertices.copy()
        for i, n in enumerate(normal):
            if n:
                verts[:, i] = -verts[:, i]
        self._mesh.vertices = verts
        self._notify(SyncCmd(self.uuid, self._mesh, self.pos, self.color))
        return self

    # -- 3d → 2d -------------------------------------------------------------

    def section(self, plane: str = "z", value: float = 0.0) -> "Profile":
        """Slice this shape at *value* along *plane* ('x', 'y', 'z').

        Returns a :class:`~ezcad.d2.Profile` of the cross-section.
        Not auto-registered with the viewer.
        """
        from ezcad.d2 import Profile

        axes = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
        origin_map = {
            "x": [value, 0, 0],
            "y": [0, value, 0],
            "z": [0, 0, value],
        }
        normal = axes[plane]
        origin = origin_map[plane]
        section = self._mesh.section(plane_origin=origin, plane_normal=normal)
        if section is None or section.is_empty:
            return Profile([])

        # Extract polygon entities from the Path3D section
        from shapely.geometry import Polygon
        polygons = []
        for entity in section.entities:
            pts = section.vertices[entity.points][:, :2]  # drop Z
            if len(pts) >= 3:
                poly = Polygon(pts)
                if poly.area > 0:
                    polygons.append(poly)

        if not polygons:
            return Profile([])

        # Merge all polygons (in case of multiple shells)
        merged = polygons[0]
        for p in polygons[1:]:
            merged = merged.union(p)

        verts = list(merged.exterior.coords)
        return Profile(verts)

    # -- properties ----------------------------------------------------------

    @property
    def volume(self) -> float:
        return self._mesh.volume

    @property
    def area(self) -> float:
        return self._mesh.area

    def mass(self, density: float = 1.0) -> float:
        return self._mesh.volume * density

    def bounds(self) -> list[list[float]]:
        return self._mesh.bounds.tolist()


# -- helpers ---------------------------------------------------------------------

def _axis_vec(axis: str | list[float]) -> list[float]:
    if isinstance(axis, str):
        return {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    return axis


# -- primitive constructors ------------------------------------------------------

def box(extents: list[float]) -> Mesh:
    return Mesh(trimesh.creation.box(extents=extents))


def sphere(radius: float = 1.0) -> Mesh:
    return Mesh(trimesh.creation.uv_sphere(radius=radius))


def cylinder(radius: float = 1.0, height: float = 1.0) -> Mesh:
    return Mesh(trimesh.creation.cylinder(radius=radius, height=height))


def cone(radius: float = 1.0, height: float = 1.0) -> Mesh:
    return Mesh(trimesh.creation.cone(radius=radius, height=height))


def torus(major_radius: float = 1.0, minor_radius: float = 0.25) -> Mesh:
    return Mesh(trimesh.creation.torus(
        major_radius=major_radius, minor_radius=minor_radius
    ))



