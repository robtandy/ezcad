"""Tests for Profile (d2) and Mesh/Shape (d3) geometric functionality.

No viewer tests — just pure geometry validation via trimesh / shapely.
"""

import math
import pytest
import numpy as np
import trimesh

from ezcad.d2.profile import Profile, circle, rect, ngon, polygon
from ezcad.d3.shape import Mesh, box, sphere, cylinder, cone, torus


# ─────────── Profile construction ─────────────────────────────────────────────

class TestProfileConstruction:
    def test_raw_verts(self):
        p = Profile([(0, 0), (1, 0), (1, 1)])
        assert p.verts.shape == (3, 2)
        assert np.array_equal(p.verts[0], [0, 0])

    def test_circle_defaults(self):
        p = Profile.circle()
        assert p.verts.shape[0] == 64
        # Radius 1: distance from center to any vertex should be ~1
        dists = np.sqrt(p.verts[:, 0]**2 + p.verts[:, 1]**2)
        assert np.allclose(dists, 1.0)

    def test_circle_custom(self):
        p = Profile.circle(radius=3.0, segments=32)
        assert p.verts.shape[0] == 32
        dists = np.sqrt(p.verts[:, 0]**2 + p.verts[:, 1]**2)
        assert np.allclose(dists, 3.0)

    def test_rect_origin(self):
        p = Profile.rect(width=4, height=2)
        expected = [(-2, -1), (2, -1), (2, 1), (-2, 1)]
        assert np.allclose(p.verts, expected)

    def test_ngon_hex(self):
        p = Profile.ngon(radius=1.0, sides=6)
        assert p.verts.shape[0] == 6
        dists = np.sqrt(p.verts[:, 0]**2 + p.verts[:, 1]**2)
        assert np.allclose(dists, 1.0)

    def test_polygon_passthrough(self):
        verts = [(0, 0), (5, 0), (5, 3), (0, 3)]
        p = Profile.polygon(verts)
        assert len(p.verts) == 4

    # Module-level constructors
    def test_circle_fn(self):
        p = circle(radius=2.0)
        assert isinstance(p, Profile)

    def test_rect_fn(self):
        p = rect(width=3, height=5)
        assert isinstance(p, Profile)

    def test_ngon_fn(self):
        p = ngon(radius=1, sides=8)
        assert p.verts.shape[0] == 8

    def test_polygon_fn(self):
        p = polygon([(0, 0), (1, 0), (0, 1)])
        assert isinstance(p, Profile)


# ─────────── Profile properties ─────────────────────────────────────────────

class TestProfileProperties:
    def test_rect_area(self):
        p = Profile.rect(width=4, height=3)
        assert math.isclose(p.area, 12.0, rel_tol=1e-6)

    def test_circle_area(self):
        p = Profile.circle(radius=2.0, segments=128)
        # 128-segment polygon approximation — within 0.1%% of true circle
        assert math.isclose(p.area, math.pi * 4.0, rel_tol=1e-3)

    def test_circle_bounds(self):
        p = Profile.circle(radius=3.0, segments=64)
        minx, miny, maxx, maxy = p.bounds
        # With 64 segments the bounds are very close to ±3
        assert math.isclose(minx, -3.0, abs_tol=0.1)
        assert math.isclose(maxx, 3.0, abs_tol=0.1)
        assert math.isclose(miny, -3.0, abs_tol=0.1)
        assert math.isclose(maxy, 3.0, abs_tol=0.1)


# ─────────── Profile → Mesh (extrude / revolve) ─────────────────────────────

class TestProfileExtrude:
    def test_extrude_rect_volume(self):
        p = Profile.rect(width=2, height=3)
        m = p.extrude(height=5.0)
        assert isinstance(m, Mesh)
        assert math.isclose(m.volume, 30.0, rel_tol=1e-5)

    def test_extrude_circle_volume(self):
        p = Profile.circle(radius=1.0, segments=64)
        m = p.extrude(height=2.0)
        expected = math.pi * 1.0**2 * 2.0
        assert math.isclose(m.volume, expected, rel_tol=1e-2)

    def test_extrude_preserves_watertight(self):
        p = Profile.rect(width=4, height=4)
        m = p.extrude(height=1.0)
        assert m._mesh.is_watertight


class TestProfileRevolve:
    def test_revolve_ring_volume(self):
        """Revolve a circle offset from origin → torus-like.
        
        trimesh.creation.revolve treats the profile as (x,y) coordinates
        and revolves around the Y axis, creating a lathe shape.
        """
        # A small circle at x=2, y=0 — revolve makes a torus
        # We need a non-self-intersecting profile: use two vertical arcs
        # Simpler: just use a rectangle offset from origin
        p = Profile.rect(width=0.4, height=1.0)
        # Shift it so it's centered at x=3, y=0 (offset of 3 in x)
        shifted = [(x + 3.0, y) for x, y in p.verts]
        p_shifted = Profile(shifted)
        
        m = p_shifted.revolve(angle=2 * math.pi, sections=64)
        assert isinstance(m, Mesh)
        assert m.volume > 0
        assert m._mesh.is_watertight


# ─────────── Mesh construction ─────────────────────────────────────────────

class TestMeshConstruction:
    def test_box_volume(self):
        m = box([10, 10, 10])
        assert math.isclose(m.volume, 1000.0)

    def test_sphere_volume(self):
        m = sphere(radius=1.0)
        expected = (4 / 3) * math.pi
        assert math.isclose(m.volume, expected, rel_tol=0.05)

    def test_cylinder_volume(self):
        m = cylinder(radius=1.0, height=2.0)
        expected = math.pi * 1.0**2 * 2.0
        assert math.isclose(m.volume, expected, rel_tol=0.05)

    def test_cone_volume(self):
        m = cone(radius=1.0, height=3.0)
        expected = (1 / 3) * math.pi * 1.0**2 * 3.0
        assert math.isclose(m.volume, expected, rel_tol=0.05)

    def test_torus_volume(self):
        R, r = 3.0, 0.5
        m = torus(major_radius=R, minor_radius=r)
        expected = (2 * math.pi * R) * (math.pi * r**2)
        assert math.isclose(m.volume, expected, rel_tol=0.1)

    def test_uuid_unique(self):
        m1 = box([2, 2, 2])
        m2 = box([2, 2, 2])
        assert m1.uuid != m2.uuid

    def test_initial_state(self):
        m = box([1, 1, 1])
        assert m.pos == [0.0, 0.0, 0.0]
        assert m.visible is True
        assert m.color == "#336699"


# ─────────── Mesh transforms ─────────────────────────────────────────────

class TestMeshTranslate:
    def test_translate_updates_pos(self):
        m = box([1, 1, 1])
        m.translate([1, 2, 3])
        assert m.pos == [1.0, 2.0, 3.0]

    def test_translate_accumulates(self):
        m = box([1, 1, 1])
        m.translate([1, 0, 0])
        m.translate([0, 2, 0])
        assert m.pos == [1.0, 2.0, 0.0]

    def test_translate_chains(self):
        m = box([1, 1, 1])
        result = m.translate([5, 0, 0])
        assert result is m

    def test_translate_changes_bounds(self):
        m = box([2, 2, 2])
        bb_before = m._mesh.bounds.copy()
        m.translate([10, 10, 10])
        bb_after = m._mesh.bounds
        assert not np.allclose(bb_before, bb_after)


class TestMeshRotate:
    def test_rotate_degrees(self):
        m = box([2, 1, 1])
        m.rotate("z", degrees=90)
        # After 90° Z rotation, the long axis (X) maps to Y
        bb = m._mesh.bounds
        x_range = abs(bb[1][0] - bb[0][0])
        y_range = abs(bb[1][1] - bb[0][1])
        assert x_range < 1.1  # was 2, now ~1
        assert y_range > 1.9  # was 1, now ~2

    def test_rotate_radians(self):
        m = box([2, 1, 1])
        m.rotate("z", radians=math.pi / 2)
        bb = m._mesh.bounds
        y_range = abs(bb[1][1] - bb[0][1])
        assert y_range > 1.9

    def test_rotate_custom_axis(self):
        m = box([1, 1, 1])
        result = m.rotate([0, 1, 0], degrees=45)
        assert result is m

    def test_rotate_preserves_volume(self):
        m = box([2, 3, 4])
        vol_before = m.volume
        m.rotate("x", degrees=30)
        m.rotate("y", degrees=60)
        assert math.isclose(m.volume, vol_before)


class TestMeshScale:
    def test_scale_uniform(self):
        m = box([2, 2, 2])
        m.scale(2.0)
        assert math.isclose(m.volume, 64.0)  # 2*2=4 per axis, 4^3=64

    def test_scale_ansi(self):
        m = box([2, 2, 2])
        m.scale([1, 2, 3])
        assert math.isclose(m.volume, 48.0)  # 2*4*6=48

    def test_scale_chains(self):
        m = box([1, 1, 1])
        result = m.scale(0.5)
        assert result is m


class TestMeshMirror:
    def test_mirror_xy(self):
        m = box([1, 1, 1])
        m.translate([0, 0, 5])
        m.mirror("xy")
        bb = m._mesh.bounds
        assert bb[1][2] < 0  # should be below origin

    def test_mirror_yz(self):
        m = box([1, 1, 1])
        m.translate([5, 0, 0])
        m.mirror("yz")
        bb = m._mesh.bounds
        assert bb[1][0] < 0  # should be negative X

    def test_mirror_chains(self):
        m = box([1, 1, 1])
        result = m.mirror("xz")
        assert result is m


# ─────────── Mesh CSG ────────────────────────────────────────────────────

class TestMeshCSG:
    def test_difference_reduces_volume(self):
        outer = box([10, 10, 10])
        inner = box([2, 2, 2])
        vol_before = outer.volume
        outer.difference(inner)
        assert outer.volume < vol_before

    def test_union_increases_volume(self):
        a = box([10, 10, 10])
        b = box([10, 10, 10])
        b.translate([8, 0, 0])
        vol_combined = a.volume + b.volume
        a.union(b)
        assert a.volume < vol_combined  # overlap reduces total
        assert a.volume > a.volume / 2   # still has volume

    def test_intersection_reduces_volume(self):
        a = box([10, 10, 10])
        b = box([6, 6, 6])
        b.translate([2, 0, 0])
        a.intersection(b)
        assert a.volume > 0
        assert a.volume < 1000

    def test_csg_chains(self):
        a = box([10, 10, 10])
        b = box([2, 2, 2])
        result = a.difference(b)
        assert result is a

    def test_difference_hole(self):
        """Subtracting a cylinder from a box should create a hole."""
        block = box([10, 10, 1])
        hole = cylinder(radius=2, height=2)
        vol_before = block.volume
        block.difference(hole)
        assert block.volume < vol_before
        assert block.volume > 0


# ─────────── Mesh section ─────────────────────────────────────────────

class TestMeshSection:
    def test_section_cube(self):
        m = box([10, 10, 10])
        p = m.section(plane="z", value=0.0)
        assert isinstance(p, Profile)
        # Cross-section of a 10x10x10 cube at center should be a 10x10 square
        assert math.isclose(p.area, 100.0, rel_tol=1e-3)

    def test_section_sphere(self):
        m = sphere(radius=5.0)
        p = m.section(plane="z", value=0.0)
        # Great circle of radius ~5
        assert math.isclose(p.area, math.pi * 25, rel_tol=0.1)

    def test_section_off_center(self):
        m = sphere(radius=5.0)
        p1 = m.section(plane="z", value=0.0)
        p2 = m.section(plane="z", value=4.0)
        assert p1.area > p2.area

    def test_section_miss(self):
        m = box([2, 2, 2])
        # Section far outside the mesh should return empty profile
        p = m._mesh.section(
            plane_origin=[0, 0, 100], plane_normal=[0, 0, 1]
        )
        assert p is None


# ─────────── Mesh properties ──────────────────────────────────────────────

class TestMeshProperties:
    def test_volume(self):
        m = box([2, 3, 4])
        assert math.isclose(m.volume, 24.0)

    def test_area(self):
        m = box([1, 1, 1])
        expected = 6.0  # 6 faces of unit area
        assert math.isclose(m.area, expected, rel_tol=1e-3)

    def test_mass(self):
        m = box([2, 2, 2])
        assert math.isclose(m.mass(density=2.0), 16.0)

    def test_bounds(self):
        m = box([10, 10, 10])
        bb = m.bounds()
        assert len(bb) == 2
        # Check extent
        extent = [bb[1][i] - bb[0][i] for i in range(3)]
        assert all(math.isclose(e, 10.0) for e in extent)


# ─────────── Frozen batching ──────────────────────────────────────────────

class TestFrozenBatching:
    def test_frozen_collects_cmds(self):
        m = box([1, 1, 1])
        fake_queue = []
        m._view = type("FakeView", (), {"queue": type("Q", (), {"put": lambda s, x: fake_queue.append(x)})()})()

        with m.frozen():
            for i in range(5):
                m.rotate("z", degrees=1)

        assert len(fake_queue) == 5  # 5 commands were flushed

    def test_frozen_clears_after(self):
        m = box([1, 1, 1])
        fake_queue = []
        m._view = type("FakeView", (), {"queue": type("Q", (), {"put": lambda s, x: fake_queue.append(x)})()})()

        with m.frozen():
            m.scale(2)

        assert len(fake_queue) == 1
        fake_queue.clear()

        # After context exits, mesh is no longer frozen
        m.rotate("z", degrees=10)
        assert len(fake_queue) == 1  # immediate send

    def test_no_view_no_error(self):
        m = box([1, 1, 1])
        assert m._view is None
        # Should not raise even without a viewer
        with m.frozen():
            m.scale(2.0)
            m.rotate("z", 45)


# ─────────── Edge cases ───────────────────────────────────────────────────

class TestEdgeCases:
    def test_chain_many_operations(self):
        m = box([5, 5, 5])
        m.translate([10, 0, 0]).rotate("z", 45).scale(0.5)
        assert m.pos == [10.0, 0.0, 0.0]

    def test_negative_scale(self):
        m = box([1, 1, 1])
        vol_before = abs(m.volume)
        m.scale([-1, 1, 1])
        # Neg scale flips normals, volume sign may change
        assert math.isclose(abs(m.volume), vol_before)

    def test_rotate_zero(self):
        m = box([1, 1, 1])
        v_before = m._mesh.vertices.copy()
        m.rotate("z", degrees=0)
        assert np.allclose(m._mesh.vertices, v_before)

    def test_box_with_list(self):
        m = box([3, 4, 5])
        assert math.isclose(m.volume, 60.0)
