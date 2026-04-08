"""Thin proxy objects that forward every attribute access / method call to
the ViewBkg server over RPC.

Usage::

    from ezcad import MeshProxy
    b = MeshProxy("box_uid", rpc_client)
    print(b.pos)        # blocks, returns value from server
    b.translate([1,0,0]) # blocks, server executes method
    b.color = "red"     # blocks, server sets attribute
"""

from .rpc import RpcClient


class _MeshProxy:
    """Client-side proxy for a single ``ServerMesh`` on the view server."""

    def __init__(self, uid: str, client: RpcClient):
        object.__setattr__(self, "_uid", uid)
        object.__setattr__(self, "_client", client)

    # -- property access --

    def __getattr__(self, name):
        return self._client.call("mesh_get", self._uid, name)

    def __setattr__(self, name, value):
        self._client.call("mesh_set", self._uid, name, value)

    # -- method calls --

    def __call__(self, method, *args, **kwargs):
        return self._client.call("mesh_call", self._uid, method, list(args), kwargs)

    # -- explicit convenience for chained calls --

    def translate(self, vec):
        self._client.call("mesh_call", self._uid, "translate", [vec], {})
        return self

    def rotate(self, axis, degrees=0, radians=0):
        self._client.call("mesh_call", self._uid, "rotate",
                          [axis], {"degrees": degrees, "radians": radians})
        return self

    def scale(self, factor):
        self._client.call("mesh_call", self._uid, "scale", [factor], {})
        return self

    def mirror(self, plane="xy"):
        self._client.call("mesh_call", self._uid, "mirror", [plane], {})
        return self

    def union(self, other: "_MeshProxy"):
        self._client.call("mesh_call", self._uid, "union",
                          [other._uid], {})
        return self

    def difference(self, other: "_MeshProxy"):
        self._client.call("mesh_call", self._uid, "difference",
                          [other._uid], {})
        return self

    def intersection(self, other: "_MeshProxy"):
        self._client.call("mesh_call", self._uid, "intersection",
                          [other._uid], {})
        return self

    def section(self, plane="z", value=0.0):
        return self._client.call("mesh_call", self._uid, "section",
                                 [], {"plane": plane, "value": value})

    def __repr__(self):
        return f"<MeshProxy uid={self._uid[:8]}>"


class _ProfileProxy:
    """Client-side proxy for a 2D Profile on the view server."""
    # Profiles are currently read-only; we can extend later.

    def __init__(self, uid: str, client: RpcClient):
        object.__setattr__(self, "_uid", uid)
        object.__setattr__(self, "_client", client)

    def __getattr__(self, name):
        return self._client.call("profile_get", self._uid, name)

    def __repr__(self):
        return f"<ProfileProxy uid={self._uid[:8]}>"
