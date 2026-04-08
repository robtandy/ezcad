"""Pickleable command objects sent from Shape → View over a multiprocessing Queue."""


class AddCmd:
    """Add a new Shape to the scene."""
    def __init__(self, shape):
        self.uuid = shape.uuid
        self.mesh_data = shape._mesh.export(file_type="stl")
        self.pos = list(shape.pos)
        self.color = shape.color

    def execute(self, v):
        v._update_gfx_mesh(self.uuid, self.mesh_data, self.pos, self.color)


class SyncCmd:
    """Replace an existing Shape's geometry."""
    def __init__(self, uuid, mesh, pos, color="#336699"):
        self.uuid = uuid
        self.mesh_data = mesh.export(file_type="stl")
        self.pos = list(pos)
        self.color = color

    def execute(self, v):
        v._update_gfx_mesh(self.uuid, self.mesh_data, self.pos, self.color)


class VisibilityCmd:
    """Show or hide a Shape."""
    def __init__(self, uuid, visible):
        self.uuid = uuid
        self.visible = visible

    def execute(self, v):
        gmesh = v.gfx_map.get(self.uuid)
        if gmesh is not None:
            gmesh.visible = self.visible


class QuitCmd:
    """Shut down the background viewer process."""
    def execute(self, v):
        import sys
        sys.exit(0)
