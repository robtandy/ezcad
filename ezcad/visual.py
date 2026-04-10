"""ezcad.visual — global scene visual settings (client proxy)."""

from __future__ import annotations

from typing import Literal

AlphaMode = Literal[
    "auto",
    "blend",
    "add",
    "subtract",
    "multiply",
    "weighted_blend",
    "weighted_solid",
    "dither",
    "bayer",
]

ALPHA_MODES: set[AlphaMode] = {
    "auto",
    "blend",
    "add",
    "subtract",
    "multiply",
    "weighted_blend",
    "weighted_solid",
    "dither",
    "bayer",
}

DEFAULT_ALPHA_MODE: AlphaMode = "auto"


def _client():
    import ezcad

    if ezcad._view is None:
        raise RuntimeError("ezcad.View() not created yet")
    return ezcad._view._client


class _GlobalVisual:
    """Global visual defaults — accessed as ``ezcad.visual``."""

    @property
    def alpha_mode(self) -> AlphaMode:
        """Default alpha mode inherited by all objects (``'auto'``)."""
        return _client().call("visual_get", "visual_alpha_mode")

    @alpha_mode.setter
    def alpha_mode(self, value: AlphaMode) -> None:
        if value not in ALPHA_MODES:
            raise ValueError(f"alpha_mode must be one of {ALPHA_MODES}, got {value!r}")
        _client().call("visual_set", "visual_alpha_mode", value)

    def __repr__(self) -> str:
        return f"<ezcad.visual alpha_mode={self.alpha_mode!r}>"


# Singleton instance
visual = _GlobalVisual()
