"""ViewBkg server process.

Owns two worlds:
  - **World**: domain objects (ServerMesh, ServerProfile), accessed only by
    the RPC handler thread (exclusive owner, no locking needed).
  - **RenderWorld**: pygfx Scene + gfx.Mesh objects, accessed by the RPC
    handler thread (write lock) and the render loop (read lock).

pygfx's ``Display.show()`` runs the render loop on the main thread.  We
use ``before_render`` / ``after_render`` callbacks to manage the read lock.
"""

import io
import math
import threading
import uuid

import numpy as np
import trimesh
import pygfx as gfx
from shapely.geometry import Polygon

from .rpc import MpRpcServer


# ---------------------------------------------------------------------------
# Reader-writer lock  (single writer, multiple readers)
# ---------------------------------------------------------------------------

class RWLock:
    """Lightweight RW lock.  Multiple readers or one writer."""

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._readers = 0
        self._writer = False

    def acquire_read(self):
        with self._cond:
            while self._writer:
                self._cond.wait()
            self._readers += 1

    def release_read(self):
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self):
        with self._cond:
            while self._writer or self._readers > 0:
                self._cond.wait()
            self._writer = True

    def release_write(self):
        with self._cond:
            self._writer = False
            self._cond.notify_all()


# ---------------------------------------------------------------------------
# ServerMesh  (domain object in World, RPC-thread exclusive)
# ---------------------------------------------------------------------------

class ServerMesh:
    """Backed by ``trimesh.Trimesh``.  Lives exclusively in the RPC handler
    thread."""

    def __init__(self, uid: str, mesh: trimesh.Trimesh):
        self.uid = uid
        self._mesh = mesh
        self.pos = [0.0, 0.0, 0.0]
        self.visible = True
        self.color = "#336699"

    # -- transforms --

    def translate(self, vec):
        tm = trimesh.transformations.translation_matrix(vec)
        self._mesh.apply_transform(tm)
        self.pos = [self.pos[i] + vec[i] for i in range(3)]

    def rotate(self, axis, degrees=0, radians=0):
        rad = radians if radians != 0 else degrees * math.pi / 180.0
        _axis_vec(axis)  # validate
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

    # -- CSG  (other_uid must exist in the caller's World) --

    def union(self, other_uid, world):
        other = world.meshes[other_uid]
        self._mesh = self._mesh.union(other._mesh)

    def difference(self, other_uid, world):
        other = world.meshes[other_uid]
        self._mesh = self._mesh.difference(other._mesh)

    def intersection(self, other_uid, world):
        other = world.meshes[other_uid]
        self._mesh = self._mesh.intersection(other._mesh)

    # -- query --

    @property
    def volume(self):
        return self._mesh.volume

    @property
    def area(self):
        return self._mesh.area

    def mass(self, density=1.0):
        return self._mesh.volume * density

    def bounds(self):
        return self._mesh.bounds.tolist()

    # -- 2D export --

    def section(self, plane="z", value=0.0):
        """Return list of [[x,y], ...] for the cross-section, or None."""
        normal = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[plane]
        origin_map = {
            "x": [value, 0, 0],
            "y": [0, value, 0],
            "z": [0, 0, value],
        }
        section = self._mesh.section(
            plane_origin=origin_map[plane], plane_normal=normal
        )
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

    # -- pick info (sent to client for ray-cast results) --

    def stl_bytes(self):
        return self._mesh.export(file_type="stl")


# ---------------------------------------------------------------------------
# World  (RPC-thread exclusive, no locking)
# ---------------------------------------------------------------------------

class World:
    """Domain objects.  Only the RPC handler thread touches these."""

    def __init__(self):
        self.meshes: dict[str, ServerMesh] = {}

    # -- constructors --

    def make_box(self, extents):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(uid, trimesh.creation.box(extents=extents))
        return uid

    def make_sphere(self, radius=1.0):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(uid, trimesh.creation.uv_sphere(radius=radius))
        return uid

    def make_cylinder(self, radius=1.0, height=1.0):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(
            uid, trimesh.creation.cylinder(radius=radius, height=height)
        )
        return uid

    def make_cone(self, radius=1.0, height=1.0):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(
            uid, trimesh.creation.cone(radius=radius, height=height)
        )
        return uid

    def make_torus(self, major_radius=1.0, minor_radius=0.25):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(
            uid, trimesh.creation.torus(
                major_radius=major_radius, minor_radius=minor_radius
            )
        )
        return uid

    # -- generic RPC dispatch --

    def mesh_get(self, uid, attr):
        m = self.meshes.get(uid)
        if m is None:
            raise KeyError(uid)
        return getattr(m, attr)

    def mesh_set(self, uid, attr, value):
        m = self.meshes.get(uid)
        if m is None:
            raise KeyError(uid)
        setattr(m, attr, value)

    def mesh_call(self, uid, method, args=(), kwargs=None):
        m = self.meshes.get(uid)
        if m is None:
            raise KeyError(uid)
        fn = getattr(m, method)
        # Methods that take another mesh uid need the world reference
        if method in ("union", "difference", "intersection"):
            return fn(args[0], self)
        return fn(*args, **(kwargs or {}))


# ---------------------------------------------------------------------------
# ViewBkg – the server process entry point
# ---------------------------------------------------------------------------

def run_server(address: tuple = ("localhost", 0)):
    """Start ViewBkg: RPC server + pygfx render loop.  Blocks."""
    world = World()
    rw_lock = RWLock()

    # ── pygfx render setup ──────────────────────────────────────────
    scene = gfx.Scene()
    camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
    camera.position = (6, 6, 6)
    camera.look_at((0, 0, 0))
    controller = gfx.OrbitController(camera)

    axes = gfx.AxesHelper(1, thickness=2)
    scene.add(axes)

    # uid → gfx.Mesh  (render world mirror)
    _gfx_map: dict[str, gfx.Mesh] = {}

    def _resize_axes():
        """Called WITH the write lock held."""
        nonlocal axes
        scene.remove(axes)
        bb = scene.get_bounding_box()
        if bb is None:
            return
        size = max(
            1.0,
            abs(bb[1][0] - bb[0][0]) / 2,
            abs(bb[1][1] - bb[0][1]) / 2,
            abs(bb[1][2] - bb[0][2]) / 2,
        )
        axes = gfx.AxesHelper(size, thickness=2)
        scene.add(axes)

    def _sync_mesh_to_render(uid):
        """Add or replace a gfx.Mesh for the given ServerMesh.
        Must be called WITH the write lock held."""
        sm = world.meshes.get(uid)
        if sm is None:
            return
        stl = sm._mesh.export(file_type="stl")
        tmesh = trimesh.load(io.BytesIO(stl), file_type="stl")
        geo = gfx.geometry_from_trimesh(tmesh)
        gmesh = gfx.Mesh(geo, gfx.MeshPhongMaterial(color=sm.color))
        gmesh.position = sm.pos
        gmesh.visible = sm.visible

        old = _gfx_map.get(uid)
        if old is not None:
            scene.remove(old)
        scene.add(gmesh)
        _gfx_map[uid] = gmesh
        _resize_axes()

    def _sync_visibility(uid):
        """Update visibility of a gfx.Mesh in the render world."""
        sm = world.meshes.get(uid)
        gmesh = _gfx_map.get(uid)
        if sm and gmesh:
            gmesh.visible = sm.visible

    # ── render loop hooks ───────────────────────────────────────────

    def _before_render(self):
        rw_lock.acquire_read()

    def _after_render(self):
        rw_lock.release_read()

    display = gfx.Display(before_render=_before_render, after_render=_after_render, stats=True)

    # ── RPC handlers ────────────────────────────────────────────────

    def _make_box(extents):
        uid = world.make_box(extents)
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    def _make_sphere(radius=1.0):
        uid = world.make_sphere(radius)
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    def _make_cylinder(radius=1.0, height=1.0):
        uid = world.make_cylinder(radius, height)
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    def _make_cone(radius=1.0, height=1.0):
        uid = world.make_cone(radius, height)
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    def _make_torus(major_radius=1.0, minor_radius=0.25):
        uid = world.make_torus(major_radius, minor_radius)
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    def _mesh_get(uid, attr):
        return world.mesh_get(uid, attr)

    def _mesh_set(uid, attr, value):
        world.mesh_set(uid, attr, value)
        if attr in ("visible", "color"):
            rw_lock.acquire_write()
            try:
                if attr == "visible":
                    _sync_visibility(uid)
                else:
                    _sync_mesh_to_render(uid)
            finally:
                rw_lock.release_write()

    def _mesh_call(uid, method, args=(), kwargs=None):
        result = world.mesh_call(uid, method, args=args, kwargs=kwargs)
        # Geometry changed → sync render world
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return result

    def _section(uid, plane="z", value=0.0):
        coords = world.meshes[uid].section_vertices(plane, value)
        return coords  # list of [x, y, ...] or None

    # ── start RPC + render ──────────────────────────────────────────
    server = MpRpcServer(address)
    server.register("make_box", _make_box)
    server.register("make_sphere", _make_sphere)
    server.register("make_cylinder", _make_cylinder)
    server.register("make_cone", _make_cone)
    server.register("make_torus", _make_torus)
    server.register("mesh_get", _mesh_get)
    server.register("mesh_set", _mesh_set)
    server.register("mesh_call", _mesh_call)
    server.register("section", _section)
    server.register("quit", lambda: server.stop())

    bound_addr = server.start()
    print(f"[viewbkg] RPC listening on {bound_addr}")
    # Show blocks and runs the render loop
    display.show(scene)
    server.stop()


def _axis_vec(axis):
    if isinstance(axis, str):
        return {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    return axis
