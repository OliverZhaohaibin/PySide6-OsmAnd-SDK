# PySide6-OsmAnd-SDK Build Guide

This repository supports multiple practical workflows:

- **Windows**: MinGW and MSVC build chains
- **Linux**: GCC and Clang build chains using CMake
- **macOS**: AppleClang/CMake build chain using Qt6 from PySide6 or a Qt install

Maintainer: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

## Prerequisites

### Windows

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

### Linux

- Python 3.12+
- PySide6 installed in the active environment
- CMake 3.20+
- Git
- C++ compiler (GCC 11+ or Clang 14+)
- Qt6 development libraries

### macOS

- macOS 12.1+
- Python 3.12+
- PySide6 installed in the active environment for Python runtime
- A Qt6 SDK with CMake package files for native C++ compilation
- CMake 3.24+
- Xcode Command Line Tools

```bash
xcode-select --install
brew install cmake
brew install qt
python -m pip install PySide6
```

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    qt6-base-dev \
    libqt6opengl6-dev \
    libqt6gui6 \
    libqt6core6 \
    qt6-qpa-plugins
```

#### Fedora/RHEL/CentOS

```bash
sudo dnf install -y \
    gcc \
    g++ \
    cmake \
    git \
    qt6-qtbase-devel \
    qt6-qtbase-gui \
    qt6-qtdeclarative-devel
```

#### Arch Linux

```bash
sudo pacman -S base-devel cmake git qt6-base
```

#### Alpine Linux

```bash
apk add --no-cache \
    build-base \
    cmake \
    git \
    qt6-qtbase-dev \
    qt6-qtbase \
    musl-dev
```

## 1. Local MinGW Helper Build

This is the shortest path if you only need the helper EXE and optional native widget DLL under `tools/osmand_render_helper_native/dist`.

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper.ps1
```

Outputs:

- `tools/osmand_render_helper_native\dist\osmand_render_helper.exe`
- `tools/osmand_render_helper_native\dist\osmand_native_widget.dll` or `libosmand_native_widget.dll`

## 2. Linux CMake Build

On Linux, build the helper using the provided CMake-based build script:

```bash
bash tools/osmand_render_helper_native/build_linux.sh
```

The script automatically:
- Detects Qt6 from PySide6, system installation, or common paths
- Checks for required build tools (CMake, GCC/Clang)
- Validates vendored OsmAnd source availability
- Configures and builds the helper executable and native widget library

Outputs:

- `tools/osmand_render_helper_native/dist-linux/osmand_render_helper` (executable)
- `tools/osmand_render_helper_native/dist-linux/osmand_native_widget.so` or `libosmand_native_widget.so` (shared library)

### Qt6 Detection on Linux

The build script automatically searches for Qt6 in this order:

1. **PySide6 embedded Qt**: If PySide6 is installed in a virtual environment, it uses the bundled Qt
   ```bash
   $VIRTUAL_ENV/lib/python3.12/site-packages/PySide6/Qt
   ```

2. **System qmake6**: If `qmake6` is available in PATH
   ```bash
   qmake6 -query QT_INSTALL_PREFIX
   ```

3. **System qmake with Qt6 check**: If `qmake` is available and reports Qt 6.x
   ```bash
   qmake -query QT_INSTALL_PREFIX
   ```

4. **Common installation paths**:
   - `/usr/lib/cmake/Qt6`
   - `/usr/local/Qt-6/lib/cmake/Qt6`
   - `/opt/Qt6/lib/cmake/Qt6`
   - `~/Qt/6.*/gcc_64/lib/cmake/Qt6`

If automatic detection fails, explicitly set the Qt root:

```bash
export QT_ROOT=/path/to/qt6
bash tools/osmand_render_helper_native/build_linux.sh
```

### Custom Build Configuration on Linux

Control the build process with environment variables:

```bash
# Use Debug build instead of Release
export BUILD_TYPE=Debug

# Use fewer parallel jobs if you have limited memory
export JOBS=4

# Use Ninja instead of Unix Makefiles (if installed)
export CMAKE_GENERATOR="Ninja"

# Specify Qt root explicitly
export QT_ROOT=/usr/lib/x86_64-linux-gnu/cmake/Qt6

bash tools/osmand_render_helper_native/build_linux.sh
```

### Troubleshooting Linux Builds

**"Could not find Qt6 installation"**

Install Qt6 development libraries:

```bash
# Ubuntu/Debian
sudo apt-get install qt6-base-dev libqt6opengl6-dev

# Or build with explicit Qt path
export QT_ROOT=/path/to/qt6
bash tools/osmand_render_helper_native/build_linux.sh
```

**"Neither g++ nor clang++ found"**

Install a C++ compiler:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential

# Fedora
sudo dnf install gcc-c++

# Arch
sudo pacman -S base-devel
```

**"CMake not found"**

```bash
# Ubuntu/Debian
sudo apt-get install cmake

# Fedora
sudo dnf install cmake

# Arch
sudo pacman -S cmake
```

**Native widget opens with XCB/GLX or GLEW issues on Linux**

If the preview starts but the native OsmAnd widget fails later with GLX/XCB-related errors, make sure Qt is forced onto the desktop OpenGL path *before* `QApplication` is constructed. The standalone preview already applies the same idea in `src/maps/main.py`; use a similar guard in your own entry point if you embed `NativeOsmAndWidget`.

```python
import os
import sys
from pathlib import Path

from maps.map_sources import has_usable_osmand_native_widget


def _prepare_qt_runtime_for_maps() -> None:
    """Apply Linux Qt platform flags required by the native OsmAnd widget.

    The native OsmAnd widget expects Qt to use the XCB/GLX desktop OpenGL path
    on Linux; without these flags the application can start successfully and
    only fail later when the map view is opened with GLEW reporting missing GLX
    support.
    """

    if sys.platform != "linux":
        return

    if os.environ.get("IPHOTO_DISABLE_OPENGL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    maps_package_root = Path(__file__).resolve().parents[2] / "maps"
    if not has_usable_osmand_native_widget(maps_package_root):
        return

    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    if os.environ.get("QT_QPA_PLATFORM") == "xcb":
        os.environ.setdefault("QT_OPENGL", "desktop")
        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "xcb_glx")
```

Keep the following Linux runtime rules in mind when changing the native widget:

- A source checkout and a packaged/frozen app are different runtime targets. A
  preview that works from `python src/maps/main.py` does not prove a Nuitka
  bundle will survive opening the native map widget.
- For packaged Linux apps, force `QT_QPA_PLATFORM=xcb` before `QApplication`
  unless you are deliberately testing a Wayland opt-out path. This avoids the
  late `Failed to initialize GLEW: GLX 1.2 and up are not supported` failure
  when the map section is opened.
- Do not trust a generic Qt OpenGL probe as the only native-widget gate.
  Always keep `probe_native_widget_runtime(...)` in the decision path so the
  app can prefer the native widget only when its shared library actually loads,
  and fall back cleanly otherwise.
- The C++ bridge should request an explicit OpenGL-capable surface format. The
  current implementation sets the widget format from `QSurfaceFormat::defaultFormat()`
  and raises depth/stencil minima before `setFormat(...)`; keep that in place
  unless you have a stronger platform-specific reason to change it.
- After editing `tools/osmand_render_helper_native/src/osmand_native_map_widget.cpp`,
  rebuild the checked-in Linux artifacts under
  `tools/osmand_render_helper_native/dist-linux/` so the repository binaries
  match the source change.
- When validating Linux fixes, test both `python src/maps/main.py --backend native`
  and the final packaged application that embeds the widget. The regression only
  counts as fixed when the packaged UI can switch into the map view without the
  GLEW/GLX error.

If you consume this SDK from another project, carry the same startup guard into
that host application's entry point. The native widget's Linux assumptions are
not automatically repaired by embedding the library alone.

If you are not using the native widget on Linux, the helper-backed Python backend remains the safer default.

**Build output permissions or missing `.so` files**

Ensure proper permissions and that the build completed:

```bash
ls -la tools/osmand_render_helper_native/dist-linux/
chmod +x tools/osmand_render_helper_native/dist-linux/osmand_render_helper
```

## 3. macOS CMake Build

On macOS, build both the helper-backed Python renderer backend and the native Qt/OpenGL widget:

```bash
bash tools/osmand_render_helper_native/build_macos.sh
```

The script automatically:
- Uses `PYTHON` when provided, otherwise prefers the repository `.venv`
- Detects Qt6 from PySide6 when CMake development files are present, `qmake6`, Homebrew Qt, or Qt's installer layout
- Uses the active PySide6 Qt runtime for final Mach-O load paths when PySide6 is installed, even if the compile-time Qt SDK comes from Homebrew or the Qt installer
- Builds for the host architecture by default (`arm64` on Apple Silicon, `x86_64` on Intel)
- Writes runtime RPATHs so Python can load the native widget dylib and the helper can find Qt

Outputs:

- `tools/osmand_render_helper_native/dist-macosx/osmand_render_helper` for the Python backend
- `tools/osmand_render_helper_native/dist-macosx/osmand_native_widget.dylib` for native rendering

Run the preview with the helper-backed Python backend:

```bash
python -m maps.main --backend python
```

Run the preview with native rendering:

```bash
python -m maps.main --backend native
```

Control the build with environment variables:

```bash
export BUILD_TYPE=Debug
export JOBS=4
export MACOS_ARCH=arm64        # or x86_64
export MACOS_DEPLOYMENT_TARGET=12.1
export QT_ROOT=/path/to/Qt/6.x/macos
export QT_RUNTIME_LIB_DIR=/path/to/PySide6/Qt/lib
export PYTHON=/path/to/python

bash tools/osmand_render_helper_native/build_macos.sh
```

If you run the app from the source tree, no extra environment variable is needed once the files exist in `dist-macosx`. To use custom binary locations:

```bash
export IPHOTO_OSMAND_RENDER_HELPER=/path/to/osmand_render_helper
export IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY=/path/to/osmand_native_widget.dylib
```

## 4. Official OsmAnd MinGW Chain

This script stages a local workspace under `build\official-workspace`, creates the required junction layout, and runs the official OsmAnd MinGW build flow against the vendored sources in this repository.

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper_official.ps1
```

Outputs:

- `build\official-workspace\binaries\windows\gcc-amd64\Release\osmand_render_helper.exe`
- mirrored runtime files under `tools\osmand_render_helper_native\dist`

## 4. Official OsmAnd MSVC Chain

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

### Windows Default Runtime Paths

- OBF data: `src/maps/tiles/World_basemap_2.obf`
- OsmAnd resources: `vendor/osmand/resources`
- helper EXE (MinGW): `tools/osmand_render_helper_native/dist/osmand_render_helper.exe`
- native widget DLL (MSVC): `tools/osmand_render_helper_native/dist-msvc/osmand_native_widget.dll`

### Linux Default Runtime Paths

- OBF data: `src/maps/tiles/World_basemap_2.obf`
- OsmAnd resources: `vendor/osmand/resources`
- helper executable: `tools/osmand_render_helper_native/dist-linux/osmand_render_helper`
- native widget library: `tools/osmand_render_helper_native/dist-linux/osmand_native_widget.so` or `dist-linux/libosmand_native_widget.so`

The bundled `World_basemap_2.obf` file is only a default demo dataset. You can replace it with another OsmAnd `.obf` file, select a different file from the preview window, or point the runtime to a custom path through the environment variables below. Additional `.obf` downloads are available from the official OsmAnd download list: [https://download.osmand.net/list.php](https://download.osmand.net/list.php).

Override environment variables if needed (cross-platform):

- `IPHOTO_OSMAND_OBF_PATH`
- `IPHOTO_OSMAND_RESOURCES_ROOT`
- `IPHOTO_OSMAND_STYLE_PATH`
- `IPHOTO_OSMAND_RENDER_HELPER`
- `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY`

**Linux example**:

```bash
export IPHOTO_OSMAND_OBF_PATH="/home/user/maps/france.obf"
export IPHOTO_OSMAND_RESOURCES_ROOT="/home/user/osmand-resources"
export IPHOTO_OSMAND_RENDER_HELPER="/home/user/osmand_render_helper"
osmand-preview --backend python
```
