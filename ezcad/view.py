import pygfx as gfx
import io
import trimesh

from .d3.shape import Mesh
from .commands import QuitCmd


class View:
    def __init__(self):
        self.proc = None  # started lazily on first show_in

    def _ensure_running(self):
        if self.proc is not None and self.proc.is_alive():
            return
        from multiprocessing import Process, Queue
        self.queue = Queue()
        self.proc = Process(target=_view_in_background, args=(self.queue,), daemon=True)
        self.proc.start()

    def add(self, mesh: 'Mesh'):
        self._ensure_running()
        mesh.show_in(self)

    def close(self):
        if self.proc and self.proc.is_alive():
            self.queue.put(QuitCmd())
            self.proc.join(timeout=3)
            self.proc = None


def _view_in_background(queue):
    _ViewBkg(queue)


class _ViewBkg:
    def __init__(self, queue):
        self.queue = queue
        self.scene = gfx.Scene()
        self.display = gfx.Display(
            before_render=self._before, stats=True,
        )

        self.axes = gfx.AxesHelper(1, thickness=2)
        self.scene.add(self.axes)

        # uuid → gfx.Mesh mapping
        self.gfx_map = {}

        self.display.show(self.scene)

    def _before(self):
        while True:
            try:
                cmd = self.queue.get_nowait()
                cmd.execute(self)
            except Exception:
                break

    def _update_gfx_mesh(self, uuid, mesh_data, pos, color):
        """Convert STL bytes → pygfx Mesh and place in scene."""
        tmesh = trimesh.load(io.BytesIO(mesh_data), file_type="stl")
        geo = gfx.geometry_from_trimesh(tmesh)
        gmesh = gfx.Mesh(geo, gfx.MeshPhongMaterial(color=color))
        gmesh.position = pos

        # replace or add
        old = self.gfx_map.get(uuid)
        if old is not None:
            self.scene.remove(old)
        self.scene.add(gmesh)
        self.gfx_map[uuid] = gmesh
        self._resize_axes()

    def _resize_axes(self):
        self.scene.remove(self.axes)
        bb = self.scene.get_bounding_box()
        dx = abs(bb[1][0] - bb[0][0]) / 2
        dy = abs(bb[1][1] - bb[0][1]) / 2
        dz = abs(bb[1][2] - bb[0][2]) / 2
        size = max(1.0, dx, dy, dz)
        self.axes = gfx.AxesHelper(size, thickness=2)
        self.scene.add(self.axes)
