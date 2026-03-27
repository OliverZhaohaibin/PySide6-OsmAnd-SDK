#include "SlopeRasterMapLayerProvider_P.h"
#include "SlopeRasterMapLayerProvider.h"

OsmAnd::SlopeRasterMapLayerProvider_P::SlopeRasterMapLayerProvider_P(
    SlopeRasterMapLayerProvider* owner_,
    const QString& slopeColorsFilename_,
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
    procParameters.rasterType = IGeoTiffCollection::RasterType::Slope;
    procParameters.colorsFilename = slopeColorsFilename_;
}

OsmAnd::SlopeRasterMapLayerProvider_P::~SlopeRasterMapLayerProvider_P()
{
}

OsmAnd::ZoomLevel OsmAnd::SlopeRasterMapLayerProvider_P::getMinZoom() const
{
    return minZoom;
}

OsmAnd::ZoomLevel OsmAnd::SlopeRasterMapLayerProvider_P::getMaxZoom() const
{
    return maxZoom;
}

bool OsmAnd::SlopeRasterMapLayerProvider_P::obtainData(
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
