import os
import socket
import rpyc
import warnings
import time
import threading

from typing import Any

from .world import World
from .render_world import RenderWorld, RenderWorldService

from multiprocessing import Process

from rpyc.utils.server import ThreadedServer

__all__ = ["connect", "shutdown", "_connection"]

_connection: "Connection | None" = None


def connect():
    global _connection
    if not _connection:
        _connection = Connection()
    return _connection.world


def shutdown():
    global _connection
    _connection.close()


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class Connection:
    def __init__(self):
        warnings.filterwarnings("ignore", message="invalid value encountered in")

        self._world_port = 22351  # _free_port()
        self._render_world_port = 22360  # _free_port()

        self._render_world_proc = Process(
            target=_launch_render_world,
            args=(self._render_world_port,),
            daemon=True,
        )
        self._render_world_proc.start()
        self._render_world_conn = self._connect_client(self._render_world_port)

        self._world_proc = Process(
            target=_launch_world,
            args=(self._world_port, self.render_world),
            daemon=True,
        )
        self._world_proc.start()
        self._world_conn = self._connect_client(self._world_port)

    def _connect_client(self, port: int):
        print("trying to connect...")
        start = time.time()
        elapsed = 1
        last_exc = None
        conn = None
        while elapsed < 5.0:
            try:
                conn = rpyc.connect("0.0.0.0", port)
            except ConnectionRefusedError as e:
                last_exc = e
            finally:
                elapsed = time.time() - start

        if not conn:
            raise last_exc
        return conn

    def close(self):
        self._world_conn.close()
        self._render_world_conn.close()

        self._world_proc.terminate()
        self._world_proc.join(timeout=3)

        self._render_world_proc.terminate()
        self._render_world_proc.join(timeout=3)

    @property
    def world(self):
        return self._world_conn.root

    @property
    def render_world(self):
        return self._render_world_conn.root


def _launch_world(port: int, rworld):  # what is the type of rworld
    print(f"Launching {World} on port {port}")
    world = World(rworld)
    t = ThreadedServer(world, hostname="0.0.0.0", port=port)
    t.start()


def _launch_render_world(port: int):
    rw = RenderWorld()

    def launch():
        srv = RenderWorldService(rw)
        t = ThreadedServer(srv, hostname="0.0.0.0", port=port)
        t.start()

    threading.Thread(target=launch).start()
    rw.show()


def _resolve_headless(headless):
    if headless is not None:
        return headless
    return os.environ.get("EZCAD_HEADLESS") == "1"
