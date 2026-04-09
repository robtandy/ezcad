"""ezcad — a proxy-based CAD library with a pygfx viewer."""

import os
import time
import tempfile

# Import subpackages so ezcad.d3 and ezcad.d2 are accessible
from . import d2  # noqa
from . import d3   # noqa
from .rpc import MpRpcClient

_view = None


class View:
    """Spawns a viewbkg subprocess and maintains the RPC connection."""

    def __init__(self):
        global _view
        _view = self

        from multiprocessing import Process

        addr_file = tempfile.mktemp(prefix="ezcad_addr_")

        self._headless = os.environ.get("EZCAD_HEADLESS") == "1"

        proc = Process(
            target=_launch_headless if self._headless else _launch,
            args=(addr_file,),
            daemon=True,
        )
        proc.start()
        self._proc = proc
        self._client = None

        for _ in range(50):
            time.sleep(0.1)
            try:
                address = _read_addr(addr_file)
                if address is None:
                    continue
                self._client = MpRpcClient(address)
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


def _read_addr(path):
    try:
        with open(path) as f:
            line = f.read().strip()
            if not line:
                return None
            return eval(line)
    except (FileNotFoundError, SyntaxError):
        return None


def _launch(addr_file):
    import warnings
    warnings.filterwarnings("ignore", message="invalid value encountered in")
    from multiprocessing.connection import Listener
    from .server.backend import run_server

    listener = Listener(("localhost", 0), authkey=b"ezcad")
    address = listener.address
    with open(addr_file, "w") as f:
        f.write(repr(address))
    run_server(address, _external_listener=listener)


def _launch_headless(addr_file):
    from multiprocessing.connection import Listener
    from .server.backend import run_headless

    listener = Listener(("localhost", 0), authkey=b"ezcad")
    address = listener.address
    with open(addr_file, "w") as f:
        f.write(repr(address))
    run_headless(address, _external_listener=listener)
