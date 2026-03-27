# PySide6-OsmAnd-SDK Python SDK Guide

This guide explains how to use `PySide6-OsmAnd-SDK` for Python map development, what the SDK currently exposes, which runtime pieces must exist on disk, and which integration path is the safest one for a real PySide6 application.

If you have not run the repository yet, start with [README](../README.md) and [BUILD.md](../BUILD.md), then come back here and follow the flow of "run the preview first, embed the widget second, customize data and styling third."

## 1. What This Repository Actually Is

This repository is currently closer to a runnable SDK workspace than to a pure Python map package that works after a simple `pip install`.

It is made of four layers:

1. `vendor/osmand/...`
   Vendored OsmAnd native sources and resources.
2. `tools/osmand_render_helper_native/...`
   Build scripts, the helper renderer, and the native Qt widget bridge.
3. `src/maps/...`
   The PySide6-side integration layer, map widgets, preview app, and path resolution logic.
4. `.obf` map data and rendering styles
   The offline map content and XML styling rules that actually drive rendering.

Because of that, the recommended setup is:

- keep this repository as a local SDK workspace
- install it in editable mode with `python -m pip install -e .`
- build the helper or native widget inside this repo
- import `maps` directly from your PySide6 app

You can integrate it into another project, but then you should explicitly provide runtime paths instead of relying on the repository defaults.

## 2. The Two Main Backend Paths

There are currently two practical ways to use the SDK.

### 2.1 `NativeOsmAndWidget`

This is the native C++ OsmAnd Qt map widget hosted inside PySide6 through a DLL bridge.

Characteristics:

- closest to the native OsmAnd widget path
- requires OpenGL
- currently Windows-only
- depends on `osmand_native_widget.dll`
- the DLL path is not part of `MapSourceSpec`; it is resolved from default repo paths or environment variables

Use it when:

- you are explicitly targeting Windows
- you have already built the native widget DLL
- you want behavior that stays close to the native OsmAnd widget integration

### 2.2 Python Widget + Helper Rendering

This is the easiest integration path today. The Python widget handles interaction and presentation, while an external helper process renders OBF tiles and returns raster output to Qt.

There are two frontends on top of that path:

- `MapGLWidget`
  Uses `QOpenGLWidget` as the display surface and is the recommended default when OpenGL is available.
- `MapWidget`
  Uses a plain `QWidget` plus `QPainter`, so it can still run without OpenGL.

Characteristics:

- easiest path to get running
- `MapSourceSpec` can explicitly point to the `.obf`, resources directory, style XML, and helper executable
- rendering output is raster tiles
- the SDK already handles tile requests, worker threading, and cache lookup

Use it when:

- you want to embed offline OBF maps into a Python desktop app quickly
- you want the simplest setup first
- you want a stable Python-side integration before evaluating the native widget

## 3. Recommended Integration Order

The smoothest path is:

1. run the built-in preview app and verify the runtime is complete
2. embed `MapGLWidget` or `MapWidget` into your own `QMainWindow`
3. swap in your own `.obf`, style file, or native widget only after the basics work
4. build your business overlays, markers, and side panels on top of the map widget

That keeps "can the map render at all?" separate from "how should the product UI behave?"

## 4. Run the Built-In Preview First

### 4.1 Install Python Dependencies

From the repository root:

```powershell
python -m pip install -e .
```

Editable install is recommended because the current default path resolution is designed around this repository layout.

### 4.2 Build at Least One Runtime

If you only want the Python map path first, build the helper:

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper.ps1
```

If you want to try the native embedded widget:

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_native_widget_msvc.ps1
```

For full build details, see [BUILD.md](../BUILD.md).

### 4.3 Launch the Preview

```powershell
osmand-preview --backend auto
```

You can also run the entry point directly:

```powershell
python src\maps\main.py --backend auto
```

Useful arguments:

- `--backend auto`
  Auto-selects the startup renderer. The preview prefers the native widget when available, then falls back to the Python path.
- `--backend native`
  Forces the native widget.
- `--backend python`
  Forces the Python + helper path.
- `--center <lon> <lat>`
  Sets the initial center point. The argument order is longitude, latitude.
- `--zoom <value>`
  Sets the initial zoom.
- `--screenshot <path>`
  Captures a screenshot after startup and exits.

Example:

```powershell
osmand-preview --backend python --center 2.3522 48.8566 --zoom 8 --screenshot .\paris.png
```

### 4.4 Basic Preview Interactions

The preview window already exposes enough interaction to validate the runtime:

- drag with the mouse to pan
- use the mouse wheel to zoom
- `+` or `=`
  zoom in
- `-` or `_`
  zoom out
- `Home` or `R`
  reset the view
- arrow keys or `W A S D`
  pan
- `File -> Select OBF Source...`
  switch to a different `.obf` file

## 5. Embedding the Map in Your Own PySide6 App

The most common pattern is to treat the map as a normal Qt widget and place it into your main window.

### 5.1 Minimal Example with `MapGLWidget`

If the helper runtime exists, this is usually the best first integration:

```python
from PySide6.QtWidgets import QApplication, QMainWindow

from maps.map_widget import MapGLWidget


app = QApplication([])

window = QMainWindow()
window.setWindowTitle("My Map App")

map_widget = MapGLWidget()
map_widget.center_on(2.3522, 48.8566)
map_widget.set_zoom(8.0)

window.setCentralWidget(map_widget)
window.resize(1200, 800)
window.show()

app.exec()
```

This relies on the default runtime paths:

- `.obf`: `src/maps/tiles/World_basemap_2.obf`
- resources: `vendor/osmand/resources`
- helper: `tools/osmand_render_helper_native/dist/osmand_render_helper.exe`

If those files are not present in the default layout, use `MapSourceSpec` explicitly.

### 5.2 Use `MapWidget` When OpenGL Is Not Available

```python
from PySide6.QtWidgets import QApplication, QMainWindow

from maps.map_widget import MapWidget


app = QApplication([])

window = QMainWindow()
window.setWindowTitle("CPU Map")

map_widget = MapWidget()
window.setCentralWidget(map_widget)
window.resize(1200, 800)
window.show()

app.exec()
```

`MapWidget` still uses the helper-backed OBF path. The difference is only the frontend surface.

### 5.3 Auto-Select the Best Available Widget

If you want "use native when it is available, otherwise use `MapGLWidget`, otherwise use `MapWidget`", you can mirror the repository's own startup logic:

```python
from PySide6.QtWidgets import QApplication, QMainWindow

from maps.main import check_opengl_support
from maps.map_sources import MapSourceSpec, has_usable_osmand_native_widget
from maps.map_widget import MapGLWidget, MapWidget, NativeOsmAndWidget
from maps.map_widget.native_osmand_widget import probe_native_widget_runtime


def create_best_map_widget(map_source: MapSourceSpec | None = None):
    source = map_source or MapSourceSpec.osmand_default()
    use_opengl = check_opengl_support()

    if use_opengl and has_usable_osmand_native_widget():
        is_ok, _reason = probe_native_widget_runtime()
        if is_ok:
            return NativeOsmAndWidget(map_source=source)

    if use_opengl:
        return MapGLWidget(map_source=source)

    return MapWidget(map_source=source)


app = QApplication([])

window = QMainWindow()
map_widget = create_best_map_widget()
window.setCentralWidget(map_widget)
window.resize(1200, 800)
window.show()

app.exec()
```

That is a good default backend selector for a real application.

## 6. Customizing the `.obf`, Resources, Style, and Helper

The recommended configuration entry point for real applications is `MapSourceSpec`.

### 6.1 What `MapSourceSpec` Represents

It describes where the map runtime comes from. The main fields are:

- `kind`
  Currently only `"osmand_obf"` is supported.
- `data_path`
  The `.obf` map file.
- `resources_root`
  The OsmAnd resources directory.
- `style_path`
  The rendering style XML.
- `helper_command`
  The helper executable command, usually a one-item tuple containing the absolute path to `osmand_render_helper.exe`.

### 6.2 Explicit Runtime Configuration

```python
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow

from maps.map_sources import MapSourceSpec
from maps.map_widget import MapGLWidget


SDK_ROOT = Path(r"D:\python_code\iPhoto\PySide6-OsmAnd-SDK")

source = MapSourceSpec(
    kind="osmand_obf",
    data_path=SDK_ROOT / "src" / "maps" / "tiles" / "World_basemap_2.obf",
    resources_root=SDK_ROOT / "vendor" / "osmand" / "resources",
    style_path=SDK_ROOT / "vendor" / "osmand" / "resources" / "rendering_styles" / "default.render.xml",
    helper_command=(
        str(SDK_ROOT / "tools" / "osmand_render_helper_native" / "dist" / "osmand_render_helper.exe"),
    ),
)

app = QApplication([])
window = QMainWindow()

map_widget = MapGLWidget(map_source=source)
map_widget.center_on(116.4074, 39.9042)
map_widget.set_zoom(9.0)

window.setCentralWidget(map_widget)
window.resize(1200, 800)
window.show()

app.exec()
```

### 6.3 One Important Path Resolution Detail

Relative paths inside `MapSourceSpec` are not resolved from your current working directory. They are resolved relative to the `maps` package directory.

In practice, that means:

- prefer absolute paths in application code
- if you start with relative paths, resolve them yourself first
- pass an absolute helper path whenever possible

### 6.4 The Default Style File

The repository default is not `default.render.xml`. It is:

```text
vendor/osmand/resources/rendering_styles/snowmobile.render.xml
```

If you want a more typical general-purpose map look, a common first change is:

```text
vendor/osmand/resources/rendering_styles/default.render.xml
```

or another OsmAnd style XML from the resources tree.

## 7. Common Widget API

`MapWidget`, `MapGLWidget`, and `NativeOsmAndWidget` expose very similar interaction methods.

### 7.1 Core Methods

- `zoom`
  The current zoom level.
- `set_zoom(zoom: float)`
  Sets the zoom and clamps it to the backend's supported range.
- `reset_view()`
  Resets the view to the default center and zoom.
- `pan_by_pixels(delta_x, delta_y)`
  Pans by a screen-space pixel delta.
- `center_lonlat() -> tuple[float, float]`
  Returns the current center as `(lon, lat)`.
- `center_on(lon, lat)`
  Centers the view on a geographic point.
- `focus_on(lon, lat, zoom_delta=1.0)`
  Centers the view and zooms in a bit, which is useful for "jump to object" interactions.
- `project_lonlat(lon, lat) -> QPointF | None`
  Projects a geographic position into widget-relative screen coordinates.
- `map_backend_metadata()`
  Returns backend capabilities such as zoom bounds.
- `shutdown()`
  Releases worker threads or polling resources. Destruction paths usually handle this, but it is still a good call when you manually replace widgets.

### 7.2 Qt Signals

- `viewChanged(float center_x, float center_y, float zoom)`
- `panned(QPointF delta)`
- `panFinished()`

One important detail: `viewChanged` emits normalized Mercator-space center coordinates, not longitude and latitude.

If you need geographic coordinates, call `center_lonlat()` inside your slot:

```python
def on_view_changed(_x: float, _y: float, zoom: float) -> None:
    lon, lat = map_widget.center_lonlat()
    print(f"center=({lon:.6f}, {lat:.6f}) zoom={zoom:.2f}")


map_widget.viewChanged.connect(on_view_changed)
```

### 7.3 Read Backend Capabilities

```python
metadata = map_widget.map_backend_metadata()
print(metadata.min_zoom, metadata.max_zoom, metadata.tile_kind, metadata.tile_scheme)
```

The most useful fields for application logic are usually:

- `min_zoom`
- `max_zoom`
- `provides_place_labels`

## 8. Adding Your Own Business Markers and Overlays

Right now the SDK is strongest at base map rendering and map interaction. It does not yet expose a high-level business API for markers, polylines, or polygons.

The most practical pattern today is:

1. use the map widget as the background
2. use `project_lonlat()` to convert geographic positions into screen coordinates
3. place your own Qt overlays on top of the map widget

For example, a simple `QLabel` used as a pin:

```python
from PySide6.QtWidgets import QLabel


pin = QLabel("X", parent=map_widget)
pin.resize(24, 24)


def update_pin() -> None:
    point = map_widget.project_lonlat(121.4737, 31.2304)
    if point is None:
        pin.hide()
        return

    pin.move(int(point.x()) - 12, int(point.y()) - 24)
    pin.show()


map_widget.viewChanged.connect(lambda *_: update_pin())
update_pin()
```

This pattern works well for:

- POI markers
- current device position
- photo locations
- selected-object bubbles

## 9. Environment Variables and Runtime Overrides

If the default repository layout is not the layout you want to use, the runtime can be overridden with environment variables.

### 9.1 Map Data and Rendering Resources

| Environment Variable | Purpose |
| --- | --- |
| `IPHOTO_OSMAND_OBF_PATH` | Override the `.obf` map file |
| `IPHOTO_OSMAND_RESOURCES_ROOT` | Override the resources directory |
| `IPHOTO_OSMAND_STYLE_PATH` | Override the style XML |
| `IPHOTO_OSMAND_RENDER_HELPER` | Override the helper command or executable path |
| `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY` | Override the native widget DLL path |

PowerShell example:

```powershell
$env:IPHOTO_OSMAND_OBF_PATH = "D:\maps\france_europe.obf"
$env:IPHOTO_OSMAND_STYLE_PATH = "D:\python_code\iPhoto\PySide6-OsmAnd-SDK\vendor\osmand\resources\rendering_styles\default.render.xml"
$env:IPHOTO_OSMAND_RENDER_HELPER = "D:\python_code\iPhoto\PySide6-OsmAnd-SDK\tools\osmand_render_helper_native\dist\osmand_render_helper.exe"
osmand-preview --backend python
```

### 9.2 Qt and MinGW Runtime Discovery

The helper process also tries to extend `PATH` so it can find Qt and MinGW DLLs. If your install locations differ from the repository defaults, set:

| Environment Variable | Purpose |
| --- | --- |
| `IPHOTO_OSMAND_QT_ROOT` | Qt root, for example `C:\Qt\6.10.1\mingw_64` |
| `IPHOTO_OSMAND_MINGW_ROOT` | MinGW root, for example `C:\Qt\Tools\mingw1310_64` |

These two are especially useful when the helper starts but cannot resolve its DLL dependencies correctly.

## 10. Which Widget Should You Choose?

### 10.1 You Want the Fastest Practical Integration

Prefer:

- `MapGLWidget`

Why:

- paths and assets can be made explicit through `MapSourceSpec`
- it is the most straightforward Python-facing integration
- it avoids the extra DLL bridge complexity of the native widget

### 10.2 The Machine Does Not Have Usable OpenGL

Use:

- `MapWidget`

Why:

- you still keep the OBF offline rendering path
- only the frontend surface falls back to a plain `QWidget`

### 10.3 You Need Behavior Closer to Native OsmAnd

Use:

- `NativeOsmAndWidget`

Requirements:

- Windows
- a built native widget DLL
- a runtime that can load that DLL successfully

## 11. Important Current Boundaries

These are worth knowing before you build a larger app around the SDK:

- the only publicly supported source kind right now is `osmand_obf`
- the native widget is currently Windows-only
- `tile_root` and `style_path` in the `MapWidget` and `MapGLWidget` constructors are compatibility fields; real configuration should go through `MapSourceSpec`
- `set_city_annotations()` and `city_at()` are currently compatibility-oriented methods, not a complete annotation system
- there is no built-in high-level overlay API yet, so markers and business panels are best handled in your own Qt layer
- the default runtime resolution depends on the repository layout, so "source checkout + editable install" is the smoothest setup
- if you package this into another project, explicitly provide the `.obf`, resources root, style file, and helper path

One extra detail matters a lot for standalone deployment:

- the Python helper path can be passed directly via `MapSourceSpec.helper_command`
- the native widget DLL path is not part of `MapSourceSpec`; it is currently resolved through default repo locations or `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY`

## 12. Troubleshooting

### 12.1 "Helper Not Configured" or "Unable to Start Helper"

Common symptoms:

- `OsmAnd helper command not configured`
- `Unable to start OsmAnd helper`

Check in this order:

1. confirm that you ran `build_helper.ps1`
2. confirm that `tools/osmand_render_helper_native/dist/osmand_render_helper.exe` exists
3. if the helper is somewhere else, set `IPHOTO_OSMAND_RENDER_HELPER`

### 12.2 `.obf`, Resources, or Style File Not Found

This is usually a path issue.

Check:

- `data_path`
- `resources_root`
- `style_path`

Absolute paths are the safest option.

### 12.3 Native Widget DLL Missing or Failing to Load

Check:

1. that you ran `build_native_widget_msvc.ps1`
2. that `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY` points to the correct DLL if you are overriding it
3. that you are on Windows
4. that Qt, PySide6, and transitive DLL dependencies are all discoverable

### 12.4 The Helper Starts but Rendering Fails

Focus on:

- `IPHOTO_OSMAND_QT_ROOT`
- `IPHOTO_OSMAND_MINGW_ROOT`
- whether the helper directory contains the runtime DLLs it needs

### 12.5 The Map Renders but the Style Is Not What You Want

Do not start by modifying widget classes. Start by changing `style_path`.

For example, switching from `snowmobile.render.xml` to `default.render.xml` is often enough to get a more standard visual style.

## 13. A Good Long-Term Integration Pattern

If your application will depend on this SDK for a while, a stable setup usually looks like this:

1. keep this repository as a separate directory or git submodule
2. construct `MapSourceSpec` explicitly in your application
3. use absolute paths for all runtime assets
4. standardize on `MapGLWidget` first
5. enable the native widget later only for Windows builds that really need it

If you just want the shortest path to a proof of concept, the simplest route is:

1. `python -m pip install -e .`
2. run `build_helper.ps1`
3. drop `MapGLWidget()` into your `QMainWindow`

That path is short, predictable, and easy to debug.
