"""Client-side View.  Spawns a server subprocess and issues RPC calls.

The pygfx window appears immediately on creation.  Shapes are created via
factory methods that return thin proxies — all geometry lives on the server.
"""

import time
import queue
from multiprocessing import Process, Queue
from .rpc import MpRpcClient
from .proxy import _MeshProxy
from .menu import _MenuSpec


class ActionRegistry:
    """Map of action-name → callback, living on the client side.

    Callbacks are fired from **the client process** when the server
    detects a menu leaf click.
    """

    def __init__(self, event_queue: Queue):
        self._handlers: dict[str, callable] = {}
        self._event_queue = event_queue

    def add(self, name: str, callback: callable):
        """Register *callback* under *name* for use in pie menu items."""
        self._handlers[name] = callback

    def remove(self, name: str):
        self._handlers.pop(name, None)

    def poll(self) -> int:
        """Drain the event queue and fire matching callbacks.

        Returns the number of events processed.
        """
        count = 0
        while True:
            try:
                evt = self._event_queue.get_nowait()
            except queue.Empty:
                break
            if evt[0] == "menu_click":
                _, action_name, x, y, hit_uid = evt
                handler = self._handlers.get(action_name)
                if handler:
                    hit_shape = _MeshProxy(hit_uid, None) if hit_uid else None
                    handler(x, y, hit_shape)
            count += 1
        return count


class View:
    """Top-level viewer.  The pygfx window appears immediately on creation."""

    def __init__(self):
        self._event_queue = Queue()
        self._proc = Process(
            target=_launch,
            args=(self._event_queue,),
            daemon=True,
        )
        self._proc.start()

        # Wait for the server to be ready
        connected = False
        for _ in range(50):
            time.sleep(0.1)
            try:
                self._client = MpRpcClient(("localhost", 62700))
                self._client.call("make_box", [1, 1, 1])
                connected = True
                break
            except (ConnectionRefusedError, OSError):
                continue
        if not connected:
            raise RuntimeError("Could not connect to viewbkg server")

        self.actions = ActionRegistry(self._event_queue)

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
        return self._client.call("section", mesh._uid, plane, value)

    def register_menu(self, items: list):
        """Build a menu tree from ``_MenuSpec`` dicts and send to server."""
        self._client.call("register_menu", [_norm_spec(i) for i in items])

    def poll_actions(self):
        """Check for and dispatch any pending menu callbacks."""
        return self.actions.poll()

    def close(self):
        self._client.call("quit")
        self._client.close()
        self._proc.join(timeout=3)
        self._proc = None


def _norm_spec(item) -> _MenuSpec:
    """Normalise user input into a picklable ``_MenuSpec``."""
    if isinstance(item, _MenuSpec):
        return item
    if isinstance(item, dict):
        return _MenuSpec(
            icon=item.get("icon"),
            action=item.get("action", ""),
            children=[_norm_spec(c) for c in item.get("children", [])],
        )
    return _MenuSpec(
        icon=getattr(item, "icon", None),
        action=getattr(item, "action", ""),
        children=[_norm_spec(c) for c in (getattr(item, "children", []) or [])],
    )


def _launch(event_queue: Queue):
    import warnings
    warnings.filterwarnings("ignore", message="invalid value encountered in")
    from . import server
    server.run_server(("localhost", 62700), event_queue=event_queue)
