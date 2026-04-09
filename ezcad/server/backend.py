"""ViewBkg — ties together World, RenderWorld, PieMenu, RPC servers.
Only imported in the viewbkg subprocess.
"""

import time
import pygfx as gfx

from ..rpc import MpRpcServer
from .world import World
from .render import RenderWorld
from .menu import PieMenu, _MenuSpec


class ViewBkg:
    def __init__(self):
        self.world = World()
        self.render = RenderWorld()
        self.menu = PieMenu()
        self._menu_open = False
        self._server = None
        self._display = None  # set in run() before show()

    # ── entry points ─────────────────────────────────────────────────

    def run(self, address: tuple, server: MpRpcServer = None):
        self._server = server or self._make_server(address)
        self._register_handlers()
        self._display = gfx.Display(
            before_render=self._before_render,
            after_render=self._after_render,
            stats=True,
        )
        self._display.show(self.render.scene)
        if self._server:
            self._server.stop()

    def run_headless(self, address: tuple, server: MpRpcServer = None):
        self._server = server or self._make_server(address)
        self._register_handlers_headless()
        addr = self._server.start()
        print(f"[viewbkg] headless RPC on {addr}")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        self._server.stop()

    # ── render-loop hooks ────────────────────────────────────────────

    def _before_render(self):
        r = self.render
        if r.renderer is None:
            d_renderer = getattr(self._display, "renderer", None)
            if d_renderer is not None:
                r.renderer = d_renderer
                r.renderer.add_event_handler(
                    self._on_pointer, "pointer_up", "pointer_move")
        r.lock.acquire_read()

    def _after_render(self):
        r = self.render
        if self._menu_open and r.renderer is not None:
            try:
                r.renderer.render(r.screen_scene, r.screen_camera)
            except Exception:
                pass
        r.lock.release_read()

    # ── event handler ────────────────────────────────────────────────

    def _on_pointer(self, event):
        x, y = event.x, event.y
        button = getattr(event, "button", -1)
        is_right = button == 2

        if self._menu_open:
            if event.type == "pointer_move":
                self.menu.handle_mouse(x, y)
            elif is_right:
                self.menu.close()
                self._menu_open = False
            else:
                self.menu.handle_click(x, y)
                self._menu_open = False
            return

        if is_right:
            self.render.lock.acquire_write()
            try:
                self.menu.open_at(
                    x, y, self.render.screen_scene, _placeholder_specs())
                self._menu_open = True
            finally:
                self.render.lock.release_write()

    # ── RPC handlers (graphical) ─────────────────────────────────────

    def _register_handlers(self):
        world = self.world
        render = self.render
        s = self._server

        def _make(kind, **kw):
            if kind == "box":
                uid = world.make_box(kw["extents"])
            elif kind == "sphere":
                uid = world.make_sphere(kw.get("radius", 1.0))
            elif kind == "cylinder":
                uid = world.make_cylinder(kw.get("radius", 1.0), kw.get("height", 1.0))
            elif kind == "cone":
                uid = world.make_cone(kw.get("radius", 1.0), kw.get("height", 1.0))
            elif kind == "torus":
                uid = world.make_torus(kw.get("major_radius", 1.0), kw.get("minor_radius", 0.25))
            else:
                raise ValueError(f"Unknown kind: {kind}")
            render.lock.acquire_write()
            try:
                render.sync_mesh(world.meshes[uid])
            finally:
                render.lock.release_write()
            return uid

        def _mesh_get(uid, attr):
            return world.mesh_get(uid, attr)

        def _mesh_set(uid, attr, value):
            world.mesh_set(uid, attr, value)
            if attr in ("visible", "color"):
                render.lock.acquire_write()
                try:
                    if attr == "visible":
                        render.sync_visibility(uid, value)
                    else:
                        render.sync_mesh(world.meshes[uid])
                finally:
                    render.lock.release_write()

        def _mesh_call(uid, method, args=(), kwargs=None):
            result = world.mesh_call(uid, method, args=args, kwargs=kwargs)
            render.lock.acquire_write()
            try:
                render.sync_mesh(world.meshes[uid])
            finally:
                render.lock.release_write()
            return result

        def _section(uid, plane="z", value=0.0):
            return world.meshes[uid].section_vertices(plane, value)

        def _delete_mesh(uid):
            world.delete_mesh(uid)
            render.lock.acquire_write()
            try:
                render.remove_mesh(uid)
            finally:
                render.lock.release_write()

        def _profile_get(uid, attr):
            return world.profile_get(uid, attr)

        def _profile_call(uid, method, args=(), kwargs=None):
            return world.profile_call(uid, method, args=args, kwargs=kwargs)

        def _make_profile(kind, **kw):
            if kind == "circle":
                return world.make_circle(kw.get("radius", 1.0), kw.get("segments", 64))
            if kind == "rect":
                return world.make_rect(kw.get("width", 1.0), kw.get("height", 1.0))
            if kind == "ngon":
                return world.make_ngon(kw.get("radius", 1.0), kw.get("sides", 6))
            raise ValueError(f"Unknown profile kind: {kind}")

        s.register("make_box", lambda e: _make("box", extents=e))
        s.register("make_sphere", lambda r=1.0: _make("sphere", radius=r))
        s.register("make_cylinder", lambda r=1.0, h=1.0: _make("cylinder", radius=r, height=h))
        s.register("make_cone", lambda r=1.0, h=1.0: _make("cone", radius=r, height=h))
        s.register("make_torus", lambda R=1.0, r=0.25: _make("torus", major_radius=R, minor_radius=r))
        s.register("mesh_get", _mesh_get)
        s.register("mesh_set", _mesh_set)
        s.register("mesh_call", _mesh_call)
        s.register("section", _section)
        s.register("delete_mesh", _delete_mesh)
        s.register("make_circle", lambda r=1.0, s=64: _make_profile("circle", radius=r, segments=s))
        s.register("make_rect", lambda w=1.0, h=1.0: _make_profile("rect", width=w, height=h))
        s.register("make_ngon", lambda r=1.0, s=6: _make_profile("ngon", radius=r, sides=s))
        s.register("profile_get", _profile_get)
        s.register("profile_call", _profile_call)
        s.register("quit", lambda: self._server.stop())
        bound = self._server.start()
        print(f"[viewbkg] RPC on {bound}")

    # ── RPC handlers (headless) ──────────────────────────────────────

    def _register_handlers_headless(self):
        world = self.world
        s = self._server

        def _make(kind, **kw):
            if kind == "box": return world.make_box(kw["extents"])
            if kind == "sphere": return world.make_sphere(kw.get("radius", 1.0))
            if kind == "cylinder": return world.make_cylinder(kw.get("radius", 1.0), kw.get("height", 1.0))
            if kind == "cone": return world.make_cone(kw.get("radius", 1.0), kw.get("height", 1.0))
            if kind == "torus": return world.make_torus(kw.get("major_radius", 1.0), kw.get("minor_radius", 0.25))
            raise ValueError(kind)

        s.register("make_box", lambda e: _make("box", extents=e))
        s.register("make_sphere", lambda r=1.0: _make("sphere", radius=r))
        s.register("make_cylinder", lambda r=1.0, h=1.0: _make("cylinder", radius=r, height=h))
        s.register("make_cone", lambda r=1.0, h=1.0: _make("cone", radius=r, height=h))
        s.register("make_torus", lambda R=1.0, r=0.25: _make("torus", major_radius=R, minor_radius=r))
        s.register("mesh_get", world.mesh_get)
        s.register("mesh_set", world.mesh_set)
        s.register("mesh_call", world.mesh_call)
        s.register("section", lambda uid, plane="z", value=0.0: world.meshes[uid].section_vertices(plane, value))
        s.register("delete_mesh", world.delete_mesh)
        s.register("profile_get", world.profile_get)
        s.register("profile_call", world.profile_call)
        s.register("make_circle", lambda r=1.0, s=64: world.make_circle(r, s))
        s.register("make_rect", lambda w=1.0, h=1.0: world.make_rect(w, h))
        s.register("make_ngon", lambda r=1.0, s=6: world.make_ngon(r, s))
        s.register("quit", lambda: self._server.stop())
        bound = self._server.start()
        print(f"[viewbkg] headless RPC on {bound}")

    @staticmethod
    def _make_server(address: tuple) -> MpRpcServer:
        return MpRpcServer(address)


# ── module-level convenience ─────────────────────────────────────────

def run_server(address: tuple, _external_listener=None):
    v = ViewBkg()
    server = v._make_server(address)
    if _external_listener is not None:
        server._listener = _external_listener
    v.run(address, server=server)


def run_headless(address: tuple, _external_listener=None):
    v = ViewBkg()
    server = v._make_server(address)
    if _external_listener is not None:
        server._listener = _external_listener
    v.run_headless(address, server=server)


def _placeholder_specs():
    verts = [[-10, -10], [10, -10], [10, 10], [-10, 10]]
    return [_MenuSpec(icon_verts=verts) for _ in range(5)]
