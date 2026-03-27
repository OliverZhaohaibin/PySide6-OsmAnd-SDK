#include "GeoTileRasterizer_P.h"
#include "GeoTileRasterizer.h"

OsmAnd::GeoTileRasterizer_P::GeoTileRasterizer_P(
    GeoTileRasterizer* const owner_)
    : owner(owner_)
{
}

OsmAnd::GeoTileRasterizer_P::~GeoTileRasterizer_P()
{
}

QHash<OsmAnd::BandIndex, sk_sp<const SkImage>> OsmAnd::GeoTileRasterizer_P::rasterize(
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    Q_UNUSED(queryController);
    if (pOutMetric)
        pOutMetric->reset();
    return QHash<BandIndex, sk_sp<const SkImage>>();
}

QHash<OsmAnd::BandIndex, sk_sp<const SkImage>> OsmAnd::GeoTileRasterizer_P::rasterize(
    QHash<BandIndex, QByteArray>& outEncImgData,
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    outEncImgData.clear();
    return rasterize(pOutMetric, queryController);
}

QHash<OsmAnd::BandIndex, sk_sp<const SkImage>> OsmAnd::GeoTileRasterizer_P::rasterizeContours(
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    Q_UNUSED(queryController);
    if (pOutMetric)
        pOutMetric->reset();
    return QHash<BandIndex, sk_sp<const SkImage>>();
}

QHash<OsmAnd::BandIndex, sk_sp<const SkImage>> OsmAnd::GeoTileRasterizer_P::rasterizeContours(
    QHash<BandIndex, QByteArray>& outEncImgData,
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    outEncImgData.clear();
    return rasterizeContours(pOutMetric, queryController);
}

bool OsmAnd::GeoTileRasterizer_P::evaluateContours(
    QHash<BandIndex, QList<std::shared_ptr<GeoContour>>>& bandContours,
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    Q_UNUSED(queryController);
    if (pOutMetric)
        pOutMetric->reset();
    bandContours.clear();
    return false;
}

sk_sp<SkImage> OsmAnd::GeoTileRasterizer_P::rasterizeBandContours(
    const QList<std::shared_ptr<GeoContour>>& contours,
    const TileId tileId,
    const ZoomLevel zoom,
    const int width,
    const int height)
{
    Q_UNUSED(contours);
    Q_UNUSED(tileId);
    Q_UNUSED(zoom);
    Q_UNUSED(width);
    Q_UNUSED(height);
    return nullptr;
}
