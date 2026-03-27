#ifndef _OSMAND_CORE_GEO_TILE_RASTERIZER_P_H_
#define _OSMAND_CORE_GEO_TILE_RASTERIZER_P_H_

#include "stdlib_common.h"

#include "QtExtensions.h"
#include <QHash>
#include <QMutex>

#include "OsmAndCore.h"
#include "CommonTypes.h"
#include "PrivateImplementation.h"
#include "GeoTileRasterizer.h"

namespace OsmAnd
{
    class GeoTileRasterizer_P Q_DECL_FINAL
    {
        Q_DISABLE_COPY_AND_MOVE(GeoTileRasterizer_P);
    private:
        mutable QMutex _dataMutex;
    protected:
        GeoTileRasterizer_P(GeoTileRasterizer* const owner);
    public:
        ~GeoTileRasterizer_P();

        ImplementationInterface<GeoTileRasterizer> owner;

        QHash<BandIndex, sk_sp<const SkImage>> rasterize(
            std::shared_ptr<Metric>* const pOutMetric = nullptr,
            const std::shared_ptr<const IQueryController>& queryController = nullptr);

        QHash<BandIndex, sk_sp<const SkImage>> rasterize(
            QHash<BandIndex, QByteArray>& outEncImgData,
            std::shared_ptr<Metric>* const pOutMetric = nullptr,
            const std::shared_ptr<const IQueryController>& queryController = nullptr);

        QHash<BandIndex, sk_sp<const SkImage>> rasterizeContours(
            std::shared_ptr<Metric>* const pOutMetric = nullptr,
            const std::shared_ptr<const IQueryController>& queryController = nullptr);

        QHash<BandIndex, sk_sp<const SkImage>> rasterizeContours(
            QHash<BandIndex, QByteArray>& outEncImgData,
            std::shared_ptr<Metric>* const pOutMetric = nullptr,
            const std::shared_ptr<const IQueryController>& queryController = nullptr);

        bool evaluateContours(
            QHash<BandIndex, QList<std::shared_ptr<GeoContour>>>& bandContours,
            std::shared_ptr<Metric>* const pOutMetric = nullptr,
            const std::shared_ptr<const IQueryController>& queryController = nullptr);

        static sk_sp<SkImage> rasterizeBandContours(
            const QList<std::shared_ptr<GeoContour>>& contours,
            const TileId tileId,
            const ZoomLevel zoom,
            const int width,
            const int height);

    friend class OsmAnd::GeoTileRasterizer;
    };
}

#endif // !defined(_OSMAND_CORE_GEO_TILE_RASTERIZER_P_H_)
