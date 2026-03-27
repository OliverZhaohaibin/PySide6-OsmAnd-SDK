"""Shared exception types for the standalone OsmAnd preview."""

from __future__ import annotations


class TileLoadingError(Exception):
    """Base exception for recoverable tile-loading problems."""


class TileAccessError(TileLoadingError):
    """Raised when a required map asset is missing or unreadable."""


__all__ = ["TileAccessError", "TileLoadingError"]
