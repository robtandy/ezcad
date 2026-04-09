"""RenderWorld — pygfx Scene + sync helpers, with reader-writer locking.

The main render thread acquires a **read lock** every frame.  The RPC
thread acquires a **write lock** when it needs to mutate the scene
graph.
"""

import io
import threading

import trimesh
import pygfx as gfx


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


class RenderWorld:
    """Holds the pygfx Scene, cameras, and per-mesh gfx.Mesh objects.

    All ``sync_*`` and other mutating methods MUST be called while the
    caller holds the **write lock** (``rw_lock.acquire_write()``).
    """

    def __init__(self):
        self.lock = RWLock()

        self.scene = gfx.Scene()

        self.camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
        self.camera.position = (6, 6, 6)
        self.camera.look_at((0, 0, 0))

        self.screen_scene = gfx.Scene()
        self.screen_camera = gfx.ScreenCoordsCamera()

        self.axes = gfx.AxesHelper(1, thickness=2)
        self.scene.add(self.axes)

        # uid → gfx.Mesh
        self.gfx_map: dict[str, gfx.Mesh] = {}

        self.renderer: gfx.renderers.Renderer | None = None

    # -- write-locked mutators (caller must hold write lock) --

    def sync_mesh(self, mesh_impl):
        """Add or replace the gfx.Mesh mirror for *mesh_impl*."""
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
        self._resize_axes()

    def sync_visibility(self, uid, visible):
        gmesh = self.gfx_map.get(uid)
        if gmesh is not None:
            gmesh.visible = visible

    def remove_mesh(self, uid):
        gmesh = self.gfx_map.pop(uid, None)
        if gmesh is not None:
            self.scene.remove(gmesh)
        self._resize_axes()

    # -- read-only helpers (callers just need a consistent snapshot) --

    def pick_uid(self, x: int, y: int) -> str | None:
        if self.renderer is None:
            return None
        hits = self.renderer.get_pick_info((x, y))
        if hits and "world_object" in hits:
            wo = hits["world_object"]
            for u, gm in self.gfx_map.items():
                if gm is wo:
                    return u
        return None

    # -- internals --

    def _resize_axes(self):
        self.scene.remove(self.axes)
        bb = self.scene.get_bounding_box()
        if bb is None:
            return
        size = max(
            1.0,
            abs(bb[1][0] - bb[0][0]) / 2,
            abs(bb[1][1] - bb[0][1]) / 2,
            abs(bb[1][2] - bb[0][2]) / 2,
        )
        self.axes = gfx.AxesHelper(size, thickness=2)
        self.scene.add(self.axes)
