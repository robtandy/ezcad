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


class RequestMenuOpen:
    """View → main: user right-clicked at (x, y).  Main should respond
    with a ``MenuOpenCmd`` containing the items."""
    def __init__(self, x, y, hit_shape_uuid=None):
        self.x = x
        self.y = y
        self.hit_shape_uuid = hit_shape_uuid


class MenuOpenCmd:
    """Main → view: open the pie menu at (x, y)."""
    def __init__(self, x, y, item_specs):
        self.x = x
        self.y = y
        self.item_specs = item_specs

    def execute(self, v):
        v._open_menu(self.x, self.y, self.item_specs)


class MenuCloseCmd:
    def __init__(self):
        pass

    def execute(self, v):
        v._close_menu()


class MenuClickCmd:
    """View → main: user clicked a menu leaf."""
    def __init__(self, item_id, x, y):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.hit_shape_uuid = None
