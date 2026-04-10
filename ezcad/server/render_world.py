"""ViewBkg — pygfx renderer that subscribes to geometry from the RPC server.

ViewBkg is a WebSocket client that:
1. Runs pygfx Display in the main thread (blocks)
2. Has a background thread running the WebSocket event loop
3. Receives geometry push messages and uses locks to update RenderWorld
"""

from __future__ import annotations

import threading

import numpy as np
import pygfx as gfx

import rpyc

from .messages import Viewable


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


@rpyc.service
class RenderWorldService(rpyc.Service):
    def __init__(self, rworld: RenderWorld):
        self.rworld = rworld

    @rpyc.exposed
    def remove(self, uid: str):
        """Remove a mesh when the solid is deleted."""
        with self.rworld.lock:
            self.rworld.remove_locked(uid)

    @rpyc.exposed
    def add(self, v: Viewable):
        with self.rworld.lock:
            self.rworld.add_locked(v)


class RenderWorld:
    """pygfx Scene + sync.  Read lock for render, write lock for sync."""

    def __init__(self):
        self.lock = threading.Lock()
        self.scene = gfx.Scene()
        self.camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
        self.camera.position = (6, 6, 6)
        self.camera.look_at((0, 0, 0))
        self.camera.add(gfx.DirectionalLight())
        self.scene.add(gfx.AmbientLight())

        self.axes = gfx.AxesHelper(1, thickness=2)
        self.scene.add(self.axes)

        self.renderer = None
        self.gfx_map: dict[str, gfx.Mesh] = {}

        # Tiny invisible sphere so show() can compute a bounding sphere
        ph = gfx.Mesh(gfx.sphere_geometry(0.01), gfx.MeshBasicMaterial())
        ph.visible = False
        self.scene.add(ph)

    def _before_render(self):
        if self.renderer is None:
            r = getattr(self._display, "renderer", None)
            if r is not None:
                self.renderer = r
        self.lock.acquire()

    def _after_render(self):
        self.lock.release()

    def add_locked(self, v: Viewable):
        """Apply update while holding the write lock."""
        positions = np.frombuffer(v.positions, dtype=np.float32).reshape(-1, 3)
        indices = np.frombuffer(v.indices, dtype=np.uint32).reshape(-1, 3)
        normals = np.frombuffer(v.normals, dtype=np.float32).reshape(-1, 3)

        if len(positions) == 0:
            return

        geo = gfx.Geometry(
            positions=positions,
            indices=indices,
            normals=normals,
        )
        material = gfx.MeshPhongMaterial(
            color=list(v.color),
            alpha_mode=v.alpha_mode,
        )
        gmesh = gfx.Mesh(geo, material)
        gmesh.position = list(v.pos)
        gmesh.visible = v.visible

        # Replace existing mesh if any
        old = self.gfx_map.get(v.uid)
        if old is not None:
            self.scene.remove(old)
        self.scene.add(gmesh)
        self.gfx_map[msg.uid] = gmesh
        self._resize_axes_locked()

    def remove_locked(self, uid: str):
        gmesh = self.gfx_map.pop(uid, None)
        if gmesh is not None:
            self.scene.remove(gmesh)
        self._resize_axes_locked()

    def _resize_axes(self):
        if len(self.scene.children) <= 1:  # Only ambient light
            return
        try:
            self.scene.remove(self.axes)
        except Exception:
            pass
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

    def show(self):
        # Run pygfx display (blocks main thread)
        self._display = gfx.Display(
            before_render=self._before_render,
            after_render=self._after_render,
            stats=True,
        )
        self._display.show(self.scene)
