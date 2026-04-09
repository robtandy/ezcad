"""ezcad.d2 — thin client-side Profile proxies."""

from ezcad.rpc import RpcClient


def _client() -> RpcClient:
    import ezcad
    if ezcad._view is None:
        raise RuntimeError("ezcad.View() not created yet")
    return ezcad._view._client


class Profile:
    def __init__(self, uid: str):
        self._uid = uid

    def __getattr__(self, name):
        return _client().call("profile_get", self._uid, name)

    def __repr__(self):
        return f"<d2.Profile uid={self._uid}>"


def circle(radius=1.0, segments=64) -> Profile:
    uid = _client().call("make_circle", radius, segments)
    return Profile(uid)


def rect(width=1.0, height=1.0) -> Profile:
    uid = _client().call("make_rect", width, height)
    return Profile(uid)


def ngon(radius=1.0, sides=6) -> Profile:
    uid = _client().call("make_ngon", radius, sides)
    return Profile(uid)
