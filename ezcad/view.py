"""Main API — View + proxy factory functions."""

import time
from multiprocessing import Process

from .rpc import MpRpcClient
from .proxy import _MeshProxy


class View:
    """Spawns a ViewBkg server process.  All geometry lives on the server;
    this object hands out thin proxies.

    The pygfx window appears immediately on creation.
    """

    def __init__(self):
        from . import server

        # Start the server process
        self._proc = Process(target=_launch, daemon=True)
        self._proc.start()

        # Wait for the RPC server to be ready
        connected = False
        for _ in range(50):  # retry for up to ~5 seconds
            time.sleep(0.1)
            try:
                self._client = MpRpcClient(("localhost", 62700))
                # Quick smoke test
                self._client.call("make_box", [1, 1, 1])
                connected = True
                break
            except (ConnectionRefusedError, BlockingIOError, OSError):
                continue
        if not connected:
            raise RuntimeError("Could not connect to viewbkg server")

    # -- factory methods returning proxies --

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

    def section(self, mesh: _MeshProxy, plane="z", value=0.0):
        """Slice a mesh, returning cross-section coords ``[[x,y], ...]``."""
        return self._client.call("section", mesh._uid, plane, value)

    def close(self):
        self._client.call("quit")
        self._client.close()
        self._proc.join(timeout=3)
        self._proc = None


def _launch():
    """Entry point for the server subprocess."""
    import sys
    import warnings
    warnings.filterwarnings("ignore", message="invalid value encountered in")

    from . import server
    server.run_server(("localhost", 62700))
