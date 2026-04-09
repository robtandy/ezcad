"""World — domain objects, owned exclusively by the RPC thread."""

import math
import uuid

import numpy as np
import trimesh
from shapely.geometry import Polygon


class MeshImpl:
    """Full 3D mesh backed by trimesh.Trimesh."""

    def __init__(self, uid: str, mesh: trimesh.Trimesh):
        self.uid = uid
        self._mesh = mesh
        self.pos = [0.0, 0.0, 0.0]
        self.visible = True
        self.color = "#336699"

    def translate(self, vec):
        tm = trimesh.transformations.translation_matrix(vec)
        self._mesh.apply_transform(tm)
        self.pos = [self.pos[i] + vec[i] for i in range(3)]

    def rotate(self, axis, degrees=0, radians=0):
        rad = radians if radians != 0 else degrees * math.pi / 180.0
        tm = trimesh.transformations.rotation_matrix(rad, _axis_vec(axis))
        self._mesh.apply_transform(tm)

    def scale(self, factor):
        if isinstance(factor, (int, float)):
            factor = [factor, factor, factor]
        sm = np.eye(4)
        for i in range(3):
            sm[i, i] = factor[i]
        self._mesh.apply_transform(sm)

    def mirror(self, plane="xy"):
        axes = {"xy": [0, 0, 1], "yz": [1, 0, 0], "xz": [0, 1, 0]}
        n = axes[plane]
        verts = self._mesh.vertices.copy()
        for i, c in enumerate(n):
            if c:
                verts[:, i] = -verts[:, i]
        self._mesh.vertices = verts

    def union(self, other_uid, world):
        self._mesh = self._mesh.union(world.meshes[other_uid]._mesh)

    def difference(self, other_uid, world):
        self._mesh = self._mesh.difference(world.meshes[other_uid]._mesh)

    def intersection(self, other_uid, world):
        self._mesh = self._mesh.intersection(world.meshes[other_uid]._mesh)

    @property
    def volume(self):
        return self._mesh.volume

    @property
    def area(self):
        return self._mesh.area

    def bounds(self):
        return self._mesh.bounds.tolist()

    def section_vertices(self, plane="z", value=0.0):
        normal = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[plane]
        origin_map = {"x": [value, 0, 0], "y": [0, value, 0], "z": [0, 0, value]}
        section = self._mesh.section(
            plane_origin=origin_map[plane], plane_normal=normal)
        if section is None or section.is_empty:
            return None
        polygons = []
        for entity in section.entities:
            pts = section.vertices[entity.points][:, :2]
            if len(pts) >= 3:
                poly = Polygon(pts)
                if poly.area > 0:
                    polygons.append(poly)
        if not polygons:
            return None
        merged = polygons[0]
        for p in polygons[1:]:
            merged = merged.union(p)
        return list(merged.exterior.coords)

    def stl_bytes(self):
        return self._mesh.export(file_type="stl")


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


class World:
    """Container for all domain objects.  Only accessed from RPC thread."""

    def __init__(self):
        self.meshes: dict[str, MeshImpl] = {}
        self.profiles: dict[str, ProfileImpl] = {}

    def make_box(self, extents):
        uid = _uid()
        self.meshes[uid] = MeshImpl(uid, trimesh.creation.box(extents=extents))
        return uid

    def make_sphere(self, radius=1.0):
        uid = _uid()
        self.meshes[uid] = MeshImpl(uid, trimesh.creation.uv_sphere(radius=radius))
        return uid

    def make_cylinder(self, radius=1.0, height=1.0):
        uid = _uid()
        self.meshes[uid] = MeshImpl(
            uid, trimesh.creation.cylinder(radius=radius, height=height))
        return uid

    def make_cone(self, radius=1.0, height=1.0):
        uid = _uid()
        self.meshes[uid] = MeshImpl(
            uid, trimesh.creation.cone(radius=radius, height=height))
        return uid

    def make_torus(self, major_radius=1.0, minor_radius=0.25):
        uid = _uid()
        self.meshes[uid] = MeshImpl(
            uid, trimesh.creation.torus(
                major_radius=major_radius, minor_radius=minor_radius))
        return uid

    def delete_mesh(self, uid):
        self.meshes.pop(uid, None)

    def make_circle(self, radius=1.0, segments=64):
        uid = _uid()
        theta = np.linspace(0, 2 * math.pi, segments, endpoint=False)
        verts = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
        self.profiles[uid] = ProfileImpl(uid, verts)
        return uid

    def make_rect(self, width=1.0, height=1.0):
        uid = _uid()
        hw, hh = width / 2, height / 2
        verts = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
        self.profiles[uid] = ProfileImpl(uid, verts)
        return uid

    def make_ngon(self, radius=1.0, sides=6):
        uid = _uid()
        theta = np.linspace(0, 2 * math.pi, sides, endpoint=False)
        verts = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
        self.profiles[uid] = ProfileImpl(uid, verts)
        return uid

    def mesh_get(self, uid, attr):
        return getattr(self.meshes[uid], attr)

    def mesh_set(self, uid, attr, value):
        setattr(self.meshes[uid], attr, value)

    def mesh_call(self, uid, method, args=(), kwargs=None):
        m = self.meshes[uid]
        fn = getattr(m, method)
        if method in ("union", "difference", "intersection"):
            return fn(args[0], self)
        return fn(*args, **(kwargs or {}))

    def profile_get(self, uid, attr):
        return getattr(self.profiles[uid], attr)


def _uid():
    return str(uuid.uuid4())[:8]


def _axis_vec(axis):
    if isinstance(axis, str):
        return {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    return list(axis)
