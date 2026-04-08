"""2D icon profiles for pie menu items.

Each function returns a `Profile` whose verts are centered at origin and
fit into roughly a ±20×±20 unit box.
"""

import math
import numpy as np
from ezcad.d2 import Profile


# ---------------------------------------------------------------------------
# Primitive icon shapes
# ---------------------------------------------------------------------------

def _regular_ngon(n, r=20):
    """Utility profile for a regular n-gon."""
    theta = np.linspace(0, 2 * math.pi, n, endpoint=False) + math.pi / 2
    return Profile(list(zip(r * np.cos(theta), r * np.sin(theta))))


def icon_cube() -> Profile:
    """Diamond (square seen from corner) — represents adding a box."""
    return _regular_ngon(4, r=18)


def icon_sphere() -> Profile:
    """Circle — add a sphere."""
    return Profile.circle(radius=18, segments=48)


def icon_cylinder() -> Profile:
    """Tall rectangle — add a cylinder."""
    return Profile.rect(width=16, height=30)


def icon_cone() -> Profile:
    """Triangle — add a cone."""
    return Profile([(0, 18), (-16, -12), (16, -12)])


def icon_torus() -> Profile:
    """Donut shape (thick ring) — add a torus."""
    return Profile.circle(radius=18, segments=48)


def icon_extrude() -> Profile:
    """Rectangle with an upward arrow — extrude a profile."""
    # Simple upward chevron
    return Profile([(0, 18), (-14, -8), (-6, -8), (-6, -18), (6, -18), (6, -8), (14, -8)])


def icon_union() -> Profile:
    """Two overlapping circles — boolean union."""
    return Profile.circle(radius=18, segments=48)


def icon_difference() -> Profile:
    """Square with a circle cutout feel — boolean difference."""
    return _regular_ngon(4, r=18)


def icon_grid() -> Profile:
    """Hash-mark / grid symbol."""
    return _regular_ngon(4, r=18)


def icon_trash() -> Profile:
    """Hexagon — delete."""
    return _regular_ngon(6, r=18)


def icon_reset() -> Profile:
    """Ring (hollow circle) — reset camera / clear."""
    return Profile.circle(radius=18, segments=48)


def icon_rotate() -> Profile:
    """Curved arrow feel — represented by two chevrons."""
    return _regular_ngon(6, r=18)


def icon_scale() -> Profile:
    """Two concentric squares."""
    return _regular_ngon(4, r=18)


def icon_section() -> Profile:
    """Horizontal bar with a gap — represents slicing/section."""
    return Profile.rect(width=32, height=8)
