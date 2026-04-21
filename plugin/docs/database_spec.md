# GeoNames SQLite Database Spec

## Summary

This database is now built from `cities500.zip` only.
The goal is query speed, not full GeoNames coverage:

- keep only cities with population >= 500 from the upstream dataset
- reuse the inline alternate-name column in `cities500.txt`
- replace the previous FTS + join path with a denormalized `search_index` table
- add a `prefix_cache` table for hot short-prefix queries
- make exact and prefix lookup run as single-table reads

Compared with the old `allCountries.zip + alternateNamesV2.zip` build, this version trades coverage for much smaller database size and much lower lookup latency.

## Input

- `cities500.zip` -> `cities500.txt`

The builder only extracts the fields needed for lookup and output.

## Schema

### `geonames`

```sql
CREATE TABLE geonames (
    geoname_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    asciiname TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    feature_code TEXT,
    country_code TEXT,
    admin1_code TEXT,
    admin2_code TEXT,
    admin3_code TEXT,
    admin4_code TEXT,
    population INTEGER NOT NULL
);
```

Field mapping from `cities500.txt`:

- `geoname_id`: column 1
- `name`: column 2
- `asciiname`: column 3
- `latitude`: column 5
- `longitude`: column 6
- `feature_code`: column 8
- `country_code`: column 9
- `admin1_code`: column 11
- `admin2_code`: column 12
- `admin3_code`: column 13
- `admin4_code`: column 14
- `population`: column 15

### `search_index`

```sql
CREATE TABLE search_index (
    norm_name TEXT NOT NULL,
    name_priority INTEGER NOT NULL,
    population INTEGER NOT NULL,
    geoname_id INTEGER NOT NULL,
    matched_name TEXT NOT NULL,
    primary_name TEXT NOT NULL,
    asciiname TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    feature_code TEXT,
    country_code TEXT,
    admin1_code TEXT,
    admin2_code TEXT,
    admin3_code TEXT,
    admin4_code TEXT,
    PRIMARY KEY (norm_name, name_priority, population DESC, geoname_id)
) WITHOUT ROWID;
```

Design notes:

- one row per normalized city name variant per `geoname_id`
- rows are clustered by `norm_name`, then by ranking columns
- query paths do not need to join back to `geonames`
- `name_priority` ranking:
  - `0`: primary name
  - `1`: `asciiname`
  - `2`: inline alternate name from `cities500`

### `prefix_cache`

```sql
CREATE TABLE prefix_cache (
    prefix TEXT NOT NULL,
    rank INTEGER NOT NULL,
    name_priority INTEGER NOT NULL,
    population INTEGER NOT NULL,
    geoname_id INTEGER NOT NULL,
    matched_name TEXT NOT NULL,
    primary_name TEXT NOT NULL,
    asciiname TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    feature_code TEXT,
    country_code TEXT,
    admin1_code TEXT,
    admin2_code TEXT,
    admin3_code TEXT,
    admin4_code TEXT,
    PRIMARY KEY (prefix, rank)
) WITHOUT ROWID;
```

Design notes:

- stores precomputed top results for prefixes with length `1..4`
- ranking is `name_priority ASC`, `population DESC`, `geoname_id ASC`
- intended for very short prefixes such as `s`, `sa`, `san`, `bei`
- avoids the temp sort that a broad prefix scan would otherwise need

## Normalization

Search input and imported names use the same normalization rule:

1. Unicode `NFKC`
2. lowercase
3. trim leading and trailing whitespace
4. collapse internal whitespace to a single ASCII space

Reference Python implementation:

```python
import re
import unicodedata

WHITESPACE_RE = re.compile(r"\s+")

def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return WHITESPACE_RE.sub(" ", normalized)
```

## Indexes

```sql
CREATE INDEX idx_geonames_country_feature
    ON geonames(country_code, feature_code);

CREATE INDEX idx_search_index_country_norm
    ON search_index(country_code, norm_name, name_priority, population DESC, geoname_id);

CREATE INDEX idx_search_index_geoname_id
    ON search_index(geoname_id);
```

## Query Contract

### Lookup flow

1. Normalize user input into `:query_norm`.
2. Run an exact lookup on `search_index`.
3. If fewer than 5 rows are returned:
   - use `prefix_cache` when `LENGTH(:query_norm) <= 4`
   - otherwise use a prefix range lookup on `search_index`
4. Return the first 5 rows from exact-first ordering.

This keeps lookup on single-table reads and avoids FTS joins.

### Prefix upper bound

SQLite can use the primary key for prefix search when the application provides an exclusive upper bound.

Reference Python helper:

```python
def next_prefix(value: str) -> str:
    return value + "\U0010ffff"
```

Then the prefix predicate is:

```sql
norm_name >= :query_norm AND norm_name < :query_upper
```

### Exact query

```sql
SELECT
    geoname_id,
    primary_name,
    asciiname,
    matched_name,
    latitude,
    longitude,
    feature_code,
    country_code,
    admin1_code,
    admin2_code,
    admin3_code,
    admin4_code,
    population
FROM search_index
WHERE norm_name = :query_norm
ORDER BY
    name_priority ASC,
    population DESC,
    geoname_id ASC
LIMIT 5;
```

### Prefix query

Short prefix, fastest path:

```sql
SELECT
    geoname_id,
    primary_name,
    asciiname,
    matched_name,
    latitude,
    longitude,
    feature_code,
    country_code,
    admin1_code,
    admin2_code,
    admin3_code,
    admin4_code,
    population
FROM prefix_cache
WHERE prefix = :query_norm
ORDER BY rank ASC
LIMIT 5;
```

Longer prefix fallback:

```sql
SELECT
    geoname_id,
    primary_name,
    asciiname,
    matched_name,
    latitude,
    longitude,
    feature_code,
    country_code,
    admin1_code,
    admin2_code,
    admin3_code,
    admin4_code,
    population
FROM search_index
WHERE norm_name >= :query_norm
  AND norm_name < :query_upper
  AND norm_name <> :query_norm
ORDER BY
    norm_name ASC,
    name_priority ASC,
    population DESC,
    geoname_id ASC
LIMIT 5;
```

### Exact-first template

If `LENGTH(:query_norm) <= 4`, prefer `prefix_cache` in the second branch.
If `LENGTH(:query_norm) > 4`, use the `search_index` range scan.

```sql
WITH exact_hits AS (
    SELECT
        geoname_id,
        primary_name,
        asciiname,
        matched_name,
        latitude,
        longitude,
        feature_code,
        country_code,
        admin1_code,
        admin2_code,
        admin3_code,
        admin4_code,
        population
    FROM search_index
    WHERE norm_name = :query_norm
    ORDER BY
        name_priority ASC,
        population DESC,
        geoname_id ASC
    LIMIT 5
),
prefix_hits AS (
    SELECT
        geoname_id,
        primary_name,
        asciiname,
        matched_name,
        latitude,
        longitude,
        feature_code,
        country_code,
        admin1_code,
        admin2_code,
        admin3_code,
        admin4_code,
        population
    FROM search_index
    WHERE norm_name >= :query_norm
      AND norm_name < :query_upper
      AND norm_name <> :query_norm
    ORDER BY
        norm_name ASC,
        name_priority ASC,
        population DESC,
        geoname_id ASC
    LIMIT 5
)
SELECT * FROM exact_hits
UNION ALL
SELECT * FROM prefix_hits
LIMIT 5;
```

## Builder CLI

```bash
python3 build_db.py \
  --cities-zip source/cities500.zip \
  --output data/geonames.sqlite3 \
  --rebuild
```

## Benchmarking

Use `benchmark_db.py` to benchmark the current build and query paths.
The current recorded baseline lives in `docs/benchmark_baseline.md`.

Backward compatibility:

- `--all-countries-zip` is accepted as an alias for `--cities-zip`
- `--alternate-names-zip` is ignored in the optimized build path
