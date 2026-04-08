# ezcad

A lightweight CAD-like library built on top of [trimesh](https://github.com/mikedh/trimesh) for geometry and [pygfx](https://github.com/pygfx/pygfx) for rendering.

## Structure

- `ezcad.d2` — `Profile` class for 2D shapes (`circle`, `rect`, `ngon`, etc.)
- `ezcad.d3` — `Mesh` class for 3D solids (`box`, `sphere`, `cylinder`, etc.)
- `ezcad.view` — Multiprocess viewer for interactive display

## Features

- Eager viewer updates on every mutation
- `with mesh.frozen():` escape hatch for batched operations
- Boolean CSG: `union()`, `difference()`, `intersection()`
- Transforms: `translate()`, `rotate()`, `scale()`, `mirror()`
- 2D → 3D via `Profile.extrude()` and `Profile.revolve()`
- 3D → 2D via `Mesh.section()`

## Quick Start

```python
from ezcad.d2 import rect, cylinder
from ezcad import View

# Create a plate and punch a hole
plate = rect(width=10, height=6).extrude(2).difference(cylinder(radius=1.5, height=5))

view = View()
view.add(plate)
```
