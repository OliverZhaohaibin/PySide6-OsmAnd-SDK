#include "SqliteHeightmapTileProvider_P.h"
#include "SqliteHeightmapTileProvider.h"

#include <algorithm>
#include <memory>

#include "MapDataProviderHelpers.h"
#include "GeoTiffCollection.h"

OsmAnd::SqliteHeightmapTileProvider_P::SqliteHeightmapTileProvider_P(
    SqliteHeightmapTileProvider* const owner_)
    : owner(owner_)
{
}

OsmAnd::SqliteHeightmapTileProvider_P::~SqliteHeightmapTileProvider_P()
{
}

bool OsmAnd::SqliteHeightmapTileProvider_P::hasDataResources() const
{
    return owner->filesCollection && owner->filesCollection->hasDataResources();
}

OsmAnd::ZoomLevel OsmAnd::SqliteHeightmapTileProvider_P::getMinZoom() const
{
    if (owner->filesCollection)
        return owner->filesCollection->getMinZoom();
    return MaxZoomLevel;
}

OsmAnd::ZoomLevel OsmAnd::SqliteHeightmapTileProvider_P::getMaxZoom() const
{
    if (owner->filesCollection)
        return ZoomLevel31;
    return MaxZoomLevel;
}

int OsmAnd::SqliteHeightmapTileProvider_P::getMaxMissingDataZoomShift(int defaultMaxMissingDataZoomShift) const
{
    // Keep the original overscale behavior when elevation data is available.
    const int maxMissingDataZoomShift = std::max(ZoomLevel22 - getMaxZoom(), defaultMaxMissingDataZoomShift);
    return maxMissingDataZoomShift;
}

bool OsmAnd::SqliteHeightmapTileProvider_P::obtainData(
    const IMapDataProvider::Request& request_,
    std::shared_ptr<IMapDataProvider::Data>& outData,
    std::shared_ptr<Metric>* const pOutMetric)
{
    const auto& request = MapDataProviderHelpers::castRequest<IMapElevationDataProvider::Request>(request_);

    if (pOutMetric)
        pOutMetric->reset();

    if (!owner->filesCollection)
    {
        outData.reset();
        return true;
    }

    float minValue = 0.0f;
    float maxValue = 0.0f;
    const auto pBuffer = new float[owner->outputTileSize * owner->outputTileSize];
    const auto result = owner->filesCollection->getGeoTiffData(
        request.tileId,
        request.zoom,
        owner->outputTileSize,
        3,
        1,
        false,
        minValue,
        maxValue,
        pBuffer);
    if (result == GeoTiffCollection::CallResult::Completed)
    {
        outData = std::make_shared<IMapElevationDataProvider::Data>(
            request.tileId,
            request.zoom,
            sizeof(float) * owner->outputTileSize,
            owner->outputTileSize,
            minValue,
            maxValue,
            pBuffer);
        return true;
    }

    delete[] pBuffer;
    if (result == GeoTiffCollection::CallResult::Failed)
        return false;

    outData.reset();
    return true;
}
