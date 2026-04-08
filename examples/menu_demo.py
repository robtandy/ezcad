"""Demo: pie menu integration with the new RPC proxy architecture.

Run this to see the pie menu in action:
  1. A blank pygfx window appears immediately
  2. Right-click anywhere → a donut-shaped menu appears
  3. Hover a slice to see it expand outward
  4. Click a leaf icon to fire the callback (printed to console)
  5. Left-click outside a leaf to close the menu
  6. Use v.actions.poll() to dispatch events (called automatically below)
"""

import time
from ezcad import View
from ezcad.menu import _MenuSpec
from ezcad.icons import icon_cube, icon_sphere, icon_cylinder, icon_cone, \
    icon_torus, icon_trash, icon_reset, icon_union


def main():
    v = View()

    # ── Register menu actions (callbacks run in THIS process) ────────

    def on_add_box(x, y, shape):
        print(f"  [callback] add_box at ({x}, {y})")
        v.box([2, 2, 2])

    def on_add_sphere(x, y, shape):
        print(f"  [callback] add_sphere at ({x}, {y})")
        v.sphere(radius=1.0)

    def on_add_cylinder(x, y, shape):
        print(f"  [callback] add_cylinder at ({x}, {y})")
        v.cylinder(radius=0.8, height=2.0)

    def on_add_cone(x, y, shape):
        print(f"  [callback] add_cone at ({x}, {y})")
        v.cone(radius=1.0, height=2.0)

    def on_add_torus(x, y, shape):
        print(f"  [callback] add_torus at ({x}, {y})")
        v.torus(major_radius=1.2, minor_radius=0.3)

    def on_clear(x, y, shape):
        print(f"  [callback] clear — no-op for now")

    def on_help(x, y, shape):
        print(f"  [callback] help — no-op for now")

    v.actions.add("add_box", on_add_box)
    v.actions.add("add_sphere", on_add_sphere)
    v.actions.add("add_cylinder", on_add_cylinder)
    v.actions.add("add_cone", on_add_cone)
    v.actions.add("add_torus", on_add_torus)
    v.actions.add("clear", on_clear)
    v.actions.add("help", on_help)

    # ── Build and register the menu tree ─────────────────────────────

    v.register_menu([
        _MenuSpec(icon=icon_cube(), action="add_box"),
        _MenuSpec(icon=icon_sphere(), action="add_sphere"),
        _MenuSpec(icon=icon_cylinder(), action="add_cylinder"),
        _MenuSpec(icon=icon_cone(), action="add_cone"),
        _MenuSpec(icon=icon_torus(), action="add_torus"),
        _MenuSpec(icon=icon_trash(), children=[
            _MenuSpec(icon=icon_trash(), action="clear"),
            _MenuSpec(icon=icon_reset(), action="help"),
        ]),
    ])

    # ── Add a starting shape so the scene isn't blank ────────────────
    v.box([3, 3, 3])
    print("[demo] Window is up.  Right-click anywhere to open the pie menu.")

    # ── Main loop: poll for menu callbacks ───────────────────────────
    print("[demo] Polling for menu events...")
    while True:
        count = v.poll_actions()
        time.sleep(0.05)


if __name__ == "__main__":
    main()
