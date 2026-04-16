"""Tile collection and request scheduling for the map renderer."""

from __future__ import annotations

import math

from maps.tile_backend import TilePayload

from .tile_manager import TileManager
from .viewport import ViewState


def collect_tiles(
    view_state: ViewState,
    tile_manager: TileManager,
) -> tuple[
    list[tuple[tuple[int, int, int], TilePayload, float, float, int, int]],
    list[tuple[tuple[int, int], tuple[int, int, int]]],
]:
    """Gather tiles that intersect the viewport and schedule missing ones."""

    start_tile_x = math.floor(view_state.view_top_left_x / view_state.scaled_tile_size)
    start_tile_y = math.floor(view_state.view_top_left_y / view_state.scaled_tile_size)
    end_tile_x = math.ceil(
        (view_state.view_top_left_x + view_state.width) / view_state.scaled_tile_size
    )
    end_tile_y = math.ceil(
        (view_state.view_top_left_y + view_state.height) / view_state.scaled_tile_size
    )

    # Guard against fractional-zoom rounding seams by drawing/requesting one
    # tile outside each edge of the viewport.
    start_tile_x -= 1
    start_tile_y -= 1
    end_tile_x += 1
    end_tile_y += 1

    tiles_to_draw: list[tuple[tuple[int, int, int], TilePayload, float, float, int, int]] = []
    tiles_to_request: list[tuple[tuple[int, int], tuple[int, int, int]]] = []

    # Iterate tiles in screen order (top-to-bottom, left-to-right) to ensure
    # consistent rendering and request order. This is especially important
    # on Linux where the top-left corner may otherwise show ghosting.
    for tile_y in range(start_tile_y, end_tile_y):
        if tile_y < 0 or tile_y >= view_state.tiles_across:
            continue
        for tile_x in range(start_tile_x, end_tile_x):
            wrapped_x = tile_x % view_state.tiles_across
            tile_scheme = tile_manager.metadata.tile_scheme
            resolved_y = (view_state.tiles_across - 1) - tile_y if tile_scheme == "tms" else tile_y
            tile_key = (view_state.fetch_zoom, wrapped_x, resolved_y)

            tile_origin_x = tile_x * view_state.scaled_tile_size - view_state.view_top_left_x
            tile_origin_y = tile_y * view_state.scaled_tile_size - view_state.view_top_left_y

            tile_data = tile_manager.get_tile(tile_key)
            if tile_data is None:
                if not tile_manager.is_tile_missing(tile_key):
                    # Request missing tiles in strict viewport scan order.
                    request_priority = (tile_y - start_tile_y, tile_x - start_tile_x)
                    tiles_to_request.append((request_priority, tile_key))
                continue

            tiles_to_draw.append(
                (tile_key, tile_data, tile_origin_x, tile_origin_y, wrapped_x, tile_y)
            )

    return tiles_to_draw, tiles_to_request


def request_tiles(
    tiles_to_request: list[tuple[tuple[int, int], tuple[int, int, int]]],
    tile_manager: TileManager,
) -> None:
    """Request tiles in sorted viewport scan-order `(row, col)` priority."""

    if not tiles_to_request:
        return

    tiles_to_request.sort(key=lambda item: item[0])
    for _, tile_key in tiles_to_request:
        tile_manager.ensure_tile(tile_key)
