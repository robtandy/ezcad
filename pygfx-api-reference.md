# pygfx API Reference (v0.16)

Access: `import pygfx` — all public symbols are in the top-level namespace.

---

## Renderers

| Class / Function | Signature |
|---|---|
| `Renderer` | Base abstract class |
| `WgpuRenderer` | `(target, pixel_filter='mitchell', show_fps=False, sort_objects=True, enable_events=True, gamma_correction=1.0, ppaa='default', …)` |
| `SvgRenderer` | `(width, height, filename)` |

## Scene Objects

| Class | Signature |
|---|---|
| `WorldObject` | `(geometry=None, material=None, *, visible=True, render_order=0, name='')` |
| `Group` | `(*, visible=True, name='')` |
| `Scene` | `(environment=None, *args, **kwargs)` |
| `Background` | `(geometry=None, material=None, *, render_order=-1e6, **kwargs)` |
| `Points` | `(geometry=None, material=None, *, visible=True, render_order=0, name='')` |
| `Line` | `(geometry=None, material=None, *, visible=True, render_order=0, name='')` |
| `Mesh` | `(geometry=None, material=None, *args, **kwargs)` |
| `InstancedMesh` | `(geometry, material, count, **kwargs)` |
| `InstancedLine` | `(geometry, material, count, **kwargs)` |
| `SkinnedMesh` | `(geometry, material)` |
| `Image` | `(geometry=None, material=None, *, visible=True, render_order=0, name='')` |
| `Volume` | `(geometry=None, material=None, *, visible=True, render_order=0, name='')` |
| `Text` | `(geometry=None, material=None, *, text=None, markdown=None, font_size=12, family=None, direction=None, screen_space=False, anchor='middle-center', anchor_offset=0, max_width=0, line_height=1.2, paragraph_spacing=0, text_align='start', text_align_last='auto', visible=True, render_order=0, name='')` |
| `MultiText` | *(same as Text)* |
| `TextBlock` | `(index, dirty_blocks)` |
| `Grid` | `(geometry=None, material=None, *, orientation, render_order=-100, **kwargs)` |
| `Ruler` | `(*, start_pos=(0,0,0), end_pos=(0,0,0), start_value=0.0, ticks=None, tick_format='0.4g', tick_side='left', tick_size=8.0, …)` |

## Lights

| Class | Signature |
|---|---|
| `Light` | `(color='#ffffff', intensity=1, *, cast_shadow=False, **kwargs)` |
| `AmbientLight` | `(color='#ffffff', intensity=0.2)` |
| `PointLight` | `(color='#ffffff', intensity=3, *, cast_shadow=False, distance=0, decay=0, **kwargs)` |
| `DirectionalLight` | `(color='#ffffff', intensity=3, *, cast_shadow=False, target=None, **kwargs)` |
| `SpotLight` | `(color='#ffffff', intensity=3, *, cast_shadow=False, distance=0, decay=0, angle=π/3, penumbra=0, **kwargs)` |
| `LightShadow` | Base class |
| `PointLightShadow` | — |
| `DirectionalLightShadow` | — |
| `SpotLightShadow` | — |

## Skeletons

| Class | Signature |
|---|---|
| `Bone` | `(name='')` |
| `Skeleton` | `(bones, bone_inverses=None)` |

## Cameras

| Class | Signature |
|---|---|
| `Camera` | Base class |
| `NDCCamera` | — |
| `ScreenCoordsCamera` | `(invert_y=False)` |
| `PerspectiveCamera` | `(fov=50, aspect=1, *, width=None, height=None, zoom=1, maintain_aspect=True, depth=None, depth_range=None)` |
| `OrthographicCamera` | `(width=1, height=1, *, zoom=1, maintain_aspect=True, depth=None, depth_range=None)` |

## Controllers

| Class | Signature |
|---|---|
| `Controller` | `(camera=None, *, enabled=True, damping=4, auto_update=True, register_events=None)` |
| `PanZoomController` | — |
| `OrbitController` | `(*args, target=None, **kwargs)` |
| `TrackballController` | `(*args, target=None, **kwargs)` |
| `FlyController` | `(camera, *, speed=None, **kwargs)` |

## Geometry

**Factory functions:**

| Function | Signature |
|---|---|
| `box_geometry` | `(width=1, height=1, depth=1, width_segments=1, height_segments=1, depth_segments=1)` |
| `cylinder_geometry` | `(radius_bottom=1, radius_top=1, height=1, radial_segments=8, height_segments=1, theta_start=0, theta_length=2π, open_ended=False)` |
| `cone_geometry` | `(radius=1, height=1, radial_segments=8, height_segments=1, open_ended=False)` |
| `sphere_geometry` | `(radius=1, width_segments=32, height_segments=16, phi_start=0, phi_length=2π, theta_start=0, theta_length=π)` |
| `plane_geometry` | `(width=1, height=1, width_segments=1, height_segments=1)` |
| `octahedron_geometry` | `(radius=1.0, subdivisions=0)` |
| `icosahedron_geometry` | `(radius=1.0, subdivisions=0)` |
| `dodecahedron_geometry` | `(radius=1.0, subdivisions=0)` |
| `tetrahedron_geometry` | `(radius=1.0, subdivisions=0)` |
| `torus_knot_geometry` | `(scale=1, tube=0.4, tubular_segments=64, radial_segments=8, p=2, q=3, stitch=False)` |
| `klein_bottle_geometry` | `(scale=1.0, stitch=False)` |
| `geometry_from_trimesh` | `(mesh)` |

**Class:**

| Class | Signature |
|---|---|
| `Geometry` | `(*, positions=None, indices=None, normals=None, texcoords=None, colors=None, grid=None, **other_attributes)` |

## Materials

### Base

| Class | Key Params |
|---|---|
| `Material` | `opacity=1, clipping_planes=(), clipping_mode='ANY', alpha_mode='auto', alpha_config=None, depth_test=True, depth_compare='<', depth_write=None, pick_write=False, alpha_test=0.0` |

### Mesh

| Class | Key Params |
|---|---|
| `MeshAbstractMaterial` | `color='#fff', color_mode='auto', map=None, maprange=None, side='both'` |
| `MeshBasicMaterial` | `env_map=None, wireframe=False, wireframe_thickness=1, flat_shading=False, reflectivity=1.0, env_combine_mode='MULTIPLY'` |
| `MeshPhongMaterial` | `shininess=30, emissive='#000', specular='#494949'` |
| `MeshStandardMaterial` | `emissive='#000', metalness=0.0, roughness=1.0, roughness_map=None, metalness_map=None, emissive_map=None, normal_map=None, env_map_intensity=1.0, normal_scale=(1,1), emissive_intensity=1.0` |
| `MeshPhysicalMaterial` | `ior=1.5, specular='#fff', specular_intensity=1.0, clearcoat=0.0, iridescence=0.0, anisotropy=0.0, sheen=0.0, …` |
| `MeshToonMaterial` | `emissive='#000', gradient_map=None, emissive_intensity=1.0` |
| `MeshNormalMaterial` | *(inherits MeshAbstractMaterial)* |
| `MeshNormalLinesMaterial` | `line_length=1.0` |
| `MeshSliceMaterial` | `plane=(0,0,1,0), thickness=2.0` |

### Points

| Class | Key Params |
|---|---|
| `PointsMaterial` | `size=4, size_space='screen', size_mode='uniform', color=(1,1,1,1), color_mode='auto', edge_mode='centered', map=None, aa=False, rotation=0` |
| `PointsGaussianBlobMaterial` | *(similar to PointsMaterial)* |
| `PointsMarkerMaterial` | `marker='circle', marker_mode='uniform', edge_width=1.0, edge_color='black', edge_color_mode='auto', custom_sdf=None` |
| `PointsSpriteMaterial` | `sprite=None` |

### Lines

| Class | Key Params |
|---|---|
| `LineMaterial` | `thickness=2.0, thickness_space='screen', color=(1,1,1,1), color_mode='auto', map=None, dash_pattern=(), dash_offset=0, loop=False, aa=False` |
| `LineSegmentMaterial` | *(same as LineMaterial)* |
| `LineArrowMaterial` | *(same as LineMaterial)* |
| `LineThinMaterial` | *(same as LineMaterial)* |
| `LineThinSegmentMaterial` | *(same as LineMaterial)* |
| `LineInfiniteSegmentMaterial` | `start_is_infinite=True, end_is_infinite=True` |
| `LineDebugMaterial` | *(same as LineMaterial)* |

### Image / Volume / Background / Text

| Class | Key Params |
|---|---|
| `ImageBasicMaterial` | `maprange=None, clim=None, map=None, gamma=1.0, interpolation='nearest'` |
| `VolumeBasicMaterial` | `maprange=None, clim=None, map=None, gamma=1.0, interpolation='linear'` |
| `VolumeSliceMaterial` | `plane=(0,0,1,0)` |
| `VolumeRayMaterial` | `maprange=None, clim=None, map=None, gamma=1.0, interpolation='linear'` |
| `VolumeMipMaterial` | *(same as VolumeRayMaterial)* |
| `VolumeMinipMaterial` | *(same as VolumeRayMaterial)* |
| `VolumeIsoMaterial` | `threshold=0.5, step_size=1.0, substep_size=0.1, emissive='#000', shininess=30` |
| `BackgroundMaterial` | `*colors, alpha_mode='blend', depth_write=False, render_queue=1000` |
| `BackgroundImageMaterial` | `map=None` |
| `BackgroundSkyboxMaterial` | `map=None` |
| `GridMaterial` | `major_step=(1,1), minor_step=(0.1,0.1), axis_thickness=0.0, major_thickness=2.0, axis_color='#777', infinite=True` |
| `TextMaterial` | `color='#fff', outline_color='#000', outline_thickness=0, weight_offset=0, aa=False` |
| `material_from_trimesh` | `(x)` |

## Resources

| Class | Signature |
|---|---|
| `Resource` | Base class |
| `Buffer` | `(data=None, *, nbytes=None, nitems=None, format=None, chunk_size=None, force_contiguous=False, usage=0)` |
| `Texture` | `(data=None, *, dim, size=None, format=None, colorspace='srgb', colorrange='limited', generate_mipmaps=False, chunk_size=None, force_contiguous=False, usage=0)` |
| `TextureMap` | `(texture, *, uv_channel=0, filter='linear', mag_filter=None, min_filter=None, mipmap_filter=None, wrap='repeat')` |

## Helpers

| Class | Signature |
|---|---|
| `AxesHelper` | `(size=1.0, thickness=2)` |
| `GridHelper` | `(size=10.0, divisions=10, color1=(0.35,0.35,0.35,1), color2=(0.1,0.1,0.1,1), thickness=1)` |
| `BoxHelper` | `(size=1.0, thickness=1, color='white')` |
| `TransformGizmo` | `(object=None, screen_size=100)` |
| `PointLightHelper` | `(size=1, geometry=None, color=None)` |
| `DirectionalLightHelper` | `(ray_length=1, color=None, show_shadow_extent=False)` |
| `SpotLightHelper` | `(color=None)` |
| `SkeletonHelper` | `(wobject, thickness=1.0)` |
| `Stats` | `(viewport)` |

## Animation

| Class | Signature |
|---|---|
| `Clock` | `(auto_start=True)` |
| `AnimationMixer` | `()` |
| `AnimationClip` | `(name='', duration=-1, tracks=None)` |
| `AnimationAction` | `(mixer, clip)` |
| `KeyframeTrack` | `(name, target, path, times, values, interpolation)` |
| `Interpolant` | `(parameter_positions, sample_values)` |
| `LinearInterpolant` | `(parameter_positions, sample_values)` |
| `StepInterpolant` | `(parameter_positions, sample_values)` |
| `CubicSplineInterpolant` | `(parameter_positions, sample_values)` |
| `QuaternionLinearInterpolant` | `(parameter_positions, sample_values)` |

## Events

| Class | Key Params |
|---|---|
| `Event` | `(type, *, bubbles=True, target=None, root=None, time_stamp=None, cancelled=False, **unknown_keys)` |
| `PointerEvent` | `(*args, x, y, button=0, buttons=None, modifiers=None, ntouches=0, touches=None, pick_info=None, clicks=0, pointer_id=0)` |
| `KeyboardEvent` | `(*args, key, modifiers=None)` |
| `WheelEvent` | `(*args, dx, dy)` |
| `EventTarget` | Base mixin class |
| `RootEventHandler` | Base mixin class |

## Enums (`pygfx.utils.enums`)

`AlphaMethod`: `opaque`, `stochastic`, `blended`, `weighted`
`AlphaMode`: `auto`, `solid`, `solid_premul`, `dither`, `bayer`, `blend`, `add`, `subtract`, `multiply`, `weighted_blend`, `weighted_solid`, `custom`
`BindMode`: `attached`, `detached`
`ColorMode`: `auto`, `uniform`, `vertex`, `face`, `vertex_map`, `face_map`, `debug`
`CoordSpace`: `model`, `world`, `screen`
`EdgeMode`: `centered`, `inner`, `outer`
`ElementFormat`: `i1`, `u1`, `i2`, `u2`, `i4`, `u4`, `f2`, `f4`
`MarkerMode`: `uniform`, `vertex`
`MarkerShape`: `circle`, `ring`, `square`, `diamond`, `plus`, `cross`, `asterisk6`, `asterisk8`, `tick`, `tick_left`, `tick_right`, `triangle_up`, `triangle_down`, `triangle_left`, `triangle_right`, `heart`, `spade`, `club`, `pin`, `custom`
`RotationMode`: `uniform`, `vertex`, `curve`
`SizeMode`: `uniform`, `vertex`
`TextAlign`: `start`, `end`, `left`, `right`, `center`, `justify`, `justify_all`, `auto`
`TextAnchor`: `top-left`, `top-center`, `top-right`, `baseline-left`, `baseline-center`, `baseline-right`, `middle-left`, `middle-center`, `middle-right`, `bottom-left`, `bottom-center`, `bottom-right`
`VisibleSide`: `front`, `back`, `both`

## Utilities

| Function | Signature |
|---|---|
| `show` | `(object, up=None, *, canvas=None, renderer=None, controller=None, camera=None, before_render=None, after_render=None, draw_function=None)` |
| `Display` | `(canvas=None, renderer=None, controller=None, camera=None, before_render=None, after_render=None, draw_function=None, stats=False)` |
| `Viewport` | `(renderer, rect=None)` |
| `load_mesh` | `(path, remote_ok=False)` |
| `load_meshes` | `(path, remote_ok=False)` |
| `load_scene` | `(path, flatten=False, meshes=True, materials=True, volumes=True, lights='auto', camera='auto', remote_ok=False)` |
| `load_gltf` | `(path, quiet=False, remote_ok=True)` |
| `load_gltf_async` | `(path, quiet=False, remote_ok=True)` |
| `load_gltf_mesh` | `(path, materials=True, quiet=False, remote_ok=True)` |
| `load_gltf_mesh_async` | `(path, materials=True, quiet=False, remote_ok=True)` |
| `print_scene_graph` | `(obj, show_pos=False, show_rot=False, show_scale=False)` |
| `print_wgpu_report` | `()` |

| Object | Type |
|---|---|
| `Color` | `(r, g, b, a)` color utility |
| `font_manager` | `FontManager` singleton |
| `cm` | Colormap module |
| `logger` | Logger instance |
