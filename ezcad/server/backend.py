"""ViewBkg — ties World + RenderWorld + PieMenu + RPC together."""

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
        self._display = None

    def run(self, address, server=None):
        self._server = server or MpRpcServer(address)
        self._register_handlers()
        self._server.start()
        self._display = gfx.Display(
            before_render=self._before_render,
            after_render=self._after_render, stats=True)
        self._display.show(self.render.scene)
        self._server and self._server.stop()

    def run_headless(self, address, server=None):
        self._server = server or MpRpcServer(address)
        self._register_handlers()
        self._server.start()
        print(f"[viewbkg] headless on {self._server._listener.address}")
        try:
            while True: time.sleep(0.5)
        except KeyboardInterrupt: pass
        self._server.stop()

    def _before_render(self):
        if self.render.renderer is None:
            r = getattr(self._display, "renderer", None)
            if r is not None:
                self.render.renderer = r
                r.add_event_handler(self._on_pointer, "pointer_up", "pointer_move")
        self.render.lock.acquire_read()

    def _after_render(self):
        if self._menu_open and self.render.renderer:
            try: self.render.renderer.render(self.render.screen_scene, self.render.screen_camera)
            except: pass
        self.render.lock.release_read()

    def _on_pointer(self, event):
        x, y = event.x, event.y
        is_right = getattr(event, "button", -1) == 2
        if self._menu_open:
            if event.type == "pointer_move":
                self.menu.handle_mouse(x, y)
            elif is_right:
                self.menu.close(); self._menu_open = False
            else:
                self.menu.handle_click(x, y); self._menu_open = False
            return
        if is_right:
            self.render.lock.acquire_write()
            self.menu.open_at(x, y, self.render.screen_scene,
                              [_MenuSpec(icon_verts=[[-10,-10],[10,-10],[10,10],[-10,10]])]*5)
            self._menu_open = True
            self.render.lock.release_write()

    def _register_handlers(self):
        w, rd, s = self.world, self.render, [0]  # dummy to avoid name clash

        def _make(kind, **kw):
            if kind == "box": uid = w.make_box(kw["extents"])
            elif kind == "sphere": uid = w.make_sphere(kw.get("radius",1.0))
            elif kind == "cylinder": uid = w.make_cylinder(kw.get("radius",1.0), kw.get("height",1.0))
            elif kind == "cone": uid = w.make_cone(kw.get("radius",1.0), kw.get("height",1.0))
            elif kind == "torus": uid = w.make_torus(kw.get("major_radius",1.0), kw.get("minor_radius",0.25))
            rd.lock.acquire_write()
            try: rd.sync_mesh(w.meshes[uid])
            finally: rd.lock.release_write()
            return uid

        def _mesh_set(uid, attr, value):
            w.mesh_set(uid, attr, value)
            if attr in ("visible", "color"):
                rd.lock.acquire_write()
                try:
                    if attr == "visible": rd.sync_visibility(uid, value)
                    else: rd.sync_mesh(w.meshes[uid])
                finally: rd.lock.release_write()

        def _mesh_call(uid, method, args=(), kwargs=None):
            result = w.mesh_call(uid, method, args=args, kwargs=kwargs)
            rd.lock.acquire_write()
            try: rd.sync_mesh(w.meshes[uid])
            finally: rd.lock.release_write()
            return result

        def _del(uid):
            w.delete_mesh(uid)
            rd.lock.acquire_write()
            try: rd.remove_mesh(uid)
            finally: rd.lock.release_write()

        srv = self._server
        srv.register("make_box",          lambda e: _make("box", extents=e))
        srv.register("make_sphere",       lambda r=1.0: _make("sphere", radius=r))
        srv.register("make_cylinder",     lambda r=1.0,h=1.0: _make("cylinder", radius=r, height=h))
        srv.register("make_cone",         lambda r=1.0,h=1.0: _make("cone", radius=r, height=h))
        srv.register("make_torus",        lambda R=1.0,r=0.25: _make("torus", major_radius=R, minor_radius=r))
        srv.register("mesh_get",          lambda uid,attr: w.mesh_get(uid, attr))
        srv.register("mesh_set",          _mesh_set)
        srv.register("mesh_call",         _mesh_call)
        srv.register("section",           lambda uid,plane="z",value=0.0: w.meshes[uid].section_vertices(plane, value))
        srv.register("delete_mesh",       _del)
        srv.register("make_circle",       lambda r=1.0,s=64: w.make_circle(r,s))
        srv.register("make_rect",         lambda w2=1.0,h=1.0: w.make_rect(w2,h))
        srv.register("make_ngon",         lambda r=1.0,s=6: w.make_ngon(r,s))
        srv.register("profile_get",       lambda uid,attr: w.profile_get(uid, attr))
        srv.register("quit",              lambda: self._server.stop())


def run_server(address, _external_listener=None):
    v = ViewBkg()
    srv = MpRpcServer(address)
    if _external_listener: srv._listener = _external_listener
    v.run(address, server=srv)

def run_headless(address, _external_listener=None):
    v = ViewBkg()
    srv = MpRpcServer(address)
    if _external_listener: srv._listener = _external_listener
    v.run_headless(address, server=srv)
