"""Tests for the new client/server proxy architecture."""

import pytest
import time
from ezcad.view import View


@pytest.fixture(scope="module")
def v():
    view = View()
    yield view
    view.close()


class TestProxyCreation:
    def test_box_proxy(self, v):
        b = v.box([2, 3, 4])
        assert b is not None
        pos = b.pos  # RPC call
        assert pos == [0.0, 0.0, 0.0]

    def test_sphere_proxy(self, v):
        s = v.sphere(radius=1.0)
        assert s.volume > 0

    def test_cylinder_proxy(self, v):
        c = v.cylinder(radius=1.0, height=2.0)
        assert c.volume > 0

    def test_cone_proxy(self, v):
        c = v.cone(radius=1.0, height=3.0)
        assert c.volume > 0

    def test_torus_proxy(self, v):
        t = v.torus(major_radius=2.0, minor_radius=0.5)
        assert t.volume > 0


class TestProxyProperties:
    def test_pos_initial(self, v):
        b = v.box([1, 1, 1])
        assert b.pos == [0.0, 0.0, 0.0]

    def test_visible_initial(self, v):
        b = v.box([1, 1, 1])
        assert b.visible is True

    def test_color_initial(self, v):
        b = v.box([1, 1, 1])
        assert b.color == "#336699"

    def test_volume(self, v):
        b = v.box([2, 3, 4])
        assert abs(b.volume - 24.0) < 0.01

    def test_area(self, v):
        b = v.box([1, 1, 1])
        assert abs(b.area - 6.0) < 0.01


class TestProxyTransforms:
    def test_translate(self, v):
        b = v.box([1, 1, 1])
        b.translate([1, 2, 3])
        assert b.pos == [1.0, 2.0, 3.0]

    def test_translate_chains(self, v):
        b = v.box([1, 1, 1])
        result = b.translate([5, 0, 0])
        assert result is b
        assert b.pos == [5.0, 0.0, 0.0]

    def test_rotate_degrees(self, v):
        b = v.box([2, 1, 1])
        b.rotate("z", degrees=90)
        # Volume should be preserved
        assert abs(b.volume - 2.0) < 0.01

    def test_scale(self, v):
        b = v.box([1, 1, 1])
        b.scale(2.0)
        assert abs(b.volume - 8.0) < 0.1

    def test_mirror(self, v):
        b = v.box([1, 1, 1])
        b.mirror("xy")
        # Volume preserved (may be negated)
        assert abs(b.volume) > 0.9


class TestProxyCSG:
    def test_difference(self, v):
        outer = v.box([10, 10, 10])
        inner = v.box([2, 2, 2])
        vol_before = outer.volume
        outer.difference(inner)
        assert outer.volume < vol_before

    def test_union(self, v):
        a = v.box([5, 5, 5])
        b = v.box([5, 5, 5])
        b.translate([3, 0, 0])
        vol_sum = a.volume + b.volume
        a.union(b)
        assert a.volume < vol_sum  # overlap
        assert a.volume > 0

    def test_csg_chain(self, v):
        a = v.box([10, 10, 10])
        b = v.box([2, 2, 2])
        c = v.box([2, 2, 2])
        c.translate([5, 0, 0])
        a.difference(b).difference(c)
        assert a.volume > 0
