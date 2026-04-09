"""PieMenu — screen-space donut rings, server-side only."""

import math
import numpy as np
import pygfx as gfx


class _MenuSpec:
    def __init__(self, icon_verts=None, children=None):
        self.icon_verts = icon_verts
        self.children = children or None


class PieMenu:
    RING_W = 55.0; SLICE_GAP = 0.03; ICON_SCALE = 0.45
    RING1_INNER = 30.0; SEG_PER_RAD = 10

    def __init__(self):
        self.open = False; self.center = (0.0, 0.0)
        self.scene = None; self.group = None
        self._specs = []; self._wedges = []; self._icons = []
        self.hover_path = []

    def open_at(self, x, y, scene, specs):
        self.close()
        self.open = True; self.center = (x, y); self.scene = scene
        self.group = gfx.Group(); scene.add(self.group)
        self._specs = specs; self.hover_path = [-1]; self._rebuild()

    def close(self):
        if self.group and self.scene:
            self.scene.remove(self.group)
        self.group = None; self.scene = None
        self._specs.clear(); self._wedges.clear(); self._icons.clear()
        self.hover_path.clear(); self.open = False

    def handle_mouse(self, x, y):
        if not self.open: return
        path = self._path_for(x, y)
        if path: self.hover_path = path; self._rebuild()

    def handle_click(self, x, y):
        path = self._path_for(x, y); self.close(); return path is not None

    def _path_for(self, x, y):
        dx, dy = x - self.center[0], y - self.center[1]
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        specs = self._specs; result = []
        for ri in range(20):
            if not specs: break
            r_i = self.RING1_INNER + ri * self.RING_W; r_o = r_i + self.RING_W
            if dist < r_i or dist > r_o: break
            n = len(specs); a = angle if angle >= 0 else angle + 2 * math.pi
            idx = int(a / (2 * math.pi / n)) % n
            result.append(idx); specs = specs[idx].children or []
        return result or None

    def _rebuild(self):
        for m in self._wedges: self.group.remove(m)
        for m in self._icons: self.group.remove(m)
        self._wedges.clear(); self._icons.clear()
        specs = self._specs
        for ri, hl in enumerate(self.hover_path):
            if not specs: break
            r_i = self.RING1_INNER + ri * self.RING_W; n = len(specs)
            sa = (2 * math.pi) / n
            for i, sp in enumerate(specs):
                a_s, a_e = i * sa, (i + 1) * sa
                c = "#FFB800" if i == hl else "#444466"
                w = self._wedge(r_i, a_s, a_e, c)
                self.group.add(w); self._wedges.append(w)
                if sp.icon_verts is not None:
                    a_m = (a_s + a_e) / 2; r_m = r_i + self.RING_W / 2
                    ic = self._icon(sp.icon_verts, a_m, r_m)
                    self.group.add(ic); self._icons.append(ic)
            specs = specs[hl].children if (0 <= hl < len(specs)) else []

    def _wedge(self, ri, a_s, a_e, color):
        seg = max(3, int((a_e - a_s) * self.SEG_PER_RAD))
        angles = np.linspace(a_s + self.SLICE_GAP / 2, a_e - self.SLICE_GAP / 2, seg)
        ro = ri + self.RING_W
        v = []
        for a in angles: v.append([ri*math.cos(a), ri*math.sin(a), 0])
        for a in reversed(angles): v.append([ro*math.cos(a), ro*math.sin(a), 0])
        pos = np.array(v, dtype=np.float32); n = len(angles)
        idx = []
        for i in range(n - 1):
            idx.extend([i, 2*n-1-i, i+1, i+1, 2*n-1-i, 2*n-2-i])
        return gfx.Mesh(gfx.Geometry(positions=pos, indices=np.array(idx, dtype=np.uint32)),
                        gfx.MeshBasicMaterial(color=color, side="front"))

    def _icon(self, verts_xy, angle, radius):
        v = np.array(verts_xy, dtype=np.float32) * self.ICON_SCALE
        cx, cy = radius*math.cos(angle), radius*math.sin(angle)
        iv = np.column_stack([v[:, 0]+cx, v[:, 1]+cy, np.zeros(len(v), dtype=np.float32)])
        ic = []
        for i in range(1, len(iv)-1): ic.extend([0, i, i+1])
        return gfx.Mesh(gfx.Geometry(positions=iv, indices=np.array(ic, dtype=np.uint32)),
                        gfx.MeshBasicMaterial(color="#D0D0D0", side="both"))
