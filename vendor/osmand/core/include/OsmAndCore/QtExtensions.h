#ifndef _OSMAND_CORE_QT_EXTENSIONS_H_
#define _OSMAND_CORE_QT_EXTENSIONS_H_

#include <memory>
#include <type_traits>

#if !defined(SWIG)
#   if defined(QGLOBAL_H)
#       error <OsmAndCore/QtExtensions.h> must be included before any Qt header
#   endif // QGLOBAL_H
#endif // !defined(SWIG)

#include <QtGlobal>
#include <QHashFunctions>
#include <QString>
#include <QStringView>

#if QT_VERSION >= QT_VERSION_CHECK(6, 0, 0)
#   if !defined(OSMAND_QSTRINGREF_COMPAT_DEFINED)
#       define OSMAND_QSTRINGREF_COMPAT_DEFINED
class QStringRef
{
public:
    QStringRef() noexcept = default;
    QStringRef(const QString* string) noexcept
        : _string(string)
        , _position(0)
        , _size(string ? string->size() : 0)
    {
    }
    QStringRef(const QString& string) noexcept
        : QStringRef(&string)
    {
    }
    QStringRef(const QString* string, qsizetype position, qsizetype size) noexcept
        : _string(string)
        , _position(0)
        , _size(0)
    {
        if (!_string)
            return;

        const auto stringSize = _string->size();
        _position = qBound<qsizetype>(0, position, stringSize);
        const auto available = stringSize - _position;
        _size = qBound<qsizetype>(0, size, available);
    }
    QStringRef(const QString& string, qsizetype position, qsizetype size) noexcept
        : QStringRef(&string, position, size)
    {
    }

    const QString* string() const noexcept { return _string; }
    qsizetype position() const noexcept { return _position; }
    qsizetype size() const noexcept { return _size; }
    qsizetype length() const noexcept { return _size; }
    const QChar* constData() const noexcept { return _string ? _string->constData() + _position : nullptr; }
    const QChar* data() const noexcept { return constData(); }
    const QChar* unicode() const noexcept { return constData(); }
    bool isEmpty() const noexcept { return _size <= 0; }

    QStringView view() const noexcept
    {
        return _string ? QStringView(*_string).mid(_position, _size) : QStringView();
    }
    operator QStringView() const noexcept { return view(); }
    QString toString() const { return view().toString(); }

    QStringRef mid(qsizetype position) const noexcept
    {
        const auto safePosition = qBound<qsizetype>(0, position, _size);
        return mid(safePosition, _size - safePosition);
    }
    QStringRef mid(qsizetype position, qsizetype size) const noexcept
    {
        const auto safePosition = qBound<qsizetype>(0, position, _size);
        const auto available = _size - safePosition;
        const auto safeSize = qBound<qsizetype>(0, size, available);
        return QStringRef(_string, _position + safePosition, safeSize);
    }

private:
    const QString* _string = nullptr;
    qsizetype _position = 0;
    qsizetype _size = 0;
};
Q_DECLARE_TYPEINFO(QStringRef, Q_RELOCATABLE_TYPE);

inline bool operator==(const QStringRef& lhs, const QStringRef& rhs) noexcept { return lhs.view() == rhs.view(); }
inline bool operator!=(const QStringRef& lhs, const QStringRef& rhs) noexcept { return !(lhs == rhs); }
inline bool operator==(const QStringRef& lhs, const QString& rhs) noexcept { return lhs.view() == QStringView(rhs); }
inline bool operator!=(const QStringRef& lhs, const QString& rhs) noexcept { return !(lhs == rhs); }
inline bool operator==(const QString& lhs, const QStringRef& rhs) noexcept { return QStringView(lhs) == rhs.view(); }
inline bool operator!=(const QString& lhs, const QStringRef& rhs) noexcept { return !(lhs == rhs); }
inline bool operator==(const QStringRef& lhs, QLatin1String rhs) noexcept { return lhs.view() == rhs; }
inline bool operator!=(const QStringRef& lhs, QLatin1String rhs) noexcept { return !(lhs == rhs); }
inline bool operator==(QLatin1String lhs, const QStringRef& rhs) noexcept { return lhs == rhs.view(); }
inline bool operator!=(QLatin1String lhs, const QStringRef& rhs) noexcept { return !(lhs == rhs); }
inline size_t qHash(const QStringRef& value, size_t seed = 0) noexcept { const auto view = value.view(); return qHashBits(view.data(), static_cast<size_t>(view.size()) * sizeof(QChar), seed); }
#   endif
#endif

#include <OsmAndCore/CommonTypes.h>
#include <OsmAndCore/SmartPOD.h>
#include <OsmAndCore/Data/DataCommonTypes.h>
#include <OsmAndCore/Map/MapCommonTypes.h>

#if !defined(SWIG)
template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.qHash()), uint(uint)>::value, uint>::type;

template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.operator uint64_t()), uint64_t()>::value, uint>::type;

template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.operator int64_t()), int64_t()>::value, uint>::type;

template<typename T>
inline uint qHash(const std::shared_ptr<T>& value) Q_DECL_NOTHROW;

template<typename T>
inline auto qHash(
    const T value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_enum<T>::value && !std::is_convertible<T, int>::value, uint>::type;

template<typename T, T DEFAULT_VALUE>
inline uint qHash(const OsmAnd::SmartPOD<T, DEFAULT_VALUE>& value) Q_DECL_NOTHROW;
#endif // !defined(SWIG)

#include <QHash>

#if !defined(SWIG)
template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.qHash()), uint()>::value, uint>::type
{
    return value.qHash();
}

template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.operator uint64_t()), uint64_t()>::value, uint>::type
{
    return ::qHash(static_cast<uint64_t>(value));
}

template<typename T>
inline auto qHash(
    const T& value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_same<decltype(value.operator int64_t()), int64_t()>::value, uint>::type
{
    return ::qHash(static_cast<int64_t>(value));
}

template<typename T>
inline uint qHash(const std::shared_ptr<T>& value) Q_DECL_NOTHROW
{
    return ::qHash(value.get());
}

template<typename T>
inline auto qHash(
    const T value) Q_DECL_NOTHROW -> typename std::enable_if< std::is_enum<T>::value && !std::is_convertible<T, int>::value, uint>::type
{
    return ::qHash(static_cast<typename std::underlying_type<T>::type>(value));
}

template<typename T, T DEFAULT_VALUE>
inline uint qHash(const OsmAnd::SmartPOD<T, DEFAULT_VALUE>& value) Q_DECL_NOTHROW
{
    return ::qHash(static_cast<T>(value));
}
#endif // !defined(SWIG)

#endif // !defined(_OSMAND_CORE_QT_EXTENSIONS_H_)





