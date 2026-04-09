"""RenderWorld — pygfx Scene + sync + RWLock."""

import io
import threading
import trimesh
import pygfx as gfx


class RenderWorld:
    """pygfx Scene + gfx.Mesh mirrors.  Read lock for render, write lock for sync."""

    def __init__(self):
        self.lock = _RWLock()
        self.scene = gfx.Scene()
        self.camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
        self.camera.position = (6, 6, 6)
        self.camera.look_at((0, 0, 0))
        self.screen_scene = gfx.Scene()
        self.screen_camera = gfx.ScreenCoordsCamera()
        self.axes = gfx.AxesHelper(1, thickness=2)
        self.scene.add(self.axes)
        self.gfx_map: dict[str, gfx.Mesh] = {}
        self.renderer = None

    def sync_mesh(self, mesh_impl):
        stl = mesh_impl.stl_bytes()
        tmesh = trimesh.load(io.BytesIO(stl), file_type="stl")
        geo = gfx.geometry_from_trimesh(tmesh)
        gmesh = gfx.Mesh(geo, gfx.MeshPhongMaterial(color=mesh_impl.color))
        gmesh.position = mesh_impl.pos
        gmesh.visible = mesh_impl.visible
        old = self.gfx_map.get(mesh_impl.uid)
        if old is not None:
            self.scene.remove(old)
        self.scene.add(gmesh)
        self.gfx_map[mesh_impl.uid] = gmesh
        # Defer axes resize until there's actual content
        if len(self.gfx_map) > 0:
            self._resize_axes()

    def sync_visibility(self, uid, visible):
        gmesh = self.gfx_map.get(uid)
        if gmesh:
            gmesh.visible = visible

    def remove_mesh(self, uid):
        gmesh = self.gfx_map.pop(uid, None)
        if gmesh:
            self.scene.remove(gmesh)
        self._resize_axes()

    def pick_uid(self, x, y):
        if self.renderer is None:
            return None
        hits = self.renderer.get_pick_info((int(x), int(y)))
        if hits and "world_object" in hits:
            wo = hits["world_object"]
            for u, g in self.gfx_map.items():
                if g is wo:
                    return u
        return None

    def _resize_axes(self):
        # Only remove old axes if we've already been added to the scene
        if len(self.scene.children) > 0:
            try:
                self.scene.remove(self.axes)
            except Exception:
                pass
        bb = self.scene.get_bounding_box()
        if bb is None:
            return
        size = max(1.0,
                   abs(bb[1][0] - bb[0][0]) / 2,
                   abs(bb[1][1] - bb[0][1]) / 2,
                   abs(bb[1][2] - bb[0][2]) / 2)
        self.axes = gfx.AxesHelper(size, thickness=2)
        self.scene.add(self.axes)


class _RWLock:
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
