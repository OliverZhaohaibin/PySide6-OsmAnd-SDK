#ifndef _OSMAND_CORE_GEOTIFF_COLLECTION_P_H_
#define _OSMAND_CORE_GEOTIFF_COLLECTION_P_H_

#include "stdlib_common.h"

#include "QtExtensions.h"
#include <QDir>
#include <QFileInfo>
#include <QHash>
#include <QList>
#include <QMutex>

#include "OsmAndCore.h"
#include "CommonTypes.h"
#include "PrivateImplementation.h"
#include "GeoTiffCollection.h"
#include <OsmAndCore/PointsAndAreas.h>

namespace OsmAnd
{
    class GeoTiffCollection;
    class GeoTiffCollection_P Q_DECL_FINAL
    {
        Q_DISABLE_COPY_AND_MOVE(GeoTiffCollection_P);
    private:
        mutable QMutex _mutex;
        QList<GeoTiffCollection::SourceOriginId> _sourceOriginIds;
        QHash<QString, GeoTiffCollection::SourceOriginId> _fileIds;
        int _lastSourceOriginId = 0;
        mutable ZoomLevel _minZoom = ZoomLevel0;
        QDir _localCacheDir;
    protected:
        GeoTiffCollection_P(GeoTiffCollection* owner, bool useFileWatcher = true);
    public:
        ~GeoTiffCollection_P();

        ImplementationInterface<GeoTiffCollection> owner;

        QList<GeoTiffCollection::SourceOriginId> getSourceOriginIds() const;
        GeoTiffCollection::SourceOriginId addDirectory(const QDir& dir, bool recursive);
        GeoTiffCollection::SourceOriginId addFile(const QFileInfo& fileInfo);
        bool removeFile(const QFileInfo& fileInfo);
        bool remove(const GeoTiffCollection::SourceOriginId entryId);
        void setLocalCache(const QDir& localCacheDir);
        bool refreshTilesInCache(const GeoTiffCollection::RasterType cache);
        bool removeFileTilesFromCache(const GeoTiffCollection::RasterType cache, const QString& filePath);
        bool removeOlderTilesFromCache(const GeoTiffCollection::RasterType cache, int64_t time);

        bool hasDataResources() const;
        void setMinZoom(const ZoomLevel zoomLevel) const;
        ZoomLevel getMinZoom() const;
        ZoomLevel getMaxZoom(const uint32_t tileSize) const;

        GeoTiffCollection::CallResult getGeoTiffData(
            const TileId& tileId,
            const ZoomLevel zoom,
            const uint32_t tileSize,
            const uint32_t overlap,
            const uint32_t bandCount,
            const bool toBytes,
            float& minValue,
            float& maxValue,
            void* pBuffer,
            const GeoTiffCollection::ProcessingParameters* procParameters) const;

        bool calculateHeights(
            const ZoomLevel zoom,
            const uint32_t tileSize,
            const QList<PointI>& points31,
            QList<float>& outHeights) const;

    friend class OsmAnd::GeoTiffCollection;
    };
}

#endif // !defined(_OSMAND_CORE_GEOTIFF_COLLECTION_P_H_)
