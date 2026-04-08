"""Pie menu: cascading donut rings with icon-only slices.

Callback execution happens entirely in the view process — no
cross-process serialisation of callables is needed.
"""

import math
import numpy as np
import pygfx as gfx
from .d2 import Profile


# ---------------------------------------------------------------------------
# _MenuSpec — lightweight, picklable description of a menu item
# ---------------------------------------------------------------------------

class _MenuSpec:
    """Serialisable description of one pie-menu slice.

    ``icon_verts`` — list of (x, y) points for the icon, or None
    ``action``     — opaque string identifying the handler to call
    ``children``   — list of child _MenuSpec, or None
    """

    def __init__(self, icon=None, action=None, children=None):
        if icon is not None and len(icon.verts) >= 3:
            self.icon_verts = icon.verts.tolist()
        else:
            self.icon_verts = None
        self.action = action or ""
        self.children = (
            [_MenuSpec(**vars(c)._asdict()) for c in children]
            if isinstance(children, list) and len(children)
            else None
        )


# ---------------------------------------------------------------------------
# PieMenu (view-side renderer + interaction handler)
# ---------------------------------------------------------------------------

class PieMenu:
    """Screen-space cascading pie / donut menu.

    All rings share the same centre.  Ring 0 appears on request.
    Hovering a slice of ring *N* reveals ring *N+1* outside it.
    The currently hovered slot is highlighted in gold.
    """

    RING_W       = 55.0    # radial thickness per ring (screen px)
    SLICE_GAP    = 0.03    # rad gap between slices
    ICON_SCALE   = 0.45    # icon profile scale factor
    RING1_INNER  = 30.0    # inner radius of first ring
    SEG_PER_RAD  = 10

    def __init__(self, actions: dict):
        """
        Parameters
        ----------
        actions : dict
            Maps action-name (str) → callable ``(x, y, shape_or_None)``.
        """
        self.actions = actions

        self.open = False
        self.center = (0.0, 0.0)
        self.scene: gfx.Scene | None = None
        self.group: gfx.Group | None = None
        self._specs = []            # list of _MenuSpec
        self._wedges: list[gfx.Mesh] = []
        self._icons: list[gfx.Mesh] = []
        self.hover_path: list[int] = []

    # ---- public API -------------------------------------------------------

    def open_at(self, x: float, y: float, scene: gfx.Scene,
                specs: list[_MenuSpec]):
        self.open = True
        self.center = (x, y)
        self.scene = scene
        self.group = gfx.Group()
        scene.add(self.group)
        self._specs = specs
        self.hover_path = [-1]
        self._rebuild()

    def close(self):
        if self.group and self.scene:
            self.scene.remove(self.group)
        self.group = None
        self.scene = None
        self._specs.clear()
        self._wedges.clear()
        self._icons.clear()
        self.hover_path.clear()
        self.open = False

    def handle_mouse(self, x: float, y: float):
        """Update hover highlight from cursor position."""
        if not self.open:
            return
        path = self._path_for_point(x, y)
        if path is not None:
            self.hover_path = path
            self._rebuild()

    def handle_click(self, x: float, y: float) -> bool:
        """If a leaf action is under the cursor, fire it and return True."""
        if not self.open:
            return False
        path = self._path_for_point(x, y)
        if not path:
            self.close()
            return True
        specs = self._specs
        for idx in path:
            if idx < 0 or idx >= len(specs):
                self.close()
                return True
            spec = specs[idx]
            has_children = spec.children and len(spec.children) > 0
            if not has_children and spec.action:
                handler = self.actions.get(spec.action)
                if handler:
                    handler(x, y, None)   # shape resolved via pick on demand
                    self.close()
                    return True
            specs = spec.children or []
        self.close()
        return True

    # ---- internals --------------------------------------------------------

    def _path_for_point(self, x: float, y: float) -> list[int] | None:
        """Walk from ring 0 outward; return ring indices at (x, y) or None."""
        dx = x - self.center[0]
        dy = y - self.center[1]
        dist = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        specs = self._specs
        result = []
        for ri in range(20):
            if not specs:
                break
            r_inner = self.RING1_INNER + ri * self.RING_W
            r_outer = r_inner + self.RING_W
            if dist < r_inner or dist > r_outer:
                break
            n = len(specs)
            a = angle if angle >= 0 else angle + 2 * math.pi
            idx = int(a / (2 * math.pi / n)) % n
            result.append(idx)
            specs = specs[idx].children or []
        return result or None

    def _rebuild(self):
        for m in self._wedges:
            self.group.remove(m)
        for m in self._icons:
            self.group.remove(m)
        self._wedges.clear()
        self._icons.clear()

        specs = self._specs
        for ri, hl_idx in enumerate(self.hover_path):
            if not specs:
                break
            r_inner = self.RING1_INNER + ri * self.RING_W
            n = len(specs)
            slice_angle = (2 * math.pi) / n
            for i, spec in enumerate(specs):
                a_start = i * slice_angle
                a_end = (i + 1) * slice_angle
                color = "#FFB800" if i == hl_idx else "#444466"
                wedge = self._wedge(r_inner, a_start, a_end, color)
                self.group.add(wedge)
                self._wedges.append(wedge)
                if spec.icon_verts is not None:
                    a_mid = (a_start + a_end) / 2
                    r_mid = r_inner + self.RING_W / 2
                    icon = self._icon(spec.icon_verts, a_mid, r_mid)
                    self.group.add(icon)
                    self._icons.append(icon)
            # next ring
            if 0 <= hl_idx < len(specs):
                specs = specs[hl_idx].children or []
            else:
                break

    def _wedge(self, r_inner, a_start, a_end, color):
        seg = max(3, int((a_end - a_start) * self.SEG_PER_RAD))
        angles = np.linspace(
            a_start + self.SLICE_GAP / 2,
            a_end - self.SLICE_GAP / 2,
            seg,
        )
        r_outer = r_inner + self.RING_W
        verts = []
        for a in angles:
            verts.append([r_inner * math.cos(a), r_inner * math.sin(a), 0])
        for a in reversed(angles):
            verts.append([r_outer * math.cos(a), r_outer * math.sin(a), 0])
        positions = np.array(verts, dtype=np.float32)
        n = len(angles)
        indices = []
        for i in range(n - 1):
            i0, i1 = i, i + 1
            o0, o1 = 2 * n - 1 - i, 2 * n - 2 - i
            indices.extend([i0, o0, i1, i1, o0, o1])
        geo = gfx.Geometry(
            positions=positions,
            indices=np.array(indices, dtype=np.uint32),
        )
        return gfx.Mesh(geo, gfx.MeshBasicMaterial(color=color, side="front"))

    def _icon(self, verts_xy, angle, radius):
        v = np.array(verts_xy) * self.ICON_SCALE
        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)
        icon_verts = np.column_stack([
            v[:, 0] + cx,
            v[:, 1] + cy,
            np.zeros(len(v), dtype=np.float32),
        ])
        ic = []
        for i in range(1, len(icon_verts) - 1):
            ic.extend([0, i, i + 1])
        geo = gfx.Geometry(
            positions=icon_verts,
            indices=np.array(ic, dtype=np.uint32),
        )
        return gfx.Mesh(geo, gfx.MeshBasicMaterial(color="#D0D0D0", side="both"))
