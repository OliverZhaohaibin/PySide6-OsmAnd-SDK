# PySide6-OsmAnd-SDK

`PySide6-OsmAnd-SDK` is a standalone workspace that pulls the OsmAnd-native map work out of the larger iPhoto repository and packages it as its own GitHub-style project.

Author: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

This repository contains:

- vendored upstream OsmAnd source trees copied as real files, not junctions or submodules
- the native helper / widget build scripts for both the MinGW and MSVC chains
- a trimmed PySide6 preview app rooted at `src/maps/main.py`
- the bundled `World_basemap_2.obf` demo data used by the preview entry point

## What Is Included

- `vendor/osmand/build`: the official OsmAnd build tree used by the “official” helper scripts
- `vendor/osmand/core`: copied from `OsmAnd-core`
- `vendor/osmand/core-legacy`: copied from `OsmAnd-core-legacy`
- `vendor/osmand/resources`: copied from `OsmAnd-resources`
- `tools/osmand_render_helper_native`: native helper / widget sources plus MinGW and MSVC build scripts
- `src/maps`: the Python preview layer, simplified to use only OsmAnd OBF rendering paths

## What Was Removed From The Python Layer

The extracted Python app intentionally does **not** keep the old MapLibre / vector-tile fallback stack.

Removed from this standalone project:

- legacy `tiles/*.pbf` preview fallback
- legacy `style.json` rendering path
- traditional vector-tile parser / style resolver wiring

Kept in this standalone project:

- helper-backed Python raster rendering for `.obf`
- native `osmand_native_widget.dll` hosting through PySide6
- OpenGL and non-OpenGL preview widgets

## Quick Start

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

## Repository Notes

- The vendored OsmAnd trees are intentionally copied into this repository as actual files so the project can be archived or published independently.
- The helper output folders `tools/osmand_render_helper_native/dist` and `tools/osmand_render_helper_native/dist-msvc` are generated and ignored by Git.
- The preview app defaults to the bundled `src/maps/tiles/World_basemap_2.obf` and the vendored resources under `vendor/osmand/resources`.
- Intended GitHub owner: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

## License

Because this repository redistributes copied OsmAnd source trees, the top-level project is documented as `GPL-3.0-or-later`.

Top-level license files:

- `LICENSE`: project-level license summary for `PySide6-OsmAnd-SDK`
- `COPYING`: verbatim GNU GPL v3 text

The vendored upstream trees keep their own original license files:

- `vendor/osmand/core/LICENSE`
- `vendor/osmand/core-legacy/LICENSE`
- `vendor/osmand/resources/LICENSE`

Additional context is summarized in `NOTICE.md`.
