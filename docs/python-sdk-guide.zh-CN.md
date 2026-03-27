# PySide6-OsmAnd-SDK Python 地图开发指南

这份文档面向想用 `PySide6-OsmAnd-SDK` 做 Python 地图开发的开发者，重点说明这个仓库当前能做什么、推荐怎样接入、运行时依赖放在哪里，以及二次开发时应该优先使用哪些 API。

如果你还没有把本仓库跑起来，建议先看一眼 [README](../README.md) 和 [BUILD.md](../BUILD.md)，再回到这里按“先跑通预览，再嵌入自己的窗口”的节奏往下做。

## 1. 先理解这个项目是什么

这个仓库现在更接近一个“可运行的 SDK 工作区”，而不是一个只靠 `pip install` 就能独立工作的纯 Python 地图库。

它由 4 层组成：

1. `vendor/osmand/...`
   OsmAnd 原生核心代码和资源文件。
2. `tools/osmand_render_helper_native/...`
   本地构建脚本、辅助渲染程序、原生 Qt Widget 桥接代码。
3. `src/maps/...`
   PySide6 侧的地图控件、预览程序、路径解析、后端封装。
4. `.obf` 地图数据与渲染样式
   真正决定地图内容和外观的离线数据与样式文件。

所以，开发时最推荐的模式是：

- 把这个仓库作为你的地图 SDK 工作区保留在本地
- 用 `python -m pip install -e .` 以可编辑模式安装
- 在仓库内构建 helper 或 native widget
- 在你的 PySide6 程序里直接 import `maps`

如果你想把它嵌入另一个项目，也可以，但要自己明确提供运行时资源路径，而不要完全依赖默认路径推断。

## 2. 这个 SDK 目前提供哪几种地图后端

当前主要有两条可用链路。

### 2.1 `NativeOsmAndWidget`

这是原生 C++ 的 OsmAnd Qt 地图控件，通过 DLL 桥接到 PySide6。

特点：

- 渲染逻辑更接近原生 OsmAnd 控件
- 需要 OpenGL
- 目前只支持 Windows
- 依赖 `osmand_native_widget.dll`
- DLL 路径不是 `MapSourceSpec` 的一部分，而是通过默认仓库路径或环境变量解析

适合：

- 你明确在 Windows 上开发
- 你已经构建好 native widget DLL
- 你希望尽量接近原生 OsmAnd 运行方式

### 2.2 Python 控件 + helper 渲染

这是当前更容易上手的一条路径。Python 侧控件负责交互和显示，真正的 OBF 渲染由外部 helper 进程完成，再把瓦片结果交回 Qt 显示。

这条路径又分成两个前端：

- `MapGLWidget`
  使用 `QOpenGLWidget` 承载画面，交互更流畅，推荐优先使用。
- `MapWidget`
  使用普通 `QWidget` + `QPainter`，在没有 OpenGL 时也能工作。

特点：

- 上手最简单
- `MapSourceSpec` 可以显式指定 `.obf`、资源目录、样式文件、helper 命令
- 渲染结果是栅格瓦片
- SDK 已经帮你处理了后台线程和瓦片请求

适合：

- 先把地图能力接进 Python 桌面应用
- 需要离线 `.obf` 地图浏览
- 想先稳定跑通，再考虑 native widget

## 3. 推荐的接入顺序

推荐按下面顺序推进：

1. 先跑通预览程序，确认运行时齐全
2. 再在自己的 `QMainWindow` 里嵌入 `MapGLWidget` 或 `MapWidget`
3. 跑通以后再切换自定义 `.obf`、样式文件和 native widget
4. 业务层的标注、弹窗、交互面板，再叠加到地图控件外层

这样做的好处是你能先把“地图能不能显示”这个问题和“业务 UI 怎么设计”分开。

## 4. 5 分钟跑通仓库自带预览

### 4.1 安装 Python 依赖

在仓库根目录执行：

```powershell
python -m pip install -e .
```

推荐使用 `-e`，因为当前默认路径解析是围绕仓库目录结构设计的。

### 4.2 至少构建一种运行时

如果你只是想先把 Python 地图跑起来，优先构建 helper：

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_helper.ps1
```

如果你要尝试原生嵌入控件：

```powershell
powershell -ExecutionPolicy Bypass -File tools\osmand_render_helper_native\build_native_widget_msvc.ps1
```

更完整的构建说明见 [BUILD.md](../BUILD.md)。

### 4.3 启动预览

```powershell
osmand-preview --backend auto
```

也可以直接运行入口文件：

```powershell
python src\maps\main.py --backend auto
```

常用参数：

- `--backend auto`
  自动选择后端。优先 native widget，其次 Python 路径。
- `--backend native`
  强制使用原生 widget。
- `--backend python`
  强制使用 Python + helper 渲染路径。
- `--center <lon> <lat>`
  设置初始中心点，顺序是经度、纬度。
- `--zoom <value>`
  设置初始缩放。
- `--screenshot <path>`
  启动后自动截图并退出。

例如：

```powershell
osmand-preview --backend python --center 2.3522 48.8566 --zoom 8 --screenshot .\paris.png
```

### 4.4 预览程序里的交互

预览窗口本身已经带了一些基础操作，方便你判断运行是否正常：

- 鼠标拖拽平移
- 鼠标滚轮缩放
- `+` / `=`
  放大
- `-` / `_`
  缩小
- `Home` / `R`
  重置视图
- 方向键或 `W A S D`
  平移
- `File -> Select OBF Source...`
  切换 `.obf` 地图文件

## 5. 你自己的 PySide6 应用应该怎么接

最常见的做法，是把地图控件当成一个普通 Qt Widget 嵌入到你的主窗口里。

### 5.1 最小可用示例：直接使用 `MapGLWidget`

如果你已经构建好了 helper，这通常是第一选择。

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

这段代码依赖默认运行时路径，也就是：

- `.obf`: `src/maps/tiles/World_basemap_2.obf`
- 资源目录: `vendor/osmand/resources`
- helper: `tools/osmand_render_helper_native/dist/osmand_render_helper.exe`

如果这些文件不在默认位置，请看后面的 `MapSourceSpec` 配置方式。

### 5.2 没有 OpenGL 时使用 `MapWidget`

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

`MapWidget` 仍然走 helper 渲染，只是显示层使用普通 `QWidget`。

### 5.3 自动选择最佳控件

如果你希望“有 native widget 就用 native，没有就退回 `MapGLWidget`，再不行用 `MapWidget`”，可以直接按仓库现有逻辑封装一层：

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

这个策略基本和预览程序一致，适合作为你自己应用里的默认后端选择器。

## 6. 自定义 `.obf`、资源目录、样式文件

真正推荐你在业务程序里使用的配置入口是 `MapSourceSpec`。

### 6.1 `MapSourceSpec` 是什么

它描述一张地图从哪里来，核心字段有：

- `kind`
  当前只支持 `"osmand_obf"`
- `data_path`
  `.obf` 地图文件
- `resources_root`
  OsmAnd 资源目录
- `style_path`
  渲染样式 XML
- `helper_command`
  helper 可执行文件命令，通常是 `("...\\osmand_render_helper.exe",)`

### 6.2 显式指定运行时资源

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

### 6.3 关于路径的一个重要细节

`MapSourceSpec` 里的相对路径不是按你当前工作目录解析，而是按 `maps` 包目录解析。

这意味着：

- 在业务项目里，尽量传绝对路径
- 如果你要传相对路径，最好先在你自己的代码里用 `Path(...).resolve()` 处理好
- `helper_command` 也建议直接传绝对路径

### 6.4 默认样式是什么

仓库默认样式不是 `default.render.xml`，而是：

```text
vendor/osmand/resources/rendering_styles/snowmobile.render.xml
```

如果你想要更常规的地图视觉风格，通常会改成：

```text
vendor/osmand/resources/rendering_styles/default.render.xml
```

或者其它 OsmAnd style XML。

## 7. 常用控件 API

`MapWidget`、`MapGLWidget`、`NativeOsmAndWidget` 现在暴露的核心交互方法基本一致。

### 7.1 常用方法

- `zoom`
  当前缩放级别。
- `set_zoom(zoom: float)`
  设置缩放，内部会自动夹在后端允许范围内。
- `reset_view()`
  视图回到默认中心与默认缩放。
- `pan_by_pixels(delta_x, delta_y)`
  按屏幕像素平移。
- `center_lonlat() -> tuple[float, float]`
  返回当前中心点，顺序是 `(lon, lat)`。
- `center_on(lon, lat)`
  将地图中心移到指定经纬度。
- `focus_on(lon, lat, zoom_delta=1.0)`
  先居中再放大一点，适合“定位到对象”。
- `project_lonlat(lon, lat) -> QPointF | None`
  把地理坐标投影到当前控件的屏幕坐标。
- `map_backend_metadata()`
  读取后端能力，例如最小缩放、最大缩放。
- `shutdown()`
  释放后台线程或轮询资源。控件销毁时通常会自动处理，但你手动替换控件时最好显式调用。

### 7.2 Qt 信号

- `viewChanged(float center_x, float center_y, float zoom)`
- `panned(QPointF delta)`
- `panFinished()`

注意：`viewChanged` 发出的 `center_x`、`center_y` 是归一化后的墨卡托坐标，不是经纬度。

如果你想拿到真实经纬度，应该在槽函数里调用 `center_lonlat()`：

```python
def on_view_changed(_x: float, _y: float, zoom: float) -> None:
    lon, lat = map_widget.center_lonlat()
    print(f"center=({lon:.6f}, {lat:.6f}) zoom={zoom:.2f}")


map_widget.viewChanged.connect(on_view_changed)
```

### 7.3 读取后端能力

```python
metadata = map_widget.map_backend_metadata()
print(metadata.min_zoom, metadata.max_zoom, metadata.tile_kind, metadata.tile_scheme)
```

对业务代码来说，最有用的通常是：

- `min_zoom`
- `max_zoom`
- `provides_place_labels`

## 8. 怎么给地图叠加自己的业务标记

当前 SDK 的重点是“地图底图显示”和“交互视图控制”，还没有现成的高层 marker / polyline / polygon 业务 API。

现阶段最实用的方式是：

1. 用地图控件显示底图
2. 用 `project_lonlat()` 把经纬度转成屏幕坐标
3. 在地图控件上方叠加你自己的 Qt UI 或自绘 overlay

例如，用一个 `QLabel` 当定位图标：

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

这个思路适合做：

- POI 标记
- 当前设备位置
- 图片定位点
- 选中对象气泡

## 9. 环境变量与运行时覆盖

当默认仓库路径不适用时，可以通过环境变量覆盖。

### 9.1 地图数据与渲染资源

| 环境变量 | 作用 |
| --- | --- |
| `IPHOTO_OSMAND_OBF_PATH` | 指定 `.obf` 地图文件 |
| `IPHOTO_OSMAND_RESOURCES_ROOT` | 指定 `vendor/osmand/resources` 替代目录 |
| `IPHOTO_OSMAND_STYLE_PATH` | 指定 style XML |
| `IPHOTO_OSMAND_RENDER_HELPER` | 指定 helper 命令或可执行文件路径 |
| `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY` | 指定 native widget DLL 路径 |

PowerShell 示例：

```powershell
$env:IPHOTO_OSMAND_OBF_PATH = "D:\maps\france_europe.obf"
$env:IPHOTO_OSMAND_STYLE_PATH = "D:\python_code\iPhoto\PySide6-OsmAnd-SDK\vendor\osmand\resources\rendering_styles\default.render.xml"
$env:IPHOTO_OSMAND_RENDER_HELPER = "D:\python_code\iPhoto\PySide6-OsmAnd-SDK\tools\osmand_render_helper_native\dist\osmand_render_helper.exe"
osmand-preview --backend python
```

### 9.2 Qt / MinGW 运行时

helper 启动时还会尝试自动补齐 Qt 和 MinGW 的 DLL 搜索路径。如果你的 Qt 安装位置和仓库默认值不同，可以设置：

| 环境变量 | 作用 |
| --- | --- |
| `IPHOTO_OSMAND_QT_ROOT` | Qt 根目录，例如 `C:\Qt\6.10.1\mingw_64` |
| `IPHOTO_OSMAND_MINGW_ROOT` | MinGW 根目录，例如 `C:\Qt\Tools\mingw1310_64` |

这两个变量主要用于解决 helper 能启动但找不到依赖 DLL 的问题。

## 10. 不同开发目标下，应该选哪个控件

### 10.1 想最快接进业务应用

优先：

- `MapGLWidget`

理由：

- 路径和资源都可以通过 `MapSourceSpec` 明确指定
- 对 Python 应用更友好
- 不要求你先处理 native widget 的 DLL 桥接问题

### 10.2 机器没有可用 OpenGL

使用：

- `MapWidget`

理由：

- 仍可保留 OBF 离线渲染能力
- 只是显示层退回普通 `QWidget`

### 10.3 需要更接近原生 OsmAnd 的控件行为

使用：

- `NativeOsmAndWidget`

前提：

- Windows
- 已构建 native widget DLL
- DLL 可被成功加载

## 11. 这个仓库当前的几个重要边界

这些点建议在接项目时一开始就知道：

- 当前公开支持的地图源类型只有 `osmand_obf`
- native widget 目前只支持 Windows
- `MapWidget` / `MapGLWidget` 构造参数里的 `tile_root`、`style_path` 现在只是兼容字段，真正应通过 `MapSourceSpec` 配置
- `set_city_annotations()` 和 `city_at()` 目前更多是兼容保留接口，不是完整的标注系统
- SDK 现在没有现成的高层业务 overlay API，标记和面板建议由你自己的 Qt 层处理
- 默认路径推断依赖仓库目录结构，所以“源码仓库 + editable install”最省心
- 如果你把它单独打包到别的项目里，最好显式提供 `.obf`、资源目录、样式和 helper 路径

另外还有一个需要特别注意的点：

- Python helper 路径可以通过 `MapSourceSpec.helper_command` 显式传入
- 但 native widget DLL 路径不在 `MapSourceSpec` 中，目前通过默认仓库位置或 `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY` 解析

如果你想做独立部署，这一点很重要。

## 12. 常见问题排查

### 12.1 提示 helper 没配置

常见报错方向：

- `OsmAnd helper command not configured`
- `Unable to start OsmAnd helper`

排查顺序：

1. 先确认你已经执行过 `build_helper.ps1`
2. 再确认 `tools/osmand_render_helper_native/dist/osmand_render_helper.exe` 存在
3. 如果 helper 不在默认位置，就设置 `IPHOTO_OSMAND_RENDER_HELPER`

### 12.2 提示 `.obf`、resources 或 style 不存在

这通常是路径问题。

优先检查：

- `data_path`
- `resources_root`
- `style_path`

建议直接改成绝对路径，不要依赖当前工作目录。

### 12.3 native widget DLL 找不到或加载失败

优先检查：

1. 是否已经执行 `build_native_widget_msvc.ps1`
2. `IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY` 是否指向真实 DLL
3. 是否在 Windows 上运行
4. Qt / PySide6 / 依赖 DLL 是否都在可搜索路径里

### 12.4 helper 能启动，但渲染失败或闪退

重点检查：

- `IPHOTO_OSMAND_QT_ROOT`
- `IPHOTO_OSMAND_MINGW_ROOT`
- helper 所在目录里是否带齐运行时 DLL

### 12.5 地图能显示，但我想换成自己的地图风格

不要改控件类，先换 `style_path`。

例如从默认 `snowmobile.render.xml` 切到 `default.render.xml`，通常就能得到更常规的地图视觉。

## 13. 推荐的项目集成方式

如果你的业务项目要长期使用这个 SDK，比较稳妥的接入方式通常是：

1. 保留这个仓库作为一个独立目录或 git submodule
2. 业务程序里显式构造 `MapSourceSpec`
3. 所有路径都用绝对路径
4. 初期统一使用 `MapGLWidget`
5. 真正需要 native widget 时，再针对 Windows 版本单独启用

如果你只是想快速验证想法，最简单的路线就是：

1. `python -m pip install -e .`
2. `build_helper.ps1`
3. `MapGLWidget()` 直接嵌到你的 `QMainWindow`

这条路径最短，也最容易定位问题。
