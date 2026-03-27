#include "GeoTiffCollection_P.h"

#include <QMutexLocker>

#include "GeoTiffCollection.h"

OsmAnd::GeoTiffCollection_P::GeoTiffCollection_P(
    GeoTiffCollection* owner_,
    bool useFileWatcher /*= true*/)
    : owner(owner_)
{
    Q_UNUSED(useFileWatcher);
}

OsmAnd::GeoTiffCollection_P::~GeoTiffCollection_P()
{
}

QList<OsmAnd::GeoTiffCollection::SourceOriginId> OsmAnd::GeoTiffCollection_P::getSourceOriginIds() const
{
    QMutexLocker locker(&_mutex);
    return _sourceOriginIds;
}

OsmAnd::GeoTiffCollection::SourceOriginId OsmAnd::GeoTiffCollection_P::addDirectory(
    const QDir& dir,
    bool recursive)
{
    Q_UNUSED(dir);
    Q_UNUSED(recursive);

    QMutexLocker locker(&_mutex);
    const auto entryId = ++_lastSourceOriginId;
    _sourceOriginIds.append(entryId);
    return entryId;
}

OsmAnd::GeoTiffCollection::SourceOriginId OsmAnd::GeoTiffCollection_P::addFile(
    const QFileInfo& fileInfo)
{
    QMutexLocker locker(&_mutex);
    const auto entryId = ++_lastSourceOriginId;
    _sourceOriginIds.append(entryId);
    _fileIds.insert(fileInfo.absoluteFilePath(), entryId);
    return entryId;
}

bool OsmAnd::GeoTiffCollection_P::removeFile(const QFileInfo& fileInfo)
{
    QMutexLocker locker(&_mutex);
    const auto key = fileInfo.absoluteFilePath();
    const auto it = _fileIds.constFind(key);
    if (it == _fileIds.cend())
        return false;

    const auto entryId = it.value();
    _fileIds.remove(key);
    _sourceOriginIds.removeOne(entryId);
    return true;
}

bool OsmAnd::GeoTiffCollection_P::remove(const GeoTiffCollection::SourceOriginId entryId)
{
    QMutexLocker locker(&_mutex);
    auto removed = _sourceOriginIds.removeOne(entryId);
    for (auto it = _fileIds.begin(); it != _fileIds.end();)
    {
        if (it.value() == entryId)
            it = _fileIds.erase(it);
        else
            ++it;
    }
    return removed;
}

void OsmAnd::GeoTiffCollection_P::setLocalCache(const QDir& localCacheDir)
{
    QMutexLocker locker(&_mutex);
    _localCacheDir = localCacheDir;
}

bool OsmAnd::GeoTiffCollection_P::refreshTilesInCache(const GeoTiffCollection::RasterType cache)
{
    Q_UNUSED(cache);
    return false;
}

bool OsmAnd::GeoTiffCollection_P::removeFileTilesFromCache(
    const GeoTiffCollection::RasterType cache,
    const QString& filePath)
{
    Q_UNUSED(cache);
    Q_UNUSED(filePath);
    return false;
}

bool OsmAnd::GeoTiffCollection_P::removeOlderTilesFromCache(
    const GeoTiffCollection::RasterType cache,
    int64_t time)
{
    Q_UNUSED(cache);
    Q_UNUSED(time);
    return false;
}

bool OsmAnd::GeoTiffCollection_P::hasDataResources() const
{
    QMutexLocker locker(&_mutex);
    return !_sourceOriginIds.isEmpty();
}

void OsmAnd::GeoTiffCollection_P::setMinZoom(const ZoomLevel zoomLevel) const
{
    QMutexLocker locker(&_mutex);
    _minZoom = zoomLevel;
}

OsmAnd::ZoomLevel OsmAnd::GeoTiffCollection_P::getMinZoom() const
{
    QMutexLocker locker(&_mutex);
    return _minZoom;
}

OsmAnd::ZoomLevel OsmAnd::GeoTiffCollection_P::getMaxZoom(const uint32_t tileSize) const
{
    Q_UNUSED(tileSize);
    return hasDataResources() ? ZoomLevel19 : ZoomLevel0;
}

OsmAnd::GeoTiffCollection::CallResult OsmAnd::GeoTiffCollection_P::getGeoTiffData(
    const TileId& tileId,
    const ZoomLevel zoom,
    const uint32_t tileSize,
    const uint32_t overlap,
    const uint32_t bandCount,
    const bool toBytes,
    float& minValue,
    float& maxValue,
    void* pBuffer,
    const GeoTiffCollection::ProcessingParameters* procParameters) const
{
    Q_UNUSED(tileId);
    Q_UNUSED(zoom);
    Q_UNUSED(tileSize);
    Q_UNUSED(overlap);
    Q_UNUSED(bandCount);
    Q_UNUSED(toBytes);
    Q_UNUSED(pBuffer);
    Q_UNUSED(procParameters);

    minValue = 0.0f;
    maxValue = 0.0f;
    return GeoTiffCollection::CallResult::Empty;
}

bool OsmAnd::GeoTiffCollection_P::calculateHeights(
    const ZoomLevel zoom,
    const uint32_t tileSize,
    const QList<PointI>& points31,
    QList<float>& outHeights) const
{
    Q_UNUSED(zoom);
    Q_UNUSED(tileSize);
    outHeights.clear();
    outHeights.reserve(points31.size());
    for (const auto& point31 : points31)
    {
        Q_UNUSED(point31);
        outHeights.push_back(0.0f);
    }
    return false;
}
