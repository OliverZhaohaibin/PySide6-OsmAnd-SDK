#!/bin/bash

# Build script for osmand_render_helper_native on Linux
# This script builds the native widget library for use with PySide6

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENDOR_ROOT="${REPO_ROOT}/vendor/osmand"
BUILD_ROOT="${SCRIPT_DIR}/build-linux"
DIST_DIR="${SCRIPT_DIR}/dist-linux"

# Default values
BUILD_TYPE="${BUILD_TYPE:-Release}"
JOBS="${JOBS:-$(nproc)}"
CMAKE_GENERATOR="${CMAKE_GENERATOR:-Unix Makefiles}"

# Qt detection - prefer PySide6's Qt if available
detect_qt() {
    # Try to find Qt from PySide6 installation
    if [ -n "${VIRTUAL_ENV}" ]; then
        PYSIDE6_QT="${VIRTUAL_ENV}/lib/python3.12/site-packages/PySide6/Qt"
        if [ -d "${PYSIDE6_QT}" ]; then
            QT_ROOT="${PYSIDE6_QT}"
            echo "Found Qt from PySide6: ${QT_ROOT}"
            return 0
        fi
    fi

    # Try system Qt
    if command -v qmake6 &> /dev/null; then
        QT_ROOT="$(qmake6 -query QT_INSTALL_PREFIX)"
        echo "Found system Qt6: ${QT_ROOT}"
        return 0
    fi

    if command -v qmake &> /dev/null; then
        QT_VERSION=$(qmake --version | grep -oP 'Qt version \K[0-9]+' | head -1)
        if [ "${QT_VERSION}" = "6" ]; then
            QT_ROOT="$(qmake -query QT_INSTALL_PREFIX)"
            echo "Found system Qt6: ${QT_ROOT}"
            return 0
        fi
    fi

    # Common Qt installation paths
    for path in "/usr" "/usr/local/Qt-6" "/opt/Qt6" "${HOME}/Qt/6.*/gcc_64"; do
        if [ -d "${path}/lib/cmake/Qt6" ]; then
            QT_ROOT="${path}"
            echo "Found Qt at: ${QT_ROOT}"
            return 0
        fi
    done

    echo "ERROR: Could not find Qt6 installation. Please set QT_ROOT environment variable."
    exit 1
}

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    if ! command -v cmake &> /dev/null; then
        echo "ERROR: cmake not found. Please install cmake."
        exit 1
    fi

    if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
        echo "ERROR: Neither g++ nor clang++ found. Please install a C++ compiler."
        exit 1
    fi

    if [ ! -d "${VENDOR_ROOT}/core" ]; then
        echo "ERROR: OsmAnd vendor sources not found at ${VENDOR_ROOT}/core"
        exit 1
    fi

    if [ ! -d "${VENDOR_ROOT}/core-legacy" ]; then
        echo "ERROR: OsmAnd legacy vendor sources not found at ${VENDOR_ROOT}/core-legacy"
        exit 1
    fi

    echo "Prerequisites OK"
}

# Build the project
build() {
    echo "Building osmand_render_helper_native for Linux..."
    echo "Build type: ${BUILD_TYPE}"
    echo "Parallel jobs: ${JOBS}"
    echo "Qt root: ${QT_ROOT}"
    echo "Vendor root: ${VENDOR_ROOT}"

    # Create build directory
    mkdir -p "${BUILD_ROOT}"
    mkdir -p "${DIST_DIR}"

    # Configure
    cmake \
        -S "${SCRIPT_DIR}" \
        -B "${BUILD_ROOT}" \
        -G "${CMAKE_GENERATOR}" \
        -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
        -DCMAKE_PREFIX_PATH="${QT_ROOT}" \
        -DQT_ROOT="${QT_ROOT}" \
        -DOSMAND_VENDOR_ROOT="${VENDOR_ROOT}" \
        -DDIST_DIR="${DIST_DIR}" \
        -DCMAKE_TARGET_OS=linux

    # Build
    cmake --build "${BUILD_ROOT}" --config "${BUILD_TYPE}" --parallel "${JOBS}"

    echo ""
    echo "Build complete!"
    echo "Output directory: ${DIST_DIR}"

    if [ -f "${DIST_DIR}/osmand_render_helper" ]; then
        echo "Helper binary: ${DIST_DIR}/osmand_render_helper"
    fi

    if [ -f "${DIST_DIR}/osmand_native_widget.so" ]; then
        echo "Native widget: ${DIST_DIR}/osmand_native_widget.so"
    elif [ -f "${DIST_DIR}/libosmand_native_widget.so" ]; then
        echo "Native widget: ${DIST_DIR}/libosmand_native_widget.so"
    fi
}

# Main
main() {
    detect_qt
    check_prerequisites
    build
}

main "$@"
