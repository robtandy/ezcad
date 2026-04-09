import math
import pytest
import ezcad


@pytest.fixture(scope="module")
def v():
    view = ezcad.View()
    yield view
    view.close()


# ── Mesh creation via proxy ──────────────────────────────────────────

class TestMeshCreate:
    def test_box(self, v):
        b = ezcad.d3.box([2, 3, 4])
        assert b._uid
        assert b.pos == [0.0, 0.0, 0.0]
        assert math.isclose(b.volume, 24.0, rel_tol=1e-3)

    def test_sphere(self, v):
        s = ezcad.d3.sphere(1.0)
        assert math.isclose(s.volume, 4 / 3 * math.pi, rel_tol=0.05)

    def test_cylinder(self, v):
        c = ezcad.d3.cylinder(1.0, 2.0)
        assert math.isclose(c.volume, math.pi * 2, rel_tol=0.05)

    def test_cone(self, v):
        c = ezcad.d3.cone(1.0, 3.0)
        assert math.isclose(c.volume, math.pi, rel_tol=0.05)

    def test_torus(self, v):
        t = ezcad.d3.torus(2.0, 0.5)
        assert t.volume > 0


# ── Transforms via proxy ─────────────────────────────────────────────

class TestMeshTransforms:
    def test_translate(self, v):
        b = ezcad.d3.box([1, 1, 1])
        b.translate([1, 2, 3])
        assert b.pos == [1.0, 2.0, 3.0]

    def test_translate_chain(self, v):
        b = ezcad.d3.box([1, 1, 1])
        assert b.translate([5, 0, 0]) is b

    def test_rotate(self, v):
        b = ezcad.d3.box([2, 1, 1])
        vol = abs(b.volume)
        b.rotate("z", degrees=90)
        assert math.isclose(abs(b.volume), vol)

    def test_scale(self, v):
        b = ezcad.d3.box([1, 1, 1])
        b.scale(2.0)
        assert math.isclose(b.volume, 8.0, rel_tol=0.1)

    def test_mirror(self, v):
        b = ezcad.d3.box([1, 1, 1])
        b.translate([0, 0, 5])
        b.mirror("xy")
        # Z bound should be negative after mirror
        bounds = b.bounds()
        assert bounds[1][2] < 0


# ── Properties via proxy ─────────────────────────────────────────────

class TestMeshProperties:
    def test_visible(self, v):
        b = ezcad.d3.box([1, 1, 1])
        assert b.visible is True
        b.visible = False
        assert b.visible is False

    def test_colors(self, v):
        b = ezcad.d3.box([1, 1, 1])
        b.color = "#ff0000"
        assert b.color == "#ff0000"


# ── CSG via proxy ────────────────────────────────────────────────────

class TestMeshCSG:
    def test_difference(self, v):
        outer = ezcad.d3.box([10, 10, 10])
        inner = ezcad.d3.box([2, 2, 2])
        vol0 = outer.volume
        outer.difference(inner)
        assert outer.volume < vol0
        assert outer.volume > 0

    def test_union(self, v):
        a = ezcad.d3.box([5, 5, 5])
        b = ezcad.d3.box([5, 5, 5])
        b.translate([3, 0, 0])
        total = a.volume + 250  # b.volume
        a.union(b)
        assert 0 < a.volume < total

    def test_csg_chain(self, v):
        a = ezcad.d3.box([10, 10, 10])
        b = ezcad.d3.box([2, 2, 2])
        c = ezcad.d3.box([2, 2, 2])
        c.translate([5, 0, 0])
        a.difference(b).difference(c)
        assert a.volume > 0


# ── Profile via proxy ────────────────────────────────────────────────

class TestProfileCreate:
    def test_circle(self, v):
        p = ezcad.d2.circle(2.0)
        assert p._uid

    def test_rect(self, v):
        p = ezcad.d2.rect(4.0, 3.0)
        assert p._uid

    def test_ngon(self, v):
        p = ezcad.d2.ngon(1.0, sides=6)
        assert p._uid
