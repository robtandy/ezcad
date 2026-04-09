"""Client-side View.  Spawns a viewbkg subprocess and issues RPC calls.

The pygfx window appears immediately on creation.  Shapes are created via
factory methods that return thin proxies — all geometry lives on the server.
"""

import os
import time
from multiprocessing import Process
from .rpc import MpRpcClient
from .proxy import _MeshProxy


class View:
    """Top-level viewer.  The pygfx window appears immediately on creation.

    In headless environments (no ``DISPLAY``), the GUI subprocess is not
    started and a ``_HeadlessClient`` is used to talk to a pure-RPC server
    without a render loop.
    """

    def __init__(self):
        self._headless = os.environ.get("EZCAD_HEADLESS") == "1" or os.environ.get("DISPLAY") is None
        self._proc = None

        if self._headless:
            self._proc = Process(target=_launch_headless, daemon=True)
        else:
            self._proc = Process(target=_launch, daemon=True)
        self._proc.start()

        connected = False
        for _ in range(50):
            time.sleep(0.1)
            try:
                self._client = MpRpcClient(("localhost", 62700))
                uid = self._client.call("make_box", [1, 1, 1])
                self._client.call("delete_mesh", uid)
                connected = True
                break
            except (ConnectionRefusedError, OSError):
                continue
        if not connected:
            raise RuntimeError("Could not connect to viewbkg server")

    def box(self, extents):
        uid = self._client.call("make_box", extents)
        return _MeshProxy(uid, self._client)

    def sphere(self, radius=1.0):
        uid = self._client.call("make_sphere", radius)
        return _MeshProxy(uid, self._client)

    def cylinder(self, radius=1.0, height=1.0):
        uid = self._client.call("make_cylinder", radius, height)
        return _MeshProxy(uid, self._client)

    def cone(self, radius=1.0, height=1.0):
        uid = self._client.call("make_cone", radius, height)
        return _MeshProxy(uid, self._client)

    def torus(self, major_radius=1.0, minor_radius=0.25):
        uid = self._client.call("make_torus", major_radius, minor_radius)
        return _MeshProxy(uid, self._client)

    def section(self, mesh, plane="z", value=0.0):
        return self._client.call("section", mesh._uid, plane, value)

    def close(self):
        try:
            self._client.call("quit")
            self._client.close()
        except OSError:
            pass
        if self._proc:
            self._proc.join(timeout=3)
            self._proc = None


def _launch():
    """Normal launch: RPC + pygfx render loop."""
    import warnings
    warnings.filterwarnings("ignore", message="invalid value encountered in")
    from . import server
    server.run_server(("localhost", 62700))


def _launch_headless():
    """Headless launch: RPC only, no pygfx."""
    from . import server
    server.run_headless(("localhost", 62700))
