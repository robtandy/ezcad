"""ezcad — a proxy-based CAD library with a pygfx viewer."""

import os
import time
import socket

from . import d2  # noqa
from . import d3  # noqa
from .rpc import MpRpcClient

_view = None


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class View:
    """Spawns a viewbkg subprocess and maintains the RPC connection."""

    def __init__(self):
        global _view
        _view = self

        from multiprocessing import Process

        port = _free_port()
        self._headless = os.environ.get("EZCAD_HEADLESS") == "1"

        proc = Process(
            target=_launch_headless if self._headless else _launch,
            args=(port,),
            daemon=True,
        )
        proc.start()
        self._proc = proc
        self._client = None

        for _ in range(50):
            time.sleep(0.1)
            try:
                self._client = MpRpcClient(('localhost', port))
                uid = self._client.call("make_box", [1, 1, 1])
                self._client.call("delete_mesh", uid)
                break
            except (ConnectionRefusedError, OSError):
                continue
        else:
            raise RuntimeError("Could not connect to viewbkg server")

    def close(self):
        try:
            self._client.call("quit")
            self._client.close()
        except OSError:
            pass
        self._proc.join(timeout=3)
        self._proc = None
        global _view
        _view = None

    @property
    def client(self):
        return self._client


def _launch(port):
    import warnings
    warnings.filterwarnings("ignore", message="invalid value encountered in")
    from .server.backend import run_server
    run_server(('localhost', port))


def _launch_headless(port):
    from .server.backend import run_headless
    run_headless(('localhost', port))
