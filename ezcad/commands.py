"""Pickleable command objects sent between main process ↔ view process."""


class AddCmd:
    def __init__(self, shape):
        self.uuid = shape.uuid
        self.mesh_data = shape._mesh.export(file_type="stl")
        self.pos = list(shape.pos)
        self.color = shape.color

    def execute(self, v):
        v._update_gfx_mesh(self.uuid, self.mesh_data, self.pos, self.color)


class SyncCmd:
    def __init__(self, uuid, mesh, pos, color="#336699"):
        self.uuid = uuid
        self.mesh_data = mesh.export(file_type="stl")
        self.pos = list(pos)
        self.color = color

    def execute(self, v):
        v._update_gfx_mesh(self.uuid, self.mesh_data, self.pos, self.color)


class VisibilityCmd:
    def __init__(self, uuid, visible):
        self.uuid = uuid
        self.visible = visible

    def execute(self, v):
        gmesh = v.gfx_map.get(self.uuid)
        if gmesh is not None:
            gmesh.visible = self.visible


class QuitCmd:
    def execute(self, v):
        import sys
        sys.exit(0)


class RegisterActionCmd:
    """Main → view: register a handler for a named action."""
    def __init__(self, name):
        self.name = name

    def execute(self, v):
        # The viewbkg pre-registers its handlers; this ensures the
        # main-process side knows the action is ready.
        pass


class MenuOpenCmd:
    """Main → view: open the pie menu at (x, y).
    ``items`` is a nested structure of _MenuSpec that describes the tree.
    """
    def __init__(self, x, y, items):
        self.x = x
        self.y = y
        self.items = items

    def execute(self, v):
        v._open_menu(self.x, self.y, self.items)


class MenuCloseCmd:
    def __init__(self):
        pass

    def execute(self, v):
        v._close_menu()


class MenuMouseMoveCmd:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def execute(self, v):
        if v._menu_open:
            v.menu.handle_mouse(self.x, self.y)
