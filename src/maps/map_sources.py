"""Definitions for selecting and describing OsmAnd-backed map sources."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DEFAULT_OSMAND_OBF_RELATIVE_PATH = Path("src") / "maps" / "tiles" / "World_basemap_2.obf"
DEFAULT_OSMAND_RESOURCES_RELATIVE_PATH = Path("vendor") / "osmand" / "resources"
DEFAULT_OSMAND_STYLE_RELATIVE_PATH = (
    DEFAULT_OSMAND_RESOURCES_RELATIVE_PATH / "rendering_styles" / "snowmobile.render.xml"
)

ENV_OSMAND_HELPER = "IPHOTO_OSMAND_RENDER_HELPER"
ENV_OSMAND_NATIVE_WIDGET_LIBRARY = "IPHOTO_OSMAND_NATIVE_WIDGET_LIBRARY"
ENV_OSMAND_OBF_PATH = "IPHOTO_OSMAND_OBF_PATH"
ENV_OSMAND_RESOURCES_ROOT = "IPHOTO_OSMAND_RESOURCES_ROOT"
ENV_OSMAND_STYLE_PATH = "IPHOTO_OSMAND_STYLE_PATH"

DEFAULT_HELPER_RELATIVE_PATHS = (
    Path("tools") / "osmand_render_helper_native" / "dist" / "osmand_render_helper.exe",
)

DEFAULT_NATIVE_WIDGET_RELATIVE_PATHS = (
    Path("tools") / "osmand_render_helper_native" / "dist-msvc" / "osmand_native_widget.dll",
    Path("tools") / "osmand_render_helper_native" / "dist" / "osmand_native_widget.dll",
    Path("tools") / "osmand_render_helper_native" / "dist" / "libosmand_native_widget.dll",
)


@dataclass(frozen=True)
class MapBackendMetadata:
    """Describe the capabilities of a concrete map backend."""

    min_zoom: float
    max_zoom: float
    provides_place_labels: bool
    tile_kind: Literal["raster"]
    tile_scheme: Literal["xyz"] = "xyz"
    fetch_max_zoom: int | None = None


@dataclass(frozen=True)
class MapSourceSpec:
    """Describe how the preview obtains its OsmAnd background data."""

    kind: Literal["osmand_obf"]
    data_path: Path | str
    resources_root: Path | str | None = None
    style_path: Path | str | None = None
    helper_command: tuple[str, ...] | None = None

    def resolved(self, package_root: Path) -> "MapSourceSpec":
        """Return a copy whose filesystem paths are absolute."""

        data_path = _resolve_path(self.data_path, package_root)
        resources_root = _resolve_optional_path(self.resources_root, package_root)
        style_path = _resolve_optional_path(self.style_path, package_root)
        helper_command = self.helper_command or resolve_osmand_helper_command(package_root)
        return MapSourceSpec(
            kind=self.kind,
            data_path=data_path,
            resources_root=resources_root,
            style_path=style_path,
            helper_command=helper_command,
        )

    @classmethod
    def osmand_default(cls, package_root: Path | None = None) -> "MapSourceSpec":
        """Return the bundled OBF source backed by vendored OsmAnd resources."""

        root = package_root or _package_root()
        repo_root = _repo_root(root)
        return cls(
            kind="osmand_obf",
            data_path=_resolve_env_or_default(
                ENV_OSMAND_OBF_PATH,
                root / "tiles" / "World_basemap_2.obf",
                repo_root,
            ),
            resources_root=_resolve_env_or_default(
                ENV_OSMAND_RESOURCES_ROOT,
                repo_root / DEFAULT_OSMAND_RESOURCES_RELATIVE_PATH,
                repo_root,
            ),
            style_path=_resolve_env_or_default(
                ENV_OSMAND_STYLE_PATH,
                repo_root / DEFAULT_OSMAND_STYLE_RELATIVE_PATH,
                repo_root,
            ),
        )

    @classmethod
    def default(cls, package_root: Path | None = None) -> "MapSourceSpec":
        """Alias kept for callers that expect a default source helper."""

        return cls.osmand_default(package_root)


def resolve_osmand_helper_command(package_root: Path | None = None) -> tuple[str, ...] | None:
    """Return the helper command declared via the environment, if any."""

    raw_value = os.environ.get(ENV_OSMAND_HELPER, "").strip()
    if raw_value:
        parts = tuple(part for part in shlex.split(raw_value, posix=False) if part)
        return parts or None

    repo_root = _repo_root(package_root or _package_root())
    for relative_path in DEFAULT_HELPER_RELATIVE_PATHS:
        candidate = (repo_root / relative_path).resolve()
        if candidate.exists():
            return (str(candidate),)
    return None


def resolve_osmand_native_widget_library(package_root: Path | None = None) -> Path | None:
    """Return the native Qt widget DLL path when it is available."""

    raw_value = os.environ.get(ENV_OSMAND_NATIVE_WIDGET_LIBRARY, "").strip()
    repo_root = _repo_root(package_root or _package_root())
    if raw_value:
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate if candidate.exists() else None

    for relative_path in DEFAULT_NATIVE_WIDGET_RELATIVE_PATHS:
        candidate = (repo_root / relative_path).resolve()
        if candidate.exists():
            return candidate
    return None


def has_usable_osmand_default(package_root: Path | None = None) -> bool:
    """Return ``True`` when the bundled OBF source and helper are both available."""

    root = package_root or _package_root()
    source = MapSourceSpec.osmand_default(root).resolved(root)
    return _has_osmand_data_assets(source) and bool(source.helper_command)


def has_usable_osmand_native_widget(package_root: Path | None = None) -> bool:
    """Return ``True`` when the bundled OBF source and native widget DLL are available."""

    root = package_root or _package_root()
    source = MapSourceSpec.osmand_default(root).resolved(root)
    return _has_osmand_data_assets(source) and resolve_osmand_native_widget_library(root) is not None


def _has_osmand_data_assets(source: MapSourceSpec) -> bool:
    return (
        Path(source.data_path).exists()
        and Path(source.resources_root or "").exists()
        and Path(source.style_path or "").exists()
    )


def _resolve_env_or_default(env_name: str, default_path: Path, repo_root: Path) -> Path:
    raw_value = os.environ.get(env_name, "").strip()
    if not raw_value:
        return default_path.resolve()

    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _resolve_path(value: Path | str, package_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = package_root / path
    return path.resolve()


def _resolve_optional_path(value: Path | str | None, package_root: Path) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value, package_root)


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _repo_root(package_root: Path) -> Path:
    return package_root.resolve().parent.parent


__all__ = [
    "DEFAULT_HELPER_RELATIVE_PATHS",
    "DEFAULT_NATIVE_WIDGET_RELATIVE_PATHS",
    "DEFAULT_OSMAND_OBF_RELATIVE_PATH",
    "DEFAULT_OSMAND_RESOURCES_RELATIVE_PATH",
    "DEFAULT_OSMAND_STYLE_RELATIVE_PATH",
    "ENV_OSMAND_HELPER",
    "ENV_OSMAND_NATIVE_WIDGET_LIBRARY",
    "ENV_OSMAND_OBF_PATH",
    "ENV_OSMAND_RESOURCES_ROOT",
    "ENV_OSMAND_STYLE_PATH",
    "MapBackendMetadata",
    "MapSourceSpec",
    "has_usable_osmand_default",
    "has_usable_osmand_native_widget",
    "resolve_osmand_helper_command",
    "resolve_osmand_native_widget_library",
]
