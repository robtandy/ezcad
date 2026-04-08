"""Demo: interactive CAD via RPC proxies.

Run this to see the architecture work:
  1. A blank pygfx window appears immediately
  2. Shapes are created via proxy methods on the View
  3. Transforms, CSG, and property access all work through the proxy
"""

import time
from ezcad import View


def main():
    # ── 1. View appears immediately, window is blank ──────────────────
    print("[demo] Creating View...")
    v = View()
    print("[demo] Window should be up now.  Wait a moment for shapes...")
    time.sleep(2)

    # ── 2. Create shapes (proxy objects, geometry lives on the server) ──
    print("\n[demo] Creating shapes...")

    b1 = v.box([3, 3, 3])
    print(f"  box1 uid={b1._uid[:8]}, pos={b1.pos}, volume={b1.volume:.0f}")
    time.sleep(1)  # window should show a blue box

    s1 = v.sphere(radius=1.0)
    print(f"  sphere volume={s1.volume:.1f}")
    time.sleep(1)

    cy1 = v.cylinder(radius=0.5, height=4.0)
    print(f"  cylinder created")
    time.sleep(1)

    t1 = v.torus(major_radius=2.0, minor_radius=0.3)
    print(f"  torus created")
    time.sleep(1)

    # ── 3. Transforms (each one fires an RPC call) ────────────────────
    print("\n[demo] Transforming shapes...")

    b1.translate([0, 0, 3])
    print(f"  box moved to {b1.pos}")
    time.sleep(1)

    cy1.translate([0, 4, 0])
    print(f"  cylinder moved to {cy1.pos}")
    time.sleep(1)

    t1.rotate("z", degrees=45)
    t1.translate([5, 0, 0])
    print(f"  torus rotated + moved")
    time.sleep(1)

    s1.scale(1.5)
    print(f"  sphere scaled to 1.5x, volume now {s1.volume:.1f}")
    time.sleep(1)

    # ── 4. Property access (each one is a blocking RPC call) ──────────
    print("\n[demo] Reading properties over RPC...")
    print(f"  box.pos     = {b1.pos}")
    print(f"  box.visible = {b1.visible}")
    print(f"  box.color   = {b1.color}")
    print(f"  box.volume  = {b1.volume:.0f}")
    print(f"  box.area    = {b1.area:.0f}")

    # ── 5. Visibility toggle ─────────────────────────────────────────
    print("\n[demo] Toggling visibility...")
    b1.visible = False
    time.sleep(1)
    print("  box hidden")
    b1.visible = True
    time.sleep(1)
    print("  box visible again")

    b1.color = "#FF6600"
    time.sleep(1)
    print("  box color changed to orange")

    # ── 6. CSG (Create two shapes, then difference/union) ─────────────
    print("\n[demo] CSG operations...")

    outer = v.box([5, 5, 5])
    print(f"  outer block volume={outer.volume:.0f}")

    inner = v.box([2, 2, 2])
    inner.translate([1.5, 1.5, 1.5])
    print(f"  inner block volume={inner.volume:.0f}")

    outer.difference(inner)
    print(f"  outer - inner = {outer.volume:.0f} (should be ~117)")
    time.sleep(2)

    # ── 7. Cross-section ─────────────────────────────────────────────
    print("\n[demo] Cross section...")
    section = v.section(outer, plane="z", value=0.0)
    if section is not None:
        print(f"  Section at z=0: {len(section)} vertices")
    else:
        print("  No section at z=0")

    # ── Wrap up ──────────────────────────────────────────────────────
    print("\n[demo] Complete!  Close the window or call v.close()")
    print("[demo] You can now interactively create more shapes with v.box([...]) etc.")

    # Keep alive so user can interact with the window
    while v._proc.is_alive():
        time.sleep(0.5)


if __name__ == "__main__":
    main()
