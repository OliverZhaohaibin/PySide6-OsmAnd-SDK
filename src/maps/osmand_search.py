"""Offline OsmAnd place search bindings used by the preview demo."""

from __future__ import annotations

import ctypes
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import PySide6
import shiboken6

from maps.errors import TileLoadingError
from maps.map_sources import MapSourceSpec, resolve_osmand_native_widget_library

_NATIVE_DLL_DIR_HANDLES: list[Any] = []
_PRELOADED_QT_LIBRARIES: list[ctypes.CDLL] = []


def _ensure_dll_directory(path: Path) -> None:
    if os.name == "nt" and hasattr(os, "add_dll_directory") and path.exists():
        _NATIVE_DLL_DIR_HANDLES.append(os.add_dll_directory(str(path)))


def _prepare_library_load(library_path: Path) -> None:
    if os.name == "nt":
        pyside_root = Path(PySide6.__file__).resolve().parent
        shiboken_root = Path(shiboken6.__file__).resolve().parent
        _ensure_dll_directory(pyside_root)
        _ensure_dll_directory(shiboken_root)

        package_root = Path(__file__).resolve().parents[2]
        dist_dir = library_path.parent
        for candidate_dist in [
            library_path.parent.parent.parent.parent / "tools" / "osmand_render_helper_native" / "dist-msvc",
            library_path.parent.parent.parent.parent / "tools" / "osmand_render_helper_native" / "dist",
            package_root / "tools" / "osmand_render_helper_native" / "dist-msvc",
            package_root / "tools" / "osmand_render_helper_native" / "dist",
        ]:
            if candidate_dist.is_dir():
                dist_dir = candidate_dist
                break

        _ensure_dll_directory(library_path.parent)
        if dist_dir != library_path.parent:
            _ensure_dll_directory(dist_dir)

    if os.name != "nt":
        pyside_root = Path(PySide6.__file__).resolve().parent
        qt_lib_dir = (pyside_root / "Qt" / "lib").resolve()
        for candidate_dir in [qt_lib_dir, library_path.parent.resolve()]:
            lib_dir = str(candidate_dir)
            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if lib_dir not in ld_path.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = lib_dir + (os.pathsep + ld_path if ld_path else "")
        if sys.platform == "darwin":
            for candidate_dir in [qt_lib_dir, library_path.parent.resolve()]:
                lib_dir = str(candidate_dir)
                dy_path = os.environ.get("DYLD_LIBRARY_PATH", "")
                if lib_dir not in dy_path.split(os.pathsep):
                    os.environ["DYLD_LIBRARY_PATH"] = lib_dir + (os.pathsep + dy_path if dy_path else "")
        elif sys.platform.startswith("linux") and qt_lib_dir.is_dir():
            preload_mode = getattr(ctypes, "RTLD_GLOBAL", 0)
            for library_name in [
                "libQt6Core.so.6",
                "libQt6Gui.so.6",
                "libQt6Widgets.so.6",
                "libQt6Network.so.6",
                "libQt6OpenGL.so.6",
                "libQt6OpenGLWidgets.so.6",
            ]:
                candidate = qt_lib_dir / library_name
                if candidate.exists():
                    _PRELOADED_QT_LIBRARIES.append(ctypes.CDLL(str(candidate), mode=preload_mode))


def _load_library(library_path: Path) -> ctypes.CDLL:
    _prepare_library_load(library_path)
    library = ctypes.CDLL(str(library_path))
    library.osmand_create_search_service.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    library.osmand_create_search_service.restype = ctypes.c_void_p
    library.osmand_destroy_search_service.argtypes = [ctypes.c_void_p]
    library.osmand_destroy_search_service.restype = None
    library.osmand_abort_search.argtypes = [ctypes.c_void_p]
    library.osmand_abort_search.restype = None
    library.osmand_search_query.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_int,
        ctypes.c_wchar_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    library.osmand_search_query.restype = ctypes.c_int
    return library


@dataclass(frozen=True)
class SearchSuggestion:
    display_name: str
    secondary_text: str
    longitude: float
    latitude: float
    source_kind: str
    match_kind: str


class OsmAndSearchService:
    """Thin ctypes wrapper around the native OsmAnd search bridge."""

    def __init__(self, map_source: MapSourceSpec | None = None) -> None:
        package_root = Path(__file__).resolve().parent
        self._map_source = (map_source or MapSourceSpec.osmand_default(package_root)).resolved(package_root)
        library_path = resolve_osmand_native_widget_library(package_root)
        if library_path is None:
            raise TileLoadingError("The native OsmAnd widget library is not available for search")

        self._library_path = library_path.resolve()
        self._library = _load_library(self._library_path)
        error_buffer = ctypes.create_unicode_buffer(4096)
        pointer = self._library.osmand_create_search_service(
            str(self._map_source.data_path),
            str(self._map_source.resources_root or ""),
            ctypes.cast(error_buffer, ctypes.c_void_p),
            len(error_buffer),
        )
        if not pointer:
            message = error_buffer.value or "Failed to create the native OsmAnd search service"
            raise TileLoadingError(message)

        self._service_pointer = ctypes.c_void_p(pointer)

    def abort(self) -> None:
        if getattr(self, "_service_pointer", None):
            self._library.osmand_abort_search(self._service_pointer)

    def shutdown(self) -> None:
        if getattr(self, "_service_pointer", None):
            self.abort()
            self._library.osmand_destroy_search_service(self._service_pointer)
            self._service_pointer = None

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        locale: str = "",
        include_poi_fallback: bool = True,
    ) -> list[SearchSuggestion]:
        trimmed_query = query.strip()
        if not trimmed_query:
            return []
        if len(trimmed_query) < 2 and all(ord(character) < 128 for character in trimmed_query):
            return []

        output_buffer = ctypes.create_unicode_buffer(32768)
        error_buffer = ctypes.create_unicode_buffer(4096)
        succeeded = self._library.osmand_search_query(
            self._service_pointer,
            trimmed_query,
            int(limit),
            locale,
            int(include_poi_fallback),
            ctypes.cast(output_buffer, ctypes.c_void_p),
            len(output_buffer),
            ctypes.cast(error_buffer, ctypes.c_void_p),
            len(error_buffer),
        )
        if not succeeded:
            message = error_buffer.value or "The native OsmAnd search query failed"
            raise TileLoadingError(message)

        raw_results = json.loads(output_buffer.value or "[]")
        suggestions: list[SearchSuggestion] = []
        for raw in raw_results:
            suggestions.append(
                SearchSuggestion(
                    display_name=str(raw.get("display_name", "")),
                    secondary_text=str(raw.get("secondary_text", "")),
                    longitude=float(raw.get("longitude", 0.0)),
                    latitude=float(raw.get("latitude", 0.0)),
                    source_kind=str(raw.get("source_kind", "")),
                    match_kind=str(raw.get("match_kind", "")),
                ),
            )
        return suggestions[: max(1, min(int(limit), 5))]

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass


__all__ = ["OsmAndSearchService", "SearchSuggestion"]
