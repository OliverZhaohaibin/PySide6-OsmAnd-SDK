# PySide6-OsmAnd-SDK Build Guide

This repository supports three practical workflows on Windows:

1. build the local MinGW helper directly from `tools/osmand_render_helper_native`
2. build through the official OsmAnd MinGW build tree
3. build the native widget through the official OsmAnd MSVC build tree

Maintainer: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

## Prerequisites

- Python 3.12+
- PySide6 installed in the active environment
- CMake
- Git for Windows
- For MinGW builds:
  - `C:\Qt\6.10.1\mingw_64`
  - `C:\Qt\Tools\mingw1310_64`
- For MSVC builds:
  - Visual Studio 2022 with C++ workload
  - `vcvars64.bat`

The default script parameters assume the same tool locations used by the original workspace.

## 1. Local MinGW Helper Build

This is the shortest path if you only need the helper EXE and optional native widget DLL under `tools/osmand_render_helper_native/dist`.

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper.ps1
```

Outputs:

- `tools/osmand_render_helper_native\dist\osmand_render_helper.exe`
- `tools/osmand_render_helper_native\dist\osmand_native_widget.dll` or `libosmand_native_widget.dll`

## 2. Official OsmAnd MinGW Chain

This script stages a local workspace under `build\official-workspace`, creates the required junction layout, and runs the official OsmAnd MinGW build flow against the vendored sources in this repository.

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper_official.ps1
```

Outputs:

- `build\official-workspace\binaries\windows\gcc-amd64\Release\osmand_render_helper.exe`
- mirrored runtime files under `tools\osmand_render_helper_native\dist`

## 3. Official OsmAnd MSVC Chain

This script stages the same local workspace and builds the native widget with the official MSVC-oriented OsmAnd flow.

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_native_widget_msvc.ps1
```

Outputs:

- `build\official-workspace\binaries\windows\msvc-amd64\...`
- mirrored runtime files under `tools\osmand_render_helper_native\dist-msvc`

## Preview App

After at least one runtime is built:

```powershell
python -m pip install -e .
osmand-preview --backend auto
```

Useful flags:

- `--backend auto`
- `--backend python`
- `--backend native`
- `--center <lon> <lat>`
- `--zoom <value>`
- `--screenshot <path>`

## Data Paths

Default runtime paths:

- OBF data: `src/maps/tiles/World_basemap_2.obf`
- OsmAnd resources: `vendor/osmand/resources`
- helper EXE: `tools/osmand_render_helper_native/dist/osmand_render_helper.exe`
- native widget DLL: `tools/osmand_render_helper_native/dist-msvc/osmand_native_widget.dll` or MinGW `dist`

The bundled `World_basemap_2.obf` file is only a default demo dataset. You can replace it with another OsmAnd `.obf` file, select a different file from the preview window, or point the runtime to a custom path through the environment variables below. Additional `.obf` downloads are available from the official OsmAnd download list: [https://download.osmand.net/list.php](https://download.osmand.net/list.php).

Override environment variables if needed:

- `IPHOTO_OSMAND_OBF_PATH`
- `IPHOTO_OSMAND_RESOURCES_ROOT`
- `IPHOTO_OSMAND_STYLE_PATH`
- `IPHOTO_OSMAND_RENDER_HELPER`
- `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY`
