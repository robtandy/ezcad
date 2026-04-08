"""ViewBkg server process.

Owns two worlds:
  - **World**: domain objects (ServerMesh), accessed only by
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

from .rpc import MpRpcServer
from .menu import PieMenu, _MenuSpec


# ---------------------------------------------------------------------------
# Reader-writer lock  (single writer, multiple readers)
# ---------------------------------------------------------------------------

class RWLock:
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

    def mass(self, density=1.0):
        return self._mesh.volume * density

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


# ---------------------------------------------------------------------------
# World  (RPC-thread exclusive, no locking)
# ---------------------------------------------------------------------------

class World:
    def __init__(self):
        self.meshes: dict[str, ServerMesh] = {}

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
            uid, trimesh.creation.cylinder(radius=radius, height=height))
        return uid

    def make_cone(self, radius=1.0, height=1.0):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(
            uid, trimesh.creation.cone(radius=radius, height=height))
        return uid

    def make_torus(self, major_radius=1.0, minor_radius=0.25):
        uid = str(uuid.uuid4())[:8]
        self.meshes[uid] = ServerMesh(
            uid, trimesh.creation.torus(
                major_radius=major_radius, minor_radius=minor_radius))
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


# ---------------------------------------------------------------------------
# ViewBkg – the server subprocess entry point
# ---------------------------------------------------------------------------

from shapely.geometry import Polygon  # noqa: E402


def run_server(address: tuple = ("localhost", 0), event_queue=None):
    world = World()
    rw_lock = RWLock()

    # ── pygfx render setup ──────────────────────────────────────────
    scene = gfx.Scene()
    camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
    camera.position = (6, 6, 6)
    camera.look_at((0, 0, 0))
    controller = gfx.OrbitController(camera)

    # Screen-space overlay for pie menu
    screen_scene = gfx.Scene()
    screen_camera = gfx.ScreenCoordsCamera()

    axes_ref = [gfx.AxesHelper(1, thickness=2)]
    scene.add(axes_ref[0])

    _gfx_map: dict[str, gfx.Mesh] = {}

    def _update_axes(bb):
        if bb is None:
            return
        size = max(1.0,
                   abs(bb[1][0] - bb[0][0]) / 2,
                   abs(bb[1][1] - bb[0][1]) / 2,
                   abs(bb[1][2] - bb[0][2]) / 2)
        old = axes_ref[0]
        scene.remove(old)
        axes_ref[0] = gfx.AxesHelper(size, thickness=2)
        scene.add(axes_ref[0])

    def _sync_mesh_to_render(uid):
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
        _update_axes(scene.get_bounding_box())

    def _sync_visibility(uid):
        gmesh = _gfx_map.get(uid)
        if gmesh:
            gmesh.visible = world.meshes[uid].visible

    def _pick_uid(x, y, renderer):
        hits = renderer.get_pick_info((int(x), int(y)))
        if hits and "world_object" in hits:
            wo = hits["world_object"]
            for u, gm in _gfx_map.items():
                if gm is wo:
                    return u
        return None

    # ── Pie menu ────────────────────────────────────────────────────
    def _on_menu_click(action_name, x, y, hit_uid):
        if event_queue is not None:
            try:
                event_queue.put(("menu_click", action_name, x, y, hit_uid))
            except Exception:
                pass

    menu = PieMenu(on_click=_on_menu_click)
    menu_specs = []
    menu_open = [False]

    # ── RPC handlers ────────────────────────────────────────────────

    def _rpc_make(kind, **kw):
        if kind == "box":
            uid = world.make_box(kw["extents"])
        elif kind == "sphere":
            uid = world.make_sphere(kw.get("radius", 1.0))
        elif kind == "cylinder":
            uid = world.make_cylinder(kw.get("radius", 1.0), kw.get("height", 1.0))
        elif kind == "cone":
            uid = world.make_cone(kw.get("radius", 1.0), kw.get("height", 1.0))
        elif kind == "torus":
            uid = world.make_torus(kw.get("major_radius", 1.0),
                                   kw.get("minor_radius", 0.25))
        else:
            raise ValueError(f"Unknown kind: {kind}")
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return uid

    renderer_ref = [None]

    def _on_pointer(event):
        x, y = event.x, event.y
        button = getattr(event, "button", -1)
        is_right = button == 2
        is_left = button == 0

        if not menu_open[0]:
            # right-click opens menu
            if is_right and event.type == "pointer_up":
                if menu_specs:
                    menu.open_at(x, y, screen_scene, menu_specs[:])
                    menu_open[0] = True
                return
        else:
            # menu is open
            if event.type == "pointer_move":
                menu.handle_mouse(x, y)
            elif is_right and event.type == "pointer_up":
                menu.close()
                menu_open[0] = False
            elif is_left and event.type == "pointer_up":
                hit_uid = _pick_uid(x, y, renderer_ref[0])
                menu.handle_click(x, y, hit_uid)
            return

    def _before_render_with_events():
        if renderer_ref[0] is None and display.renderer:
            renderer_ref[0] = display.renderer
            display.renderer.add_event_handler(
                _on_pointer, "pointer_up", "pointer_move")
        rw_lock.acquire_read()

    def _after_render_composite():
        if menu_open[0] and renderer_ref[0]:
            try:
                renderer_ref[0].render(screen_scene, screen_camera)
            except Exception:
                pass
        rw_lock.release_read()

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
        rw_lock.acquire_write()
        try:
            _sync_mesh_to_render(uid)
        finally:
            rw_lock.release_write()
        return result

    def _section(uid, plane="z", value=0.0):
        return world.meshes[uid].section_vertices(plane, value)

    def _register_menu(specs):
        nonlocal menu_specs
        menu_specs = specs

    server = MpRpcServer(address)
    server.register("make_box", lambda e: _rpc_make("box", extents=e))
    server.register("make_sphere", lambda r=1.0: _rpc_make("sphere", radius=r))
    server.register("make_cylinder", lambda r=1.0, h=1.0: _rpc_make(
        "cylinder", radius=r, height=h))
    server.register("make_cone", lambda r=1.0, h=1.0: _rpc_make(
        "cone", radius=r, height=h))
    server.register("make_torus", lambda R=1.0, r=0.25: _rpc_make(
        "torus", major_radius=R, minor_radius=r))
    server.register("mesh_get", _mesh_get)
    server.register("mesh_set", _mesh_set)
    server.register("mesh_call", _mesh_call)
    server.register("section", _section)
    server.register("register_menu", _register_menu)
    server.register("quit", lambda: server.stop())

    bound_addr = server.start()
    print(f"[viewbkg] RPC listening on {bound_addr}")
    display = gfx.Display(
        before_render=_before_render_with_events,
        after_render=_after_render_composite,
        stats=True,
    )
    display.show(scene)
    server.stop()


def _axis_vec(axis):
    if isinstance(axis, str):
        return {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    return list(axis)
