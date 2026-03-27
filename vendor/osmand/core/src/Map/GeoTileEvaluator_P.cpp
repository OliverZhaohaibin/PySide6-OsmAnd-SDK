#include "GeoTileEvaluator_P.h"
#include "GeoTileEvaluator.h"

OsmAnd::GeoTileEvaluator_P::GeoTileEvaluator_P(
    GeoTileEvaluator* const owner_)
    : owner(owner_)
{
}

OsmAnd::GeoTileEvaluator_P::~GeoTileEvaluator_P()
{
}

bool OsmAnd::GeoTileEvaluator_P::evaluate(
    const LatLon& latLon,
    QList<double>& outData,
    std::shared_ptr<Metric>* const pOutMetric /*= nullptr*/,
    const std::shared_ptr<const IQueryController>& queryController /*= nullptr*/)
{
    Q_UNUSED(latLon);
    Q_UNUSED(queryController);
    if (pOutMetric)
        pOutMetric->reset();
    outData.clear();
    return false;
}
