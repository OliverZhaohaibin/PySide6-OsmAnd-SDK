#include "HeightRasterMapLayerProvider_P.h"
#include "HeightRasterMapLayerProvider.h"

OsmAnd::HeightRasterMapLayerProvider_P::HeightRasterMapLayerProvider_P(
    HeightRasterMapLayerProvider* owner_,
    const QString& heightColorsFilename_,
    const ZoomLevel minZoom_,
    const ZoomLevel maxZoom_,
    const uint32_t tileSize_,
    const float densityFactor_)
    : owner(owner_)
    , minZoom(minZoom_)
    , maxZoom(maxZoom_)
    , tileSize(tileSize_)
    , densityFactor(densityFactor_)
{
    procParameters.rasterType = IGeoTiffCollection::RasterType::Height;
    procParameters.colorsFilename = heightColorsFilename_;
}

OsmAnd::HeightRasterMapLayerProvider_P::~HeightRasterMapLayerProvider_P()
{
}

OsmAnd::ZoomLevel OsmAnd::HeightRasterMapLayerProvider_P::getMinZoom() const
{
    return minZoom;
}

OsmAnd::ZoomLevel OsmAnd::HeightRasterMapLayerProvider_P::getMaxZoom() const
{
    return maxZoom;
}

bool OsmAnd::HeightRasterMapLayerProvider_P::obtainData(
    const IMapDataProvider::Request& request,
    std::shared_ptr<IMapDataProvider::Data>& outData,
    std::shared_ptr<Metric>* const pOutMetric)
{
    Q_UNUSED(request);
    if (pOutMetric)
        pOutMetric->reset();
    outData.reset();
    return false;
}
