"""Standalone entry point for the PySide6/OsmAnd preview application."""

from __future__ import annotations

if __package__ in {None, ""}:  # pragma: no cover - direct script bootstrap
    import sys
    from pathlib import Path

    _SRC_ROOT = Path(__file__).resolve().parents[1]
    if str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence, QOffscreenSurface, QOpenGLContext
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from maps.errors import TileLoadingError
from maps.map_sources import (
    MapBackendMetadata,
    MapSourceSpec,
    has_usable_osmand_default,
    has_usable_osmand_native_widget,
)
from maps.map_widget import MapGLWidget, MapWidget, NativeOsmAndWidget
from maps.map_widget._map_widget_base import MapWidgetBase
from maps.map_widget.native_osmand_widget import probe_native_widget_runtime


@dataclass(frozen=True)
class PreviewLaunchConfig:
    """Describe the backend setup requested for the standalone preview."""

    map_source: MapSourceSpec
    widget_class: type[MapWidgetBase]
    native_widget_class: type[MapWidgetBase] | None
    startup_message: str


def check_opengl_support() -> bool:
    """Return ``True`` when the system can create a basic OpenGL context."""

    try:
        surface = QOffscreenSurface()
        surface.create()
        if not surface.isValid():
            return False

        context = QOpenGLContext()
        if not context.create():
            return False

        if not context.makeCurrent(surface):
            return False

        context.doneCurrent()
        return True
    except Exception:
        return False


def choose_native_widget_class(
    package_root: Path,
    *,
    use_opengl: bool,
    prefer_native_widget: bool = True,
) -> tuple[type[MapWidgetBase] | None, str]:
    if not use_opengl:
        return None, "OpenGL support unavailable. Falling back to the helper-backed CPU renderer."

    if not prefer_native_widget:
        return None, "OpenGL support detected. Using the helper-backed Python OBF renderer."

    if not has_usable_osmand_native_widget(package_root):
        return None, "OpenGL support detected. Native widget unavailable, using the Python OBF renderer."

    is_available, reason = probe_native_widget_runtime(package_root)
    if is_available:
        return NativeOsmAndWidget, "OpenGL support detected. Using the native OsmAnd widget when available."

    detail = f" Native widget disabled: {reason}." if reason else ""
    return None, f"OpenGL support detected.{detail} Using the Python OBF renderer."


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the CLI parser used by the standalone preview entry point."""

    parser = argparse.ArgumentParser(description="Preview OsmAnd OBF rendering backends")
    parser.add_argument(
        "--backend",
        choices=("auto", "native", "python"),
        default="auto",
        help="Select the startup renderer explicitly instead of auto-detecting it.",
    )
    parser.add_argument(
        "--center",
        nargs=2,
        metavar=("LON", "LAT"),
        type=float,
        help="Center the initial view on the provided longitude/latitude pair.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        help="Set the initial zoom level after the window has been created.",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="Save a screenshot after startup and exit once the image is written.",
    )
    parser.add_argument(
        "--capture-delay-ms",
        type=int,
        default=1500,
        help="How long to wait before taking --screenshot (default: 1500).",
    )
    return parser


def choose_launch_configuration(
    package_root: Path,
    *,
    use_opengl: bool,
    backend: str,
) -> PreviewLaunchConfig:
    """Resolve the startup backend requested on the command line."""

    widget_cls: type[MapWidgetBase] = MapGLWidget if use_opengl else MapWidget
    normalized_backend = backend.strip().lower()
    default_source = MapSourceSpec.osmand_default(package_root)

    if normalized_backend == "auto":
        native_widget_cls, startup_message = choose_native_widget_class(
            package_root,
            use_opengl=use_opengl,
        )
        if native_widget_cls is None and not has_usable_osmand_default(package_root):
            raise TileLoadingError(
                "Neither the native widget nor the helper-backed Python renderer is available",
            )
        return PreviewLaunchConfig(
            map_source=default_source,
            widget_class=widget_cls,
            native_widget_class=native_widget_cls,
            startup_message=startup_message,
        )

    if normalized_backend == "native":
        if not use_opengl:
            raise TileLoadingError("OpenGL support is unavailable, so the native OsmAnd widget can not be forced")
        if not has_usable_osmand_native_widget(package_root):
            raise TileLoadingError("The native OsmAnd widget library is not available")
        is_available, reason = probe_native_widget_runtime(package_root)
        if not is_available:
            detail = f": {reason}" if reason else ""
            raise TileLoadingError(f"The native OsmAnd widget failed its runtime probe{detail}")
        return PreviewLaunchConfig(
            map_source=default_source,
            widget_class=widget_cls,
            native_widget_class=NativeOsmAndWidget,
            startup_message="OpenGL support detected. Forcing the native OsmAnd widget.",
        )

    if normalized_backend == "python":
        if not has_usable_osmand_default(package_root):
            raise TileLoadingError(
                "The OsmAnd helper backend is unavailable, so the Python OBF renderer can not be forced",
            )
        renderer_label = "GPU accelerated" if use_opengl else "CPU"
        return PreviewLaunchConfig(
            map_source=default_source,
            widget_class=widget_cls,
            native_widget_class=None,
            startup_message=f"Forcing the {renderer_label} Python OBF renderer.",
        )

    raise ValueError(f"unsupported backend mode: {backend}")


def _backend_kind_for_widget(
    map_widget: MapWidgetBase,
    *,
    map_source: MapSourceSpec,
) -> str:
    del map_source
    if isinstance(map_widget, NativeOsmAndWidget):
        return "osmand_native"
    return "osmand_python"


def _confirmed_gl_state(
    map_widget: MapWidgetBase,
    *,
    backend_kind: str,
) -> str:
    if backend_kind == "osmand_native":
        return "true"
    if isinstance(map_widget, MapGLWidget):
        return "true"
    if isinstance(map_widget, MapWidget):
        return "false"
    return "unknown"


def format_map_runtime_diagnostics(
    map_widget: MapWidgetBase,
    *,
    map_source: MapSourceSpec,
) -> str:
    """Return a one-line runtime summary that proves whether GL is active."""

    backend_kind = _backend_kind_for_widget(map_widget, map_source=map_source)
    metadata = map_widget.map_backend_metadata()
    event_target = map_widget.event_target()
    event_target_name = getattr(event_target, "objectName", lambda: "")()
    if not event_target_name:
        event_target_name = type(event_target).__name__
    native_library_path = getattr(map_widget, "loaded_library_path", lambda: None)()
    native_library_suffix = ""
    if native_library_path:
        native_library_suffix = f" native_library={native_library_path}"

    return (
        "[maps.main] "
        f"backend={backend_kind} "
        f"confirmed_gl={_confirmed_gl_state(map_widget, backend_kind=backend_kind)} "
        f"widget={type(map_widget).__name__} "
        f"event_target={event_target_name} "
        f"source={map_source.kind} "
        f"tile_kind={metadata.tile_kind} "
        f"tile_scheme={metadata.tile_scheme}"
        f"{native_library_suffix}"
    )


def format_status_message(
    *,
    backend_label: str,
    requested_source: MapSourceSpec,
    metadata: MapBackendMetadata,
    zoom: float,
    longitude: float,
    latitude: float,
) -> str:
    """Summarize the current map state for the status bar."""

    del metadata
    source_path = Path(requested_source.data_path).name
    return (
        f"{backend_label} | Zoom {zoom:.2f} | Center {latitude:.4f}, {longitude:.4f}"
        f" | Source {source_path}"
    )


class MainWindow(QMainWindow):
    """Primary application window that hosts an interactive map widget."""

    PAN_FRACTION = 0.18

    def __init__(
        self,
        *,
        map_source: MapSourceSpec | None = None,
        widget_class: type[MapWidgetBase] | None = None,
        native_widget_class: type[MapWidgetBase] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("OsmAnd Preview")
        self.resize(1280, 860)

        self._package_root = Path(__file__).resolve().parent
        self._widget_cls: type[MapWidgetBase] = widget_class or MapWidget
        self._native_widget_cls = native_widget_class
        self._runtime_diagnostics = ""
        self._map_source = (map_source or MapSourceSpec.osmand_default(self._package_root)).resolved(
            self._package_root,
        )

        self._map_widget: MapWidgetBase = self._create_map_widget(map_source=self._map_source)
        self._set_central_map(self._map_widget)

        self._create_actions()
        self._create_menus()
        self.statusBar().showMessage("Ready")
        self._refresh_window_chrome()
        self._announce_backend_state()

    def _create_actions(self) -> None:
        self._action_zoom_in = QAction("Zoom In", self)
        self._action_zoom_in.setShortcuts([QKeySequence("+"), QKeySequence("=")])
        self._action_zoom_in.triggered.connect(self._zoom_in)

        self._action_zoom_out = QAction("Zoom Out", self)
        self._action_zoom_out.setShortcuts([QKeySequence("-"), QKeySequence("_")])
        self._action_zoom_out.triggered.connect(self._zoom_out)

        self._action_reset_view = QAction("Reset View", self)
        self._action_reset_view.setShortcuts([QKeySequence("Home"), QKeySequence("R")])
        self._action_reset_view.triggered.connect(self._reset_view)

        self._action_pan_left = QAction("Pan Left", self)
        self._action_pan_left.setShortcuts([QKeySequence("Left"), QKeySequence("A")])
        self._action_pan_left.triggered.connect(lambda: self._pan_by_fraction(-self.PAN_FRACTION, 0.0))

        self._action_pan_right = QAction("Pan Right", self)
        self._action_pan_right.setShortcuts([QKeySequence("Right"), QKeySequence("D")])
        self._action_pan_right.triggered.connect(lambda: self._pan_by_fraction(self.PAN_FRACTION, 0.0))

        self._action_pan_up = QAction("Pan Up", self)
        self._action_pan_up.setShortcuts([QKeySequence("Up"), QKeySequence("W")])
        self._action_pan_up.triggered.connect(lambda: self._pan_by_fraction(0.0, -self.PAN_FRACTION))

        self._action_pan_down = QAction("Pan Down", self)
        self._action_pan_down.setShortcuts([QKeySequence("Down"), QKeySequence("S")])
        self._action_pan_down.triggered.connect(lambda: self._pan_by_fraction(0.0, self.PAN_FRACTION))

        self._action_open_map_source = QAction("Select OBF Source...", self)
        self._action_open_map_source.triggered.connect(self._open_map_source)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self._action_zoom_in)
        view_menu.addAction(self._action_zoom_out)
        view_menu.addAction(self._action_reset_view)

        navigate_menu = menu_bar.addMenu("Navigate")
        navigate_menu.addAction(self._action_pan_left)
        navigate_menu.addAction(self._action_pan_right)
        navigate_menu.addAction(self._action_pan_up)
        navigate_menu.addAction(self._action_pan_down)

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self._action_open_map_source)

    def _create_map_widget(self, *, map_source: MapSourceSpec) -> MapWidgetBase:
        if self._native_widget_cls is not None:
            try:
                return self._native_widget_cls(map_source=map_source)
            except Exception as exc:  # pragma: no cover - best effort error reporting
                print(
                    f"[main] NativeOsmAndWidget failed: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                self.statusBar().showMessage(
                    f"Native OsmAnd widget unavailable, falling back to the Python renderer: {exc}",
                    8000,
                )

        try:
            return self._widget_cls(map_source=map_source)
        except TileLoadingError:
            raise
        except Exception as exc:  # pragma: no cover - best effort error reporting
            if self._widget_cls is MapWidget:
                raise

            QMessageBox.warning(
                self,
                "GPU Acceleration Disabled",
                "The OpenGL based map view failed to initialize.\n"
                "The application will continue with the CPU renderer instead.\n\n"
                f"Details: {exc}",
            )
            self._widget_cls = MapWidget
            return MapWidget(map_source=map_source)

    def _zoom_in(self) -> None:
        self._map_widget.set_zoom(self._map_widget.zoom * 1.5)

    def _zoom_out(self) -> None:
        self._map_widget.set_zoom(self._map_widget.zoom / 1.5)

    def _reset_view(self) -> None:
        self._map_widget.reset_view()

    def _pan_by_fraction(self, fraction_x: float, fraction_y: float) -> None:
        self._map_widget.pan_by_pixels(
            self._map_widget.width() * fraction_x,
            self._map_widget.height() * fraction_y,
        )

    def _open_map_source(self) -> None:
        current_path = str(self._map_source.data_path)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OBF Source",
            current_path,
            "OBF Files (*.obf);;All Files (*)",
        )
        if not path:
            return

        default_source = MapSourceSpec.osmand_default(self._package_root).resolved(self._package_root)
        new_source = MapSourceSpec(
            kind="osmand_obf",
            data_path=path,
            resources_root=default_source.resources_root,
            style_path=default_source.style_path,
        ).resolved(self._package_root)
        try:
            widget = self._create_map_widget(map_source=new_source)
        except TileLoadingError as exc:
            QMessageBox.critical(self, "Error", f"Unable to open the OBF source:\n{exc}")
            return

        self._map_source = new_source
        self._set_central_map(widget)
        self._announce_backend_state()

    def _active_backend_label(self) -> str:
        if isinstance(self._map_widget, NativeOsmAndWidget):
            return "Native OsmAnd Widget"
        return "Python OBF Raster"

    def _refresh_window_chrome(self) -> None:
        self._update_window_title()
        self._update_status_bar()

    def _update_window_title(self) -> None:
        self.setWindowTitle(
            f"OsmAnd Preview - {self._active_backend_label()} - Zoom {self._map_widget.zoom:.2f}",
        )

    def _update_status_bar(self) -> None:
        longitude, latitude = self._map_widget.center_lonlat()
        status_text = format_status_message(
            backend_label=self._active_backend_label(),
            requested_source=self._map_source,
            metadata=self._map_widget.map_backend_metadata(),
            zoom=self._map_widget.zoom,
            longitude=longitude,
            latitude=latitude,
        )
        self.statusBar().showMessage(status_text)

    def _announce_backend_state(self) -> None:
        self._refresh_window_chrome()
        self._emit_runtime_diagnostics()

    def _emit_runtime_diagnostics(self) -> None:
        self._runtime_diagnostics = format_map_runtime_diagnostics(
            self._map_widget,
            map_source=self._map_source,
        )
        print(self._runtime_diagnostics, flush=True)

    def runtime_diagnostics(self) -> str:
        """Return the latest runtime diagnostics emitted by the preview window."""

        return self._runtime_diagnostics

    def apply_initial_view(
        self,
        *,
        center: tuple[float, float] | None = None,
        zoom: float | None = None,
    ) -> None:
        """Apply optional startup view overrides for debugging."""

        if center is not None:
            self._map_widget.center_on(center[0], center[1])
        if zoom is not None:
            self._map_widget.set_zoom(float(zoom))
        self._refresh_window_chrome()

    def capture_screenshot(self, destination: Path) -> bool:
        """Save a screenshot of the current preview window."""

        output_path = destination.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap = self.grab()
        if pixmap.isNull():
            return False
        return pixmap.save(str(output_path))

    def _handle_view_changed(self, center_x: float, center_y: float, zoom: float) -> None:
        del center_x, center_y, zoom
        self._refresh_window_chrome()

    def _set_central_map(self, widget: MapWidgetBase) -> None:
        old = self.takeCentralWidget()
        if old is not None:
            if hasattr(old, "viewChanged"):
                try:
                    old.viewChanged.disconnect(self._handle_view_changed)  # type: ignore[attr-defined]
                except (RuntimeError, TypeError):
                    pass
            if hasattr(old, "shutdown"):
                old.shutdown()  # type: ignore[call-arg]
            old.deleteLater()

        self._map_widget = widget
        self.setCentralWidget(self._map_widget)
        if hasattr(self._map_widget, "viewChanged"):
            self._map_widget.viewChanged.connect(self._handle_view_changed)  # type: ignore[attr-defined]
        self._map_widget.setFocus()
        self._refresh_window_chrome()


def _schedule_screenshot_capture(
    app: QApplication,
    window: MainWindow,
    screenshot_path: Path,
    *,
    capture_delay_ms: int,
) -> None:
    """Capture a screenshot after the native/Python renderer settles."""

    delay_ms = max(0, int(capture_delay_ms))

    def _capture_and_exit() -> None:
        if window.capture_screenshot(screenshot_path):
            print(f"[maps.main] screenshot={screenshot_path.resolve()}", flush=True)
            app.exit(0)
            return

        print(
            f"[maps.main] failed to save screenshot to {screenshot_path.resolve()}",
            file=sys.stderr,
            flush=True,
        )
        app.exit(1)

    QTimer.singleShot(delay_ms, _capture_and_exit)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    parsed_args = build_argument_parser().parse_args(arguments)
    app = QApplication([Path(__file__).name, *arguments])

    package_root = Path(__file__).resolve().parent
    use_opengl = check_opengl_support()
    launch_config = choose_launch_configuration(
        package_root,
        use_opengl=use_opengl,
        backend=parsed_args.backend,
    )
    print(launch_config.startup_message, flush=True)

    try:
        window = MainWindow(
            map_source=launch_config.map_source,
            widget_class=launch_config.widget_class,
            native_widget_class=launch_config.native_widget_class,
        )
    except TileLoadingError as exc:
        QMessageBox.critical(None, "Error", f"Failed to initialize map:\n{exc}")
        return 1

    if parsed_args.center is not None or parsed_args.zoom is not None:
        center = tuple(parsed_args.center) if parsed_args.center is not None else None
        window.apply_initial_view(center=center, zoom=parsed_args.zoom)

    window.show()
    if parsed_args.screenshot is not None:
        _schedule_screenshot_capture(
            app,
            window,
            parsed_args.screenshot,
            capture_delay_ms=parsed_args.capture_delay_ms,
        )
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
