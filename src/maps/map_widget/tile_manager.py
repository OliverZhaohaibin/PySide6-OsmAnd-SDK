"""Background tile loading and caching infrastructure."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections import deque
from typing import Iterable

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from maps.errors import TileLoadingError
from maps.map_sources import MapBackendMetadata
from maps.tile_backend import TileBackend, TilePayload

LOGGER = logging.getLogger(__name__)


class _TileLoaderWorker(QObject):
    """Perform blocking :meth:`~TileBackend.load_tile` calls in a dedicated thread.

    Instances are moved to a :class:`QThread` so that QProcess-backed
    backends never block the GUI event loop.
    """

    tile_ready = Signal(object, object)   # (tile_key, TilePayload)
    tile_error = Signal(object, str)      # (tile_key, error_message)

    def __init__(self, tile_backend: TileBackend) -> None:
        super().__init__()
        self._backend = tile_backend

    def process_tile(self, tile_key: tuple[int, int, int]) -> None:
        """Load a single tile (runs in the worker thread)."""

        z, x, y = tile_key
        try:
            tile = self._backend.load_tile(z, x, y)
        except TileLoadingError as exc:
            self.tile_error.emit(tile_key, str(exc))
        else:
            if tile is None:
                self.tile_error.emit(tile_key, "")
            else:
                self.tile_ready.emit(tile_key, tile)


class TileManager(QObject):
    """Manage tile loading, caching, and async request scheduling.

    Tile loading is performed in a dedicated :class:`QThread` so that the
    GUI event loop is never blocked by ``QProcess.waitFor*`` calls in
    ``OsmAndRasterBackend``.  Requests are dispatched one at a time; the
    next request is sent only after the previous result arrives, avoiding
    request-queue pile-ups when the user pans away.
    """

    tile_loaded = Signal(tuple)
    tile_missing = Signal(tuple)
    tile_removed = Signal(tuple)
    tiles_changed = Signal()
    _dispatch_tile = Signal(object)  # internal: GUI thread → worker thread
    _MISSING_RETRY_COOLDOWN_S = 1.5

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
        self._missing_tiles: dict[tuple[int, int, int], float] = {}
        self._metadata = self._tile_backend.probe()

        self._request_queue: deque[tuple[int, int, int]] = deque()
        self._processing_queue = False
        self._is_shutdown = False

        # --- worker thread setup -------------------------------------------
        self._worker_thread = QThread()
        self._worker_thread.setObjectName("TileLoaderThread")
        self._worker = _TileLoaderWorker(tile_backend)
        self._worker.moveToThread(self._worker_thread)

        self._dispatch_tile.connect(self._worker.process_tile)
        self._worker.tile_ready.connect(self._on_worker_tile_ready)
        self._worker.tile_error.connect(self._on_worker_tile_error)

        # Shut down the helper process created by probe() so that it is
        # re-created inside the worker thread with correct QProcess affinity.
        tile_backend.shutdown()

        self._worker_thread.start()

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Stop background work and release resources."""

        self._is_shutdown = True
        self._request_queue.clear()
        self._processing_queue = False

        # Ask the worker event loop to exit.
        self._worker_thread.quit()
        if not self._worker_thread.wait(5000):
            self._worker_thread.terminate()
            self._worker_thread.wait(1000)

        self._tile_backend.shutdown()

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

        if self._is_shutdown:
            return

        if tile_key in self._pending_tiles:
            return

        failed_at = self._missing_tiles.get(tile_key)
        if failed_at is not None:
            if (time.monotonic() - failed_at) < self._MISSING_RETRY_COOLDOWN_S:
                return
            # Retry after cooldown; treat this as a fresh request.
            self._missing_tiles.pop(tile_key, None)

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
        """Dispatch one queued tile to the worker thread.

        Only one tile is in-flight at a time; the next tile is dispatched
        when the worker reports a result via :meth:`_on_worker_tile_ready`
        or :meth:`_on_worker_tile_error`.
        """

        if self._is_shutdown:
            self._processing_queue = False
            return

        if not self._request_queue:
            self._processing_queue = False
            return

        tile_key = self._request_queue.popleft()
        # Non-blocking: the signal is queued into the worker thread.
        self._dispatch_tile.emit(tile_key)
        # Do NOT schedule the next tile here; wait for the worker callback.

    # ------------------------------------------------------------------
    # Worker-thread result handlers (run in the GUI thread via queued
    # signal connection).
    # ------------------------------------------------------------------
    def _on_worker_tile_ready(
        self, tile_key: tuple[int, int, int], tile: TilePayload
    ) -> None:
        if self._is_shutdown:
            return
        z, x, y = tile_key
        self._handle_tile_loaded(z, x, y, tile)
        self._continue_queue()

    def _on_worker_tile_error(
        self, tile_key: tuple[int, int, int], error_msg: str
    ) -> None:
        if self._is_shutdown:
            return
        z, x, y = tile_key
        if error_msg:
            LOGGER.warning("Tile %s/%s/%s could not be loaded: %s", z, x, y, error_msg)
        self._handle_tile_missing(z, x, y)
        self._continue_queue()

    def _continue_queue(self) -> None:
        """Schedule processing of the next queued tile after a result."""

        if self._request_queue:
            QTimer.singleShot(0, self._process_queue)
        else:
            self._processing_queue = False

    # ------------------------------------------------------------------
    def is_tile_missing(self, tile_key: tuple[int, int, int]) -> bool:
        """Return ``True`` when ``tile_key`` previously failed to load."""

        failed_at = self._missing_tiles.get(tile_key)
        if failed_at is None:
            return False
        if (time.monotonic() - failed_at) < self._MISSING_RETRY_COOLDOWN_S:
            return True
        self._missing_tiles.pop(tile_key, None)
        return False

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
        self._missing_tiles.pop(key, None)
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
        self._missing_tiles[key] = time.monotonic()
        if key in self._tile_cache:
            del self._tile_cache[key]
            self.tile_removed.emit(key)
        self.tile_missing.emit(key)
        self.tiles_changed.emit()


__all__ = ["TileManager"]
