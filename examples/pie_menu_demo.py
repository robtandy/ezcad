"""Demo: use the pie menu to add shapes and perform actions."""

import sys
import math

from ezcad.d3 import box, sphere, cylinder, cone, torus
from ezcad.d2 import Profile
from ezcad import View, MenuItem
from ezcad.icons import (
    icon_cube, icon_sphere, icon_cylinder, icon_cone,
    icon_torus, icon_trash, icon_reset, icon_union,
    icon_difference, icon_grid, icon_rotate,
)


def _build_menu(view):
    """Build the pie menu tree and register it."""

    def add_box(x, y, shape):
        print(f"[callback] add_box at ({x}, {y})")
        b = box([3, 2, 1])
        view.add(b)

    def add_sphere(x, y, shape):
        print(f"[callback] add_sphere at ({x}, {y})")
        s = sphere(radius=1.5)
        view.add(s)

    def add_cylinder(x, y, shape):
        print(f"[callback] add_cylinder at ({x}, {y})")
        c = cylinder(radius=1.0, height=3.0)
        view.add(c)

    def add_cone(x, y, shape):
        print(f"[callback] add_cone at ({x}, {y})")
        c = cone(radius=1.0, height=3.0)
        view.add(c)

    def add_torus(x, y, shape):
        print(f"[callback] add_torus at ({x}, {y})")
        t = torus(major_radius=1.5, minor_radius=0.5)
        view.add(t)

    def clear_all(x, y, shape):
        print(f"[callback] clear_all")

    def camera_reset(x, y, shape):
        print(f"[callback] camera_reset")

    # Add primitive shapes (first ring)
    primitives = MenuItem(icon=icon_cube, children=[
        MenuItem(icon=icon_cube, callback=add_box),
        MenuItem(icon=icon_sphere, callback=add_sphere),
        MenuItem(icon=icon_cylinder, callback=add_cylinder),
        MenuItem(icon=icon_cone, callback=add_cone),
        MenuItem(icon=icon_torus, callback=add_torus),
    ])

    # Modify / boolean (second ring)
    modify = MenuItem(icon=icon_union, children=[
        MenuItem(icon=icon_union, callback=lambda x, y, s: print("union")),
        MenuItem(icon=icon_difference, callback=lambda x, y, s: print("diff")),
    ])

    # Utilities (third ring)  
    tools = MenuItem(icon=icon_trash, children=[
        MenuItem(icon=icon_trash, callback=clear_all),
        MenuItem(icon=icon_reset, callback=camera_reset),
    ])

    # Root — 8 items evenly spread
    menu_items = [
        primitives,
        modify,
        tools,
        MenuItem(icon=icon_grid, callback=lambda x, y, s: print("grid")),
        MenuItem(icon=icon_rotate, callback=lambda x, y, s: print("rotate")),
    ]

    view.register_menu(menu_items)


def main():
    view = View()
    _build_menu(view)

    # Start blank — no shapes added yet
    # User right-clicks anywhere to open the pie menu
    
    import time
    while True:
        msg = view.get_return()
        if msg is not None:
            from ezcad.commands import RequestMenuOpen, MenuClickCmd
            if isinstance(msg, RequestMenuOpen):
                view.open_menu_at(msg.x, msg.y)
            elif isinstance(msg, MenuClickCmd):
                # Resolve the callback in the main process
                from ezcad.menu import MenuItem
                item = MenuItem.by_id(msg.item_id)
                if item and item.callback:
                    item.callback(msg.x, msg.y, shape=None)
        time.sleep(0.01)


if __name__ == "__main__":
    main()
