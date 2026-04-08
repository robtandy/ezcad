"""Pie menu: cascading donut rings with icon-only slices.

Usage::

    menu = PieMenu()
    menu.add_item(Shape.icon_cube, callback=on_add_box)
    menu.add_item(Shape.icon_sphere, callback=on_add_sphere)
    sub = menu.add_submenu(Shape.icon_rotate)
    sub.add_item(Shape.icon_rotate, callback=on_rotate_x)
    sub.add_item(Shape.icon_scale, callback=on_scale_y)
    # …
    view.register_menu(menu)
"""

import math
import uuid
import numpy as np
import pygfx as gfx
from .d2 import Profile


# ---------------------------------------------------------------------------
# MenuItem  (main-process side, holds the real callback)
# ---------------------------------------------------------------------------

class MenuItem:
    """A node in the pie menu tree.

    ``icon``     – Profile drawn in the slice centre
    ``children`` – sub-menu items (creates the next concentric ring)
    ``callback`` – fires on leaf click, receives ``(x, y, hit_shape)``
    """

    _registry: dict[str, "MenuItem"] = {}

    def __init__(self, icon: Profile | None = None,
                 children: list["MenuItem"] | None = None,
                 callback=None):
        self.id = str(uuid.uuid4())
        self.icon = icon
        self.children = children or []
        self.callback = callback
        MenuItem._registry[self.id] = self

    @classmethod
    def by_id(cls, mid: str):
        return cls._registry.get(mid)


# ---------------------------------------------------------------------------
# _ItemSpec (lightweight, picklable description sent to the view)
# ---------------------------------------------------------------------------

class _ItemSpec:
    """Serialisable description of a MenuItem for IPC."""

    def __init__(self, item: MenuItem):
        self.id = item.id
        # serialise icon profile as raw (x, y) vertices, or None
        if item.icon is not None and len(item.icon.verts) >= 3:
            self.icon_verts = item.icon.verts.tolist()
        else:
            self.icon_verts = None
        self.has_children = bool(item.children)
        self.children = [_ItemSpec(c) for c in item.children]


# ---------------------------------------------------------------------------
# PieMenu (view-side renderer + interaction)
# ---------------------------------------------------------------------------

class PieMenu:
    """Screen-space cascading pie / donut menu.

    All rings share the same centre.  Ring 0 appears on right-click.
    Hovering a slice of ring *N* reveals ring *N+1* outside it.
    The currently hovered slot is highlighted in gold.
    """

    RING_W       = 55.0    # radial thickness per ring (screen px)
    SLICE_GAP    = 0.03    # rad gap between slices
    ICON_SCALE   = 0.45    # icon profile scale factor
    RING1_INNER  = 30.0    # inner radius of first ring
    SEG_PER_RAD  = 10

    def __init__(self):
        self.open = False
        self.center = (0.0, 0.0)
        self.scene: gfx.Scene | None = None
        self.group: gfx.Group | None = None
        # items: list of  (_ItemSpec,  child_item_specs_or_None)
        self._items: list[tuple[_ItemSpec, list[_ItemSpec] | None]] = []
        self._wedges: list[gfx.Mesh] = []
        self._icons: list[gfx.Mesh] = []
        self.hover_path: list[int] = []     # ring_i → selected index

    # ---- public API -------------------------------------------------------

    def open_at(self, x: float, y: float, scene: gfx.Scene,
                items: list[_ItemSpec]):
        self.open = True
        self.center = (x, y)
        self.scene = scene
        self.group = gfx.Group()
        scene.add(self.group)
        self._items = [(spec, spec.children or None) for spec in items]
        self.hover_path = [-1]
        self._rebuild()

    def close(self):
        if self.group and self.scene:
            self.scene.remove(self.group)
        self.group = None
        self.scene = None
        self._items.clear()
        self._wedges.clear()
        self._icons.clear()
        self.hover_path.clear()
        self.open = False

    def handle_mouse(self, x: float, y: float):
        if not self.open:
            return
        path = self._path_for_point(x, y)
        if path is not None:
            self.hover_path = path
            self._rebuild()

    def handle_click(self, x: float, y: float) -> str | None:
        """Return the MenuItem.id of a leaf under (x, y), or None."""
        if not self.open:
            return None
        path = self._path_for_point(x, y)
        if not path:
            return None
        specs = self._items
        leaf_id = None
        for idx in path:
            if idx < 0 or idx >= len(specs):
                break
            spec, children = specs[idx]
            if not spec.has_children:
                leaf_id = spec.id
            specs = children or []
        return leaf_id

    # ---- internals --------------------------------------------------------

    def _path_for_point(self, x: float, y: float) -> list[int] | None:
        dx = x - self.center[0]
        dy = y - self.center[1]
        dist = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        specs = self._items
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
            specs = specs[idx][1] or []
        return result or None

    def _rebuild(self):
        for m in self._wedges:
            self.group.remove(m)
        for m in self._icons:
            self.group.remove(m)
        self._wedges.clear()
        self._icons.clear()

        items = self._items
        for ri, hl_idx in enumerate(self.hover_path):
            if not items:
                break
            r_inner = self.RING1_INNER + ri * self.RING_W
            n = len(items)
            slice_angle = (2 * math.pi) / n
            for i, (spec, _) in enumerate(items):
                a_start = i * slice_angle
                a_end = (i + 1) * slice_angle
                color = "#FFB800" if i == hl_idx else "#444466"
                wedge = self._wedge(r_inner, a_start, a_end, color)
                self.group.add(wedge)
                self._wedges.append(wedge)
                if spec.icon_verts is not None:
                    a_mid = (a_start + a_end) / 2
                    r_mid = r_inner + self.RING_W / 2
                    icon = self._icon_from_verts(spec.icon_verts, a_mid, r_mid)
                    self.group.add(icon)
                    self._icons.append(icon)
            # next ring
            next_specs = None
            if 0 <= hl_idx < len(items):
                next_specs = items[hl_idx][1]
            items = next_specs or []

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

    def _icon_from_verts(self, verts_xy, angle, radius):
        """Build an icon gfx.Mesh from raw [[x, y], …] data."""
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
