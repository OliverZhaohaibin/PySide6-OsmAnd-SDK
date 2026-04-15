# PySide6-OsmAnd-SDK

`PySide6-OsmAnd-SDK` is an independent GitHub project for bringing OsmAnd's native map stack into modern Qt6 and PySide6 workflows. It combines vendored OsmAnd core sources, Windows build tooling, native widget integration, and a runnable preview application in one repository, making it easier to build and embed offline map capabilities from a single codebase.

Author: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

## Highlights

- ports the OsmAnd Qt5-era native map stack to Qt6
- makes the native C++ map widget usable from PySide6 applications
- supports offline rendering based on OsmAnd `.obf` map data
- includes both native OpenGL preview and Python-driven raster preview paths
- provides build scripts for Windows (MinGW, MSVC) and Linux (GCC, Clang) toolchains
- bundles demo data and OsmAnd resources for local testing and integration work

## Demo Video

[Demo Video](https://github.com/user-attachments/assets/d2352ee7-398d-4c90-bd96-d747a6b5e0bb)

## Why This Project Matters

This project is aimed at developers who want the strengths of OsmAnd's map engine while building with modern Qt and Python tools. It reduces the friction of combining C++ map rendering with a PySide6 user interface, and provides a practical foundation for desktop map viewers, GIS tools, travel applications, and other offline-first location products.

By moving the native stack forward to Qt6 and validating PySide6 compatibility, the repository helps make OsmAnd-based development more accessible to teams working on current-generation Qt applications instead of older Qt5-only integrations.

## Repository Layout

- `vendor/osmand/build`: build tree and supporting files used by the Windows-oriented OsmAnd build flow
- `vendor/osmand/core`: vendored OsmAnd core sources
- `vendor/osmand/core-legacy`: vendored legacy core sources still required by the native build
- `vendor/osmand/resources`: OsmAnd rendering resources, styles, and data files
- `tools/osmand_render_helper_native`: native helper and widget sources plus MinGW and MSVC build scripts
- `src/maps`: PySide6 preview application and Python integration layer
- `src/maps/main.py`: preview entry point

## Key Capabilities

- native `osmand_native_widget.dll` hosting through PySide6
- helper-backed Python raster rendering for `.obf`
- OpenGL and non-OpenGL preview widgets
- bundled `World_basemap_2.obf` demo data for immediate testing

## Map Data And Styles

### `.obf` Files

OsmAnd `.obf` files are offline binary map packages. They store the map data consumed by the native engine, including vector features such as roads, boundaries, landuse, water, place labels, routing-related information, and points of interest. In this repository, the preview uses the bundled `src/maps/tiles/World_basemap_2.obf` file so the project can be run and demonstrated immediately.

The bundled `.obf` file is only a default demo dataset. You can replace it with another OsmAnd `.obf` file, select a different file from the preview window, or point the runtime to a custom path through the documented environment variables. Additional `.obf` downloads are available from the official OsmAnd download list: [https://download.osmand.net/list.php](https://download.osmand.net/list.php).

### `styles` Files

Rendering styles are XML-based rule files located under `vendor/osmand/resources/rendering_styles`, usually named like `default.render.xml`, `mapnik.render.xml`, or `snowmobile.render.xml`. These files control how the same `.obf` data is visualized, including colors, line rules, polygon fills, icons, labels, and theme-specific display logic. The Python integration layer passes both the selected `.obf` data source and the active style file into the OsmAnd rendering backend, which makes it possible to switch presentation without changing the underlying map data.

Together, `.obf` data files and rendering style files form the core of the offline map pipeline in this project: the `.obf` file provides the geographic content, and the style file defines how that content appears on screen.

## Quick Start

### Windows

1. Install Python dependencies:

```powershell
python -m pip install -e .
```

2. Build at least one runtime:

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper.ps1
```

or:

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_native_widget_msvc.ps1
```

3. Launch the preview:

```powershell
osmand-preview --backend auto
```

You can also run the entry point directly:

```powershell
python src\maps\main.py --backend auto
```

### Linux

1. Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential cmake git qt6-base-dev libqt6opengl6-dev

# Fedora/RHEL
sudo dnf install gcc g++ cmake git qt6-qtbase-devel qt6-qtbase-gui qt6-qtdeclarative-devel

# Arch
sudo pacman -S base-devel cmake git qt6-base
```

2. Install Python dependencies:

```bash
python -m pip install -e .
```

3. Build the helper:

```bash
bash tools/osmand_render_helper_native/build_linux.sh
```

4. Launch the preview:

```bash
osmand-preview --backend auto
```

You can also run the entry point directly:

```bash
python src/maps/main.py --backend auto
```

## Documentation

- [Python SDK Guide](docs/python-sdk-guide.md)
- [Build Guide](BUILD.md)

## Runtime Notes

- the preview defaults to the bundled `src/maps/tiles/World_basemap_2.obf` and the vendored resources under `vendor/osmand/resources`
- the bundled `.obf` is replaceable, so you can test other OsmAnd map extracts downloaded from [download.osmand.net/list.php](https://download.osmand.net/list.php)
- **Windows**: helper outputs in `tools/osmand_render_helper_native/dist` and `tools/osmand_render_helper_native/dist-msvc` are generated and ignored by Git
- **Linux**: helper outputs in `tools/osmand_render_helper_native/dist-linux` are generated and ignored by Git
- when the native widget runtime is available, the preview can use the embedded OsmAnd widget; otherwise the Python rendering path remains available
- on Linux, the native widget library is built as a `.so` file (shared object); the Python path remains the recommended approach for Linux deployments

## License

Because this repository redistributes vendored OsmAnd source trees, the top-level project is documented as `GPL-3.0-or-later`.

Top-level license files:

- `LICENSE`: project-level license summary for `PySide6-OsmAnd-SDK`
- `COPYING`: verbatim GNU GPL v3 text

The vendored upstream trees keep their own original license files:

- `vendor/osmand/core/LICENSE`
- `vendor/osmand/core-legacy/LICENSE`
- `vendor/osmand/resources/LICENSE`

Additional context is summarized in `NOTICE.md`.
