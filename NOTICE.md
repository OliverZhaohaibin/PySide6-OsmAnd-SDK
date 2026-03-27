# Notice

This repository is an extracted standalone workspace built around copied OsmAnd source trees and a PySide6 integration layer.

Project name: `PySide6-OsmAnd-SDK`
Author: [OliverZhaohaibin](https://github.com/OliverZhaohaibin)

Source origins preserved in this workspace:

- `vendor/osmand/core`: copied from the local `OsmAnd-core` checkout
- `vendor/osmand/core-legacy`: copied from the local `OsmAnd-core-legacy` checkout
- `vendor/osmand/resources`: copied from the local `OsmAnd-resources` checkout
- `vendor/osmand/build`: copied from the local OsmAnd build tree used by the official Windows build scripts

Licensing summary:

- the vendored OsmAnd trees document GPLv3-based licensing in their upstream `LICENSE` files
- the top-level project therefore documents itself as `GPL-3.0-or-later`
- `LICENSE` contains the project-level summary for this extracted repository
- `COPYING` contains the verbatim GNU GPL v3 license text
- the original iPhoto repository contains additional MIT-licensed code, but this extracted repository intentionally carries only the OsmAnd-focused subset needed for the standalone preview and helper workspace
