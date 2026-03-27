#include "HillshadeRasterMapLayerProvider_P.h"
#include "HillshadeRasterMapLayerProvider.h"

OsmAnd::HillshadeRasterMapLayerProvider_P::HillshadeRasterMapLayerProvider_P(
    HillshadeRasterMapLayerProvider* owner_,
    const QString& hillshadeColorsFilename_,
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
    procParameters.rasterType = IGeoTiffCollection::RasterType::Hillshade;
    procParameters.colorsFilename = hillshadeColorsFilename_;
    procParameters.intermediateColorsFilename = slopeColorsFilename_;
}

OsmAnd::HillshadeRasterMapLayerProvider_P::~HillshadeRasterMapLayerProvider_P()
{
}

OsmAnd::ZoomLevel OsmAnd::HillshadeRasterMapLayerProvider_P::getMinZoom() const
{
    return minZoom;
}

OsmAnd::ZoomLevel OsmAnd::HillshadeRasterMapLayerProvider_P::getMaxZoom() const
{
    return maxZoom;
}

bool OsmAnd::HillshadeRasterMapLayerProvider_P::obtainData(
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
