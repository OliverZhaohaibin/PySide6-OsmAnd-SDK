"""Raster-only rendering logic for the standalone OsmAnd preview."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter

from maps.tile_backend import RasterTile, TilePayload

from .tile_collector import collect_tiles, request_tiles
from .tile_manager import TileManager
from .viewport import compute_view_state


@dataclass(frozen=True)
class CityAnnotation:
    """Compatibility container retained for callers that annotate city labels."""

    longitude: float
    latitude: float
    display_name: str
    full_name: str


class MapRenderer:
    """Render helper-produced raster tiles into a QWidget/QOpenGLWidget."""

    def __init__(
        self,
        *,
        tile_manager: TileManager,
        tile_size: int,
    ) -> None:
        self._tile_manager = tile_manager
        self._tile_size = tile_size
        self._cities: list[CityAnnotation] = []

    def set_cities(self, cities: Iterable[CityAnnotation]) -> None:
        """Retain compatibility with the original preview API."""

        self._cities = list(cities)

    def render(
        self,
        painter: QPainter,
        *,
        center_x: float,
        center_y: float,
        zoom: float,
        width: int,
        height: int,
    ) -> None:
        """Draw the current raster map scene into ``painter``."""

        painter.fillRect(0, 0, width, height, QColor("#93b4c9"))

        fetch_max_zoom = self._tile_manager.metadata.fetch_max_zoom
        if fetch_max_zoom is None:
            fetch_max_zoom = max(0, int(self._tile_manager.metadata.max_zoom))

        view_state = compute_view_state(
            center_x,
            center_y,
            zoom,
            width,
            height,
            self._tile_size,
            max_tile_zoom_level=fetch_max_zoom,
        )
        tiles_to_draw, tiles_to_request = collect_tiles(view_state, self._tile_manager)
        request_tiles(tiles_to_request, self._tile_manager)

        for _, tile_data, tile_origin_x, tile_origin_y, _, _ in tiles_to_draw:
            if isinstance(tile_data, RasterTile):
                self._draw_raster_tile(
                    painter,
                    tile_data,
                    tile_origin_x,
                    tile_origin_y,
                    view_state.scaled_tile_size,
                )

    def invalidate_tile(self, tile_key: tuple[int, int, int]) -> None:
        """Retained for compatibility; raster tiles do not cache geometry."""

        del tile_key

    def city_at(self, position: QPointF) -> str | None:
        """Raster-only mode does not currently expose label hit testing."""

        del position
        return None

    @staticmethod
    def _draw_raster_tile(
        painter: QPainter,
        tile: RasterTile,
        origin_x: float,
        origin_y: float,
        scaled_tile_size: float,
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(
            QRectF(origin_x, origin_y, scaled_tile_size, scaled_tile_size),
            tile.image,
        )
        painter.restore()


__all__ = ["CityAnnotation", "MapRenderer"]
