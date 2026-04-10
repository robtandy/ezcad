from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Viewable:
    uid: str
    positions: list[list[float]] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)
    normals: list[float] = field(default_factory=list)
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    visible: bool = True
    color: tuple[float, float, float, float] = (0.13, 0.26, 0.52, 0.5)
    visual_alpha_mode: str | None = None
