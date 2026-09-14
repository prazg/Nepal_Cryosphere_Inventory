# Changelog

## 1.0.0 — 2026-09-01

First release.

### Added
- Glacier inventory: 4,480 glaciers with their representative point in Nepal,
  4,215.4 km² of ice, clipped from RGI 7.0 regions 14 and 15 with
  transboundary-aware equal-area figures.
- Annual ITS_LIVE surface velocity, 1987–2025, 172,905 glacier-year records.
- Glacial lake inventory: 1,429 lakes, 81.04 km², for 2022, with lake type from
  Hi-MAG and a 2016–17 vs 2022–24 change pair.
- Lake-terminating flag for 201 glaciers — the attribute RGI 7.0 leaves
  unassigned (`term_type = 9`) for every glacier in region 15.
- Outburst flood linkage from HMAGLOFDB v4.
- Interactive dashboard and two standalone summary pages.
- Reproducible five-step pipeline with per-tile caching.

### Deliberately excluded
- **Any velocity trend.** A naive 2000s vs 2016–2024 comparison gives a median
  46% slowdown across 96% of glaciers. It tracks the collapse in ITS_LIVE
  measurement error, not glacier dynamics: median signal-to-noise is 1.59 in
  the 2000s against 12.08 today, and speed is positive-definite so noise biases
  it upward. `velocity_change_interpretable` is False for every record.
- **Any hazard or danger ranking.** The inputs required are not in these
  sources. See CONTRIBUTING.md.

### Fixed before first push
- The lake GeoPackage duplicated the entire glacier layer (~20 MB of redundancy);
  the lake-terminating flags live in the glacier file, where they belong.
- All output geometry carried an all-zero Z dimension inherited from the RGI
  shapefiles, inflating every file by roughly a third.
- The same two tables were versioned three times over as GeoPackage, GeoParquet
  and CSV. Only the GeoPackage is kept; `make formats` regenerates the rest.
- Province boundaries carried 141,198 vertices for seven context-only polygons,
  simplified to 9,616 at 100 m.
- Coordinates snapped to a 1e-5 degree (~1.1 m) grid, far finer than the 30 m
  source imagery; total area changes by under 0.001%.
- Time series moved from gzipped CSV to Parquet with narrowed dtypes, 4.4 -> 3.2 MB.
- Together: `data/` fell from 51 MB to 25 MB, largest file 27 MB to 13.1 MB,
  with no loss of records, fields or precision.

### Added
- ICIMOD 2020 glacier outlines for Nepal (doi:10.26066/rds.1973447, CC BY 4.0):
  3,973 glaciers, 3,519 km², 280 km³ of modelled ice volume, published as
  `data/icimod_hkh_glaciers_2020_nepal.gpkg` and as a toggleable map layer.
- Lake ice contact recomputed against the 2020 margin: `dist_to_ice2020_m`,
  `ice_contact_2020`, `lost_ice_contact_since_1999`. Contact falls from 260
  lakes to 130; 143 lakes have been left behind by a retreating terminus.
- The expansion signal sharpens under the correction, from 32.9% vs 8.9%
  against 1999 margins to 46.4% vs 4.0% against 2020, and the gradient with
  distance to ice becomes monotonic.

### Fixed
- **Lake `province` was scrambled.** The projected copy of the lake frame was
  taken before a filter dropped 21 rows, so pairing it with the filtered frame
  aligned each surviving lake to a different lake's centroid — every lake after
  the first drop carried the wrong province. Province totals stayed plausible,
  which is what made it hard to spot. Glaciers were unaffected.
- Province and district are now computed by point-in-polygon against
  OpenStreetMap (`admin_level` 4 and 6), replacing geoBoundaries ADM1, and
  `district` is new. Names follow current OSM usage, so "Province 1" is now
  "Koshi Province".
- The spatial join aligns on the index rather than by position, so a point
  landing on a shared boundary can no longer shift every later value.

### Known limitations
- RGI outlines date from a median of 1999 while lakes are 2022, so ice-contact
  judgements overstate contact for retreating glaciers.
- Small lakes are under-counted: the source reports ~25% detection below
  5,400 m² against ~96% for 20,000–100,000 m².
- The Kalapani–Limpiyadhura boundary is disputed; this build follows
  geoBoundaries gbOpen ADM0.
- ICIMOD's Nepal-specific lake inventory could not be obtained.
