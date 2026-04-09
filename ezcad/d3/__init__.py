"""ezcad.d3 — thin client-side Mesh proxies."""

from ezcad.rpc import RpcClient


def _client() -> RpcClient:
    import ezcad
    if ezcad._view is None:
        raise RuntimeError("ezcad.View() not created yet")
    return ezcad._view._client


class Mesh:
    """Client proxy — all access goes through RPC."""

    def __init__(self, uid: str):
        self._uid = uid

    def __getattr__(self, name):
        return _client().call("mesh_get", self._uid, name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            _client().call("mesh_set", self._uid, name, value)

    # -- chainable transforms --

    def translate(self, vec):
        _client().call("mesh_call", self._uid, "translate", [vec], {})
        return self

    def rotate(self, axis, degrees=0, radians=0):
        _client().call("mesh_call", self._uid, "rotate",
                       [axis], {"degrees": degrees, "radians": radians})
        return self

    def scale(self, factor):
        _client().call("mesh_call", self._uid, "scale", [factor], {})
        return self

    def mirror(self, plane="xy"):
        _client().call("mesh_call", self._uid, "mirror", [plane], {})
        return self

    # -- CSG --

    def union(self, other: "Mesh"):
        _client().call("mesh_call", self._uid, "union", [other._uid], {})
        return self

    def difference(self, other: "Mesh"):
        _client().call("mesh_call", self._uid, "difference", [other._uid], {})
        return self

    def intersection(self, other: "Mesh"):
        _client().call("mesh_call", self._uid, "intersection", [other._uid], {})
        return self

    def section(self, plane="z", value=0.0):
        return _client().call("mesh_call", self._uid, "section",
                              [], {"plane": plane, "value": value})

    def __repr__(self):
        return f"<d3.Mesh uid={self._uid}>"


# -- factory functions (all objects visible on creation) --

def box(extents) -> Mesh:
    uid = _client().call("make_box", extents)
    return Mesh(uid)


def sphere(radius=1.0) -> Mesh:
    uid = _client().call("make_sphere", radius)
    return Mesh(uid)


def cylinder(radius=1.0, height=1.0) -> Mesh:
    uid = _client().call("make_cylinder", radius, height)
    return Mesh(uid)


def cone(radius=1.0, height=1.0) -> Mesh:
    uid = _client().call("make_cone", radius, height)
    return Mesh(uid)


def torus(major_radius=1.0, minor_radius=0.25) -> Mesh:
    uid = _client().call("make_torus", major_radius, minor_radius)
    return Mesh(uid)
