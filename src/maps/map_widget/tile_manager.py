"""Background tile loading and caching infrastructure."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections import deque
from typing import Iterable

from PySide6.QtCore import QObject, QTimer, Signal

from maps.errors import TileLoadingError
from maps.map_sources import MapBackendMetadata
from maps.tile_backend import TileBackend, TilePayload

LOGGER = logging.getLogger(__name__)


class TileManager(QObject):
    """Manage tile loading, caching, and async request scheduling.

    This implementation uses QTimer to schedule tile loading in the main thread,
    avoiding thread affinity issues with QProcess-based backends like OsmAndRasterBackend.
    """

    tile_loaded = Signal(tuple)
    tile_missing = Signal(tuple)
    tile_removed = Signal(tuple)
    tiles_changed = Signal()

    def __init__(
        self,
        tile_backend: TileBackend,
        *,
        cache_limit: int = 256,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._tile_backend = tile_backend
        self._cache_limit = cache_limit

        self._tile_cache: OrderedDict[tuple[int, int, int], TilePayload] = OrderedDict()
        self._pending_tiles: set[tuple[int, int, int]] = set()
        self._missing_tiles: set[tuple[int, int, int]] = set()
        self._metadata = self._tile_backend.probe()

        # Request queue for async tile loading in the main thread
        self._request_queue: deque[tuple[int, int, int]] = deque()
        self._processing_queue = False

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Stop background work and release resources."""

        self._tile_backend.shutdown()
        self._request_queue.clear()
        self._processing_queue = False

    # ------------------------------------------------------------------
    def get_tile(self, tile_key: tuple[int, int, int]) -> TilePayload | None:
        """Return a cached tile, updating the LRU ordering when found."""

        tile = self._tile_cache.get(tile_key)
        if tile is not None:
            self._tile_cache.move_to_end(tile_key)
        return tile

    # ------------------------------------------------------------------
    def ensure_tile(self, tile_key: tuple[int, int, int]) -> None:
        """Schedule ``tile_key`` for loading when it is not cached."""

        if tile_key in self._missing_tiles or tile_key in self._pending_tiles:
            return

        self._pending_tiles.add(tile_key)
        self._request_queue.append(tile_key)
        self._schedule_queue_processing()

    # ------------------------------------------------------------------
    def _schedule_queue_processing(self) -> None:
        """Schedule async processing of the tile request queue."""

        if self._processing_queue:
            return

        self._processing_queue = True
        QTimer.singleShot(0, self._process_queue)

    # ------------------------------------------------------------------
    def _process_queue(self) -> None:
        """Process one tile from the request queue."""

        if not self._request_queue:
            self._processing_queue = False
            return

        tile_key = self._request_queue.popleft()
        z, x, y = tile_key

        try:
            tile = self._tile_backend.load_tile(z, x, y)
        except TileLoadingError as exc:
            LOGGER.warning(
                "Tile %s/%s/%s could not be loaded: %s",
                z,
                x,
                y,
                exc,
            )
            self._handle_tile_missing(z, x, y)
        else:
            if tile is None:
                self._handle_tile_missing(z, x, y)
            else:
                self._handle_tile_loaded(z, x, y, tile)

        # Schedule processing of next tile if queue is not empty
        if self._request_queue:
            QTimer.singleShot(0, self._process_queue)
        else:
            self._processing_queue = False

    # ------------------------------------------------------------------
    def is_tile_missing(self, tile_key: tuple[int, int, int]) -> bool:
        """Return ``True`` when ``tile_key`` previously failed to load."""

        return tile_key in self._missing_tiles

    # ------------------------------------------------------------------
    def pending_tiles(self) -> Iterable[tuple[int, int, int]]:
        """Expose the set of in-flight requests for diagnostics/testing."""

        return set(self._pending_tiles)

    # ------------------------------------------------------------------
    @property
    def metadata(self) -> MapBackendMetadata:
        """Expose the active backend metadata to the renderer/controller."""

        return self._metadata

    # ------------------------------------------------------------------
    def set_device_scale(self, scale: float) -> None:
        """Update the raster output scale and flush cached tiles."""

        self._tile_backend.set_device_scale(scale)
        self.clear()

    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Drop all cached tile state so the next frame refetches data."""

        self._tile_backend.clear_cache()
        self._tile_cache.clear()
        self._pending_tiles.clear()
        self._missing_tiles.clear()
        self._request_queue.clear()
        self._processing_queue = False
        self.tiles_changed.emit()

    # ------------------------------------------------------------------
    def _handle_tile_loaded(self, z: int, x: int, y: int, tile: TilePayload) -> None:
        """Store the freshly loaded tile and emit update signals."""

        key = (z, x, y)
        self._pending_tiles.discard(key)
        self._missing_tiles.discard(key)
        self._tile_cache[key] = tile
        self._tile_cache.move_to_end(key)
        self.tile_loaded.emit(key)

        while len(self._tile_cache) > self._cache_limit:
            evicted_key, _ = self._tile_cache.popitem(last=False)
            self.tile_removed.emit(evicted_key)

        self.tiles_changed.emit()

    # ------------------------------------------------------------------
    def _handle_tile_missing(self, z: int, x: int, y: int) -> None:
        """Remember that a tile is unavailable and notify listeners."""

        key = (z, x, y)
        self._pending_tiles.discard(key)
        self._missing_tiles.add(key)
        if key in self._tile_cache:
            del self._tile_cache[key]
            self.tile_removed.emit(key)
        self.tile_missing.emit(key)
        self.tiles_changed.emit()


__all__ = ["TileManager"]
