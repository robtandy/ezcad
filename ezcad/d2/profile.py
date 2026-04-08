import math
from typing import List, Tuple
import numpy as np
import trimesh


class Profile:
    """A closed 2D shape that can be extruded, revolved, or lofted into 3D."""

    def __init__(self, verts: List[Tuple[float, float]]):
        self.verts = np.array(verts, dtype=float)

    # -- helpers ------------------------------------------------------------------

    @classmethod
    def circle(cls, radius: float = 1.0, segments: int = 64) -> "Profile":
        theta = np.linspace(0, 2 * math.pi, segments, endpoint=False)
        return cls(list(zip(radius * np.cos(theta), radius * np.sin(theta))))

    @classmethod
    def rect(cls, width: float = 1.0, height: float = 1.0) -> "Profile":
        hw, hh = width / 2, height / 2
        return cls([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)])

    @classmethod
    def ngon(cls, radius: float = 1.0, sides: int = 6) -> "Profile":
        theta = np.linspace(0, 2 * math.pi, sides, endpoint=False)
        return cls(list(zip(radius * np.cos(theta), radius * np.sin(theta))))

    @classmethod
    def polygon(cls, verts: List[Tuple[float, float]]) -> "Profile":
        return cls(verts)

    # -- 2d → 3d -----------------------------------------------------------------

    def extrude(self, height: float) -> "Mesh":
        """Extrude this profile along +Z by ``height``."""
        from ezcad.d3 import Mesh

        import shapely
        poly = shapely.geometry.Polygon(self.verts)
        mesh = trimesh.creation.extrude_polygon(poly, height)
        return Mesh(mesh)

    def revolve(
        self,
        angle: float = 2 * math.pi,
        sections: int = 64,
        axis: str = "z",
    ) -> "Mesh":
        """Revolve this profile around the Z axis.

        The profile is treated as lying in the XZ plane (X radius, Z height)
        and revolves about Z, producing a lathe shape.
        """
        from ezcad.d3 import Mesh

        # trimesh.creation.revolve expects a 2D linestring in (x, y),
        # revolving around Y → maps to our X (radius) / Z (height)
        verts = list(self.verts)
        if not np.allclose(verts[0], verts[-1]):
            verts.append(verts[0])
        linestring = np.array(verts)

        mesh = trimesh.creation.revolve(
            linestring, angle=angle, sections=sections
        )
        return Mesh(mesh)

    def _to_2d_vertices(self) -> np.ndarray:
        """Return verts suitable for sectioning into 2D."""
        return self.verts.copy()

    # -- properties ---------------------------------------------------------------

    @property
    def area(self) -> float:
        import shapely
        poly = shapely.geometry.Polygon(self.verts)
        return poly.area

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        import shapely
        poly = shapely.geometry.Polygon(self.verts)
        return poly.bounds  # (minx, miny, maxx, maxy)


# -- module-level constructors ----------------------------------------------------

def circle(radius: float = 1.0, segments: int = 64) -> Profile:
    return Profile.circle(radius=radius, segments=segments)


def rect(width: float = 1.0, height: float = 1.0) -> Profile:
    return Profile.rect(width=width, height=height)


def ngon(radius: float = 1.0, sides: int = 6) -> Profile:
    return Profile.ngon(radius=radius, sides=sides)


def polygon(verts: List[Tuple[float, float]]) -> Profile:
    return Profile.polygon(verts)
