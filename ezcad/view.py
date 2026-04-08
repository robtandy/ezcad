"""Multiprocess viewer for ezcad with pie menu support."""

import pygfx as gfx
import io
import trimesh
from queue import Empty

from .d3.shape import Mesh
from .commands import (
    AddCmd, SyncCmd, VisibilityCmd, QuitCmd,
    MenuClickCmd, MenuOpenCmd, MenuCloseCmd, RequestMenuOpen,
)
from .menu import PieMenu, _ItemSpec


class View:
    """Top-level viewer.  Starts lazily on first ``add()``."""

    def __init__(self):
        self.proc = None
        self.menu_items = []

    def register_menu(self, menu_items):
        """Register the root ``MenuItem`` list for the pie menu."""
        self.menu_items = menu_items

    def _ensure_running(self):
        if self.proc is not None and self.proc.is_alive():
            return
        from multiprocessing import Process, Queue
        self.queue = Queue()
        self.return_queue = Queue()
        self.proc = Process(
            target=_view_in_background,
            args=(self.queue, self.return_queue),
            daemon=True,
        )
        self.proc.start()

    def add(self, mesh: Mesh):
        self._ensure_running()
        mesh.show_in(self)

    def open_menu_at(self, x: float, y: float):
        self._ensure_running()
        specs = [_ItemSpec(it) for it in self.menu_items]
        self.queue.put(MenuOpenCmd(x, y, specs))

    def close_menu(self):
        self._ensure_running()
        self.queue.put(MenuCloseCmd())

    def get_return(self):
        """Non-blocking: return next view→main message, or None."""
        try:
            return self.return_queue.get_nowait()
        except Empty:
            return None

    def close(self):
        if self.proc and self.proc.is_alive():
            self.queue.put(QuitCmd())
            self.proc.join(timeout=3)
            self.proc = None


def _view_in_background(queue, return_queue):
    _ViewBkg(queue, return_queue)


class _ViewBkg:
    def __init__(self, queue, return_queue):
        self.queue = queue
        self.return_queue = return_queue
        self._renderer = None
        self._camera = None

        # 3D scene
        self.scene = gfx.Scene()
        self.camera = gfx.PerspectiveCamera(50, 1.0, depth_range=(0.1, 1000))
        self.camera.position = (6, 6, 6)
        self.camera.look_at((0, 0, 0))

        # Screen-space overlay for pie menu
        self.screen_scene = gfx.Scene()
        self.screen_camera = gfx.ScreenCoordsCamera()

        # Pie menu
        self.menu = PieMenu()
        self._menu_open = False

        # Axes helper
        self.axes = gfx.AxesHelper(1, thickness=2)
        self.scene.add(self.axes)

        # shape-uuid -> gfx.Mesh
        self.gfx_map = {}

        self.display = gfx.Display(
            before_render=self._before_render,
            stats=True,
        )

    def _before_render(self):
        if self._renderer is None and self.display.renderer:
            self._renderer = self.display.renderer
            self._renderer.add_event_handler(
                self._on_pointer, "pointer_up", "pointer_move"
            )

        while True:
            try:
                cmd = self.queue.get_nowait()
                cmd.execute(self)
            except Empty:
                break

        if self._menu_open and self._renderer:
            try:
                self._renderer.render(self.screen_scene, self.screen_camera)
            except Exception:
                pass

    def _on_pointer(self, event):
        x, y = int(event.x), int(event.y)
        button = getattr(event, "button", -1)
        is_right = button == 2
        is_left = button == 0
        is_move = event.type == "pointer_move"

        # ---- menu open ----
        if self._menu_open:
            if is_move:
                self.menu.handle_mouse(x, y)
            elif is_right and event.type == "pointer_up":
                self._close_menu()
            elif is_left and event.type == "pointer_up":
                self._handle_menu_click(x, y)
            return  # consume event, don't let orbit controller run while open

        # ---- menu closed ----
        if is_right and event.type == "pointer_up":
            hit_uuid = self._pick_uuid(x, y)
            self.return_queue.put(RequestMenuOpen(x, y, hit_uuid))
            return
        # everything else falls to orbit controller / renderer

    # ---- menu interactions -----------------------------------------------

    def _handle_menu_click(self, x: int, y: int):
        item_id = self.menu.handle_click(x, y)
        if item_id is not None:
            hit_uuid = self._pick_uuid(x, y)
            cmd = MenuClickCmd(item_id, x, y)
            cmd.hit_shape_uuid = hit_uuid
            self.return_queue.put(cmd)
        # else clicked empty space → close
        self._close_menu()

    def _open_menu(self, x: float, y: float, item_specs):
        self._menu_open = True
        self.menu.open_at(x, y, self.screen_scene, item_specs)

    def _close_menu(self):
        self._menu_open = False
        self.menu.close()

    # ---- shape / mesh commands -------------------------------------------

    def _update_gfx_mesh(self, uuid, mesh_data, pos, color):
        tmesh = trimesh.load(io.BytesIO(mesh_data), file_type="stl")
        geo = gfx.geometry_from_trimesh(tmesh)
        gmesh = gfx.Mesh(geo, gfx.MeshPhongMaterial(color=color))
        gmesh.position = pos

        old = self.gfx_map.get(uuid)
        if old is not None:
            self.scene.remove(old)
        self.scene.add(gmesh)
        self.gfx_map[uuid] = gmesh
        self._resize_axes()

    def _pick_uuid(self, x: int, y: int):
        """Raycast (x, y) on the main scene, return Shape uuid if hit."""
        if self._renderer is None:
            return None
        hits = self._renderer.get_pick_info((x, y))
        if hits and "world_object" in hits:
            wo = hits["world_object"]
            for uid, gmesh in self.gfx_map.items():
                if gmesh is wo:
                    return uid
        return None

    def _resize_axes(self):
        self.scene.remove(self.axes)
        bb = self.scene.get_bounding_box()
        if bb is None:
            return
        dx = abs(bb[1][0] - bb[0][0]) / 2
        dy = abs(bb[1][1] - bb[0][1]) / 2
        dz = abs(bb[1][2] - bb[0][2]) / 2
        size = max(1.0, dx, dy, dz)
        self.axes = gfx.AxesHelper(size, thickness=2)
        self.scene.add(self.axes)
