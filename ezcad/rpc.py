"""RPC abstraction for client↔server communication.

The ``RpcClient`` / ``RpcServer`` interface is stable.  Swap the backend
by replacing the concrete implementations below — the rest of the codebase
only sees the abstract API.
"""

import uuid
from abc import ABC, abstractmethod
from multiprocessing.connection import Listener, Client
from threading import Thread


class RpcError(Exception):
    """Raised when the server-side handler raises an exception."""
    pass


class RpcClient(ABC):
    """Synchronous RPC client."""

    @abstractmethod
    def call(self, method: str, *args, **kwargs): ...
    @abstractmethod
    def close(self): ...


class RpcServer(ABC):
    """RPC server — handlers are called in the listener thread."""

    @abstractmethod
    def register(self, name: str, handler): ...
    @abstractmethod
    def start(self) -> tuple: ...
    @abstractmethod
    def stop(self): ...


# ─── multiprocessing.connection backend ─────────────────────────────────

class MpRpcClient(RpcClient):
    def __init__(self, address: tuple):
        self._conn = Client(address, authkey=b"ezcad")

    def call(self, method: str, *args, **kwargs):
        rid = uuid.uuid4().hex
        self._conn.send((method, args, kwargs, rid))
        tag, data = self._conn.recv()
        if tag == "err":
            raise RpcError(data)
        return data

    def close(self):
        self._conn.close()


class MpRpcServer(RpcServer):
    """Single-client server backed by ``multiprocessing.connection``."""

    def __init__(self, address: tuple = ("localhost", 0)):
        self._address = address
        self._handlers = {}
        self._listener = None
        self._running = False
        self._thread: Thread | None = None

    def register(self, name: str, handler):
        self._handlers[name] = handler

    def start(self) -> tuple:
        if self._listener is None:
            self._listener = Listener(self._address, authkey=b"ezcad")
        self._running = True
        self._thread = Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self._listener.address

    def stop(self):
        self._running = False
        if self._listener:
            self._listener.close()

    def _serve(self):
        while self._running:
            try:
                conn = self._listener.accept()
            except Exception:
                break
            while self._running:
                try:
                    method, args, kwargs, rid = conn.recv()
                    fn = self._handlers.get(method)
                    if fn is None:
                        conn.send(("err", f"No handler '{method}'"))
                    else:
                        try:
                            conn.send(("ok", fn(*args, **kwargs)))
                        except Exception as e:
                            conn.send(("err", str(e)))
                except (OSError, EOFError, BrokenPipeError):
                    conn.close()
                    break
                except Exception as e:
                    conn.send(("err", str(e)))
