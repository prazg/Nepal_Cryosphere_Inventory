# Data dictionary

Every field in the published files. Fields whose meaning is easy to misuse are marked in **bold**.

Three things to internalise before using any of this:

1. **`term_type` is useless here.** RGI 7.0 sets it to 9 (unassigned) for every glacier in region 15. Use `has_contact_lake_1999_geom`.
2. **`velocity_change_interpretable` is always False.** The 2000s velocities sit at the noise floor; any epoch comparison measures the decline in measurement error, not glacier dynamics.
3. **`dist_to_rgi1999_m` is a distance to a ~1999 margin**, not to present-day ice. Contact is overstated for glaciers that have retreated.
4. **`province` and `district` come from OpenStreetMap, the national outline from geoBoundaries.** These are independent datasets and disagree slightly along the border. A point inside Nepal but outside every OSM province is assigned its nearest province; a point outside Nepal is left null however close to the line it sits.

---

## `data/nepal_glacier_inventory.gpkg`, layer `glaciers` — 4,679 features, EPSG:4326

The GeoPackage also carries `glof_events` and `provinces` layers. Run `make formats` for CSV and GeoParquet copies — they are derivatives and are not versioned, because storing all three formats tripled `data/` for no extra information.

Coordinates are snapped to a 1e-5 degree grid, about 1.1 m. The outlines derive from 30 m imagery, so this is roughly thirty times finer than the source and lossless in any sense that matters; measured effect on total area is under 0.001%.

| Field | Meaning |
|---|---|
| `rgi_id` | RGI 7.0 unique glacier identifier. |
| `o1region` | RGI first-order region, 14 or 15. Nepal straddles the boundary. |
| `o2region` | RGI second-order region. |
| `glims_id` | GLIMS identifier. |
| `anlys_id` | GLIMS analysis identifier. |
| `subm_id` | GLIMS submission identifier. |
| `src_date` | Acquisition date of the source imagery for this outline. |
| `cenlon` | RGI representative point longitude. |
| `cenlat` | RGI representative point latitude. |
| `utm_zone` | UTM zone of the representative point (informational; geometry is WGS84). |
| `area_km2` | Area as reported by RGI 7.0, km². |
| `primeclass` | RGI primary classification. |
| `conn_lvl` | Connectivity level to an ice sheet (0 in Nepal). |
| `surge_type` | RGI surge classification. |
| `term_type` | RGI terminus type. **Always 9 (unassigned) in region 15 — carries no information here.** Use `has_contact_lake_1999_geom` instead. |
| `glac_name` | Glacier name where RGI carries one. Most Nepali glaciers are unnamed. |
| `is_rgi6` | Whether the outline is carried over unchanged from RGI 6.0. |
| `termlon` | Terminus longitude. |
| `termlat` | Terminus latitude. |
| `zmin_m` | Minimum (terminus) elevation, m. |
| `zmax_m` | Maximum elevation, m. |
| `zmed_m` | RGI median elevation, m. |
| `zmean_m` | RGI mean elevation, m. |
| `slope_deg` | Mean surface slope, degrees. |
| `aspect_deg` | Mean aspect, degrees. |
| `aspect_sec` | Aspect sector. |
| `dem_source` | DEM used for RGI topographic attributes. |
| `lmax_m` | Maximum glacier length, m. |
| `rep_point_in_nepal` | True where the RGI representative point falls inside Nepal. **The strict national subset** used for all headline figures. |
| `area_km2_glacier_total` | Whole-glacier area recomputed in Albers equal-area, km². |
| `area_km2_within_nepal` | Portion of the glacier inside the Nepal ADM0 boundary, km². |
| `frac_within_nepal` | area_km2_within_nepal ÷ area_km2_glacier_total. |
| `is_transboundary` | True where frac_within_nepal < 0.99. |
| `province` | Province containing the representative point, by point-in-polygon against OpenStreetMap `admin_level=4`. Null where the point falls outside Nepal (190 transboundary glaciers). |
| `district` | District containing the representative point, OSM `admin_level=6`. Same null rule. |
| `z_hyps_median_m` | Median elevation recomputed independently from the RGI hypsometry table, m. |
| `frac_area_below_5000m` | Fraction of glacier area below 5000 m. |
| `src_year` | Year of src_date. Median 1999 across Nepal. |
| `v0_m_yr` | ITS_LIVE climatological mean speed over the glacier, m/yr. |
| `dv_dt_m_yr2` | ITS_LIVE fitted velocity trend, m/yr². **Subject to the same noise bias as v_change — not a usable trend.** |
| `n_px_total` | Number of 120 m ITS_LIVE pixels covering the glacier. |
| `v_mean_2000_2009` | Mean annual speed 2000–2009, m/yr. **Noise-dominated.** |
| `v_mean_2000_2009_err` | Mean reported velocity error for that epoch, m/yr. |
| `v_mean_2000_2009_pairs` | Median satellite image pairs per year for that epoch. |
| `v_mean_2016_2024` | Mean annual speed 2016–2024, m/yr. **The headline current-speed field.** |
| `v_mean_2016_2024_err` | Mean reported velocity error for that epoch, m/yr. |
| `v_mean_2016_2024_pairs` | Median satellite image pairs per year for that epoch. |
| `v_change_m_yr` | Late minus early epoch speed, m/yr. **Not interpretable.** |
| `v_change_pct` | Percent change between epochs. **Not interpretable.** |
| `snr_early` | v_mean_2000_2009 ÷ its error. Median across Nepal 1.59 — at the noise floor. |
| `snr_late` | v_mean_2016_2024 ÷ its error. Median across Nepal 12.08. |
| `v_years_observed` | Number of years with at least one valid velocity pixel. |
| `v_year_last` | Most recent year with velocity. |
| `glof_events_recorded` | Recorded outburst floods in HMAGLOFDB v4 whose source lake lies within 3 km. |
| `glof_year_last` | Year of the most recent such event. |
| `size_class` | Area bin, km². |
| `velocity_current_usable` | True where n_px_total ≥ 10 and snr_late > 3. **Filter on this for any current-speed analysis.** |
| `velocity_change_interpretable` | Always False. The epoch comparison is dominated by a change in measurement noise, not glacier dynamics. |
| `n_contact_lakes` | Number of lakes within 60 m of the mapped glacier margin. |
| `contact_lake_km2` | Combined area of those lakes, km². |
| `largest_contact_lake_km2` | Area of the largest, km². |
| `has_contact_lake_1999_geom` | True where at least one lake sits at the mapped margin. **This is the lake-terminating flag RGI does not supply.** Judged against a ~1999 margin. |
| `has_proglacial_lake_himag` | True where a margin lake is independently classified proglacial by Hi-MAG 2017. |

---

## `data/nepal_glacial_lake_inventory.gpkg`, layer `lakes` — 1,429 features, EPSG:4326

The lake-terminating flags derived here are merged into the glacier layer above, so they are not duplicated in this file. Run `make formats` for CSV and GeoParquet copies.

| Field | Meaning |
|---|---|
| `lake_id` | Lake identifier from Kumar & Vijay (2026), encoding centroid lat/lon. |
| `Latitude` | Lake centroid latitude (source). |
| `Longitude` | Lake centroid longitude (source). |
| `src_image` | Sentinel-2 scene used for the 2022 boundary. |
| `elev_m` | Lake surface elevation from Copernicus GLO-30 DEM, m. |
| `area_m2_src` | Lake area as reported by the source, m². |
| `area_km2` | Lake area recomputed in Albers equal-area, km². |
| `area_km2_within_nepal` | Portion inside the Nepal ADM0 boundary, km². |
| `frac_within_nepal` | Ratio of the two. |
| `centroid_in_nepal` | True where the lake centroid falls inside Nepal. |
| `nearest_rgi_id` | RGI 7.0 id of the nearest glacier. |
| `nearest_glacier_name` | Its name where RGI carries one. |
| `nearest_glacier_km2` | Its area, km². |
| `nearest_glacier_zmin_m` | Its terminus elevation, m. |
| `nearest_glacier_v_m_yr` | Its 2016–2024 mean surface speed, m/yr. |
| `nearest_glacier_v_usable` | Whether that speed passes the velocity quality filter. |
| `dist_to_rgi1999_m` | Distance from lake polygon to the nearest RGI 7.0 outline, m. **The outline dates from a median of 1999 — this is not distance to present-day ice, and contact is overstated for retreating glaciers.** |
| `geom_class_vs_rgi1999` | Supplementary geometric class against the 1999 outline. Not the primary lake type. |
| `lake_type_himag2017` | Lake type from Hi-MAG 2017 (proglacial / supraglacial / ice-marginal / unconnected). **Primary type field.** Null where no Hi-MAG lake matched within 150 m. |
| `himag_id` | Matched Hi-MAG lake identifier. |
| `himag_match_dist_m` | Centroid separation of the match, m. |
| `area_km2_2022_2024` | Median lake area over 2022–24, km². |
| `n_images_late` | Cloud-free images contributing to the 2022–24 median. |
| `area_km2_2016_2017` | Median lake area over 2016–17, km². |
| `n_images_early` | Cloud-free images contributing to the 2016–17 median. |
| `area_change_km2` | Late minus early area, km². |
| `area_change_pct` | Percent change between periods. |
| `change_usable` | True where area ≥ 0.01 km² in 2016–17 and ≥ 3 clear images in each period. |
| `change_class` | expanding / shrinking / stable / not assessed. |
| `province` | Province containing the lake centroid, by point-in-polygon against OpenStreetMap `admin_level=4`. Null for the one lake whose centroid lies outside Nepal. |
| `district` | District containing the lake centroid, OSM `admin_level=6`. Same null rule. |
| `glof_events_recorded` | Recorded outburst floods in HMAGLOFDB v4 whose source lake lies within 3 km. |
| `glof_year_last` | Year of the most recent such event. |
| `size_class` | Area bin, km². |

---

## `data/nepal_glacier_velocity_annual.parquet` — 172,905 rows

One row per glacier per year, 1987–2025.

| Field | Meaning |
|---|---|
| `rgi_id` | RGI 7.0 identifier |
| `year` | Calendar year of the ITS_LIVE annual composite |
| `v_mean_m_yr` | Area-mean surface speed over the glacier, m/yr |
| `v_max_m_yr` | Maximum pixel speed within the glacier, m/yr |
| `v_error_m_yr` | Mean reported velocity error, m/yr |
| `img_pairs` | Satellite image pairs contributing to the fit. Rises from ~14 in 1987 to several thousand today — the reason early years are unusable |
| `n_valid_px` | Pixels with a finite velocity |
| `n_px_total` | Pixels covering the glacier |

2025 is a partial year: image-pair counts fall roughly five-fold and apparent speed jumps. It is excluded from the 2016–2024 epoch but present here.

## `data/nepal_lake_area_annual_himag.parquet` — 6,724 rows

One row per lake per year, 2008–2017, from Hi-MAG.

| Field | Meaning |
|---|---|
| `lake_id` | Matches `lake_id` in the lake inventory |
| `year` | Calendar year |
| `area_m2` | Lake area that year, m² |

---

## Web layers, `docs/data/`

Simplified geometry and abbreviated field names, for the map only. **Do not use these for analysis** — geometry is simplified (60 m for glaciers, 15 m for lakes) and coordinates are rounded.

### `glaciers.geojson`
| Field | Meaning |
|---|---|
| `rgi_id` | RGI identifier |
| `nm` | Glacier name, empty if unnamed |
| `g_km2` | Whole-glacier area, km² |
| `g_np` | Area inside Nepal, km² |
| `v` | Mean speed 2016–2024, m/yr |
| `vok` | 1 where the speed passes the quality filter |
| `lake` | 1 where a lake sits at the mapped margin |
| `nlk` | Number of margin lakes |
| `glof` | Recorded outburst floods within 3 km |
| `zmin` | Terminus elevation, m |
| `zmax` | Maximum elevation, m |
| `npl` | 1 where the representative point is inside Nepal |
| `prov` | Province (OSM) |
| `dist` | District (OSM) |
| `yr` | Outline source year |

### `lakes.geojson`
| Field | Meaning |
|---|---|
| `lake_id` | Lake identifier |
| `l_km2` | Area 2022, km² |
| `z` | Elevation, m |
| `typ` | Hi-MAG type, or "unmatched" |
| `d` | Distance to the ~1999 ice margin, m |
| `chg` | Percent area change 2016–17 → 2022–24 |
| `cls` | expanding / stable / shrinking / not assessed |
| `glof` | Recorded outburst floods within 3 km |
| `prov` | Province (OSM) |
| `dist` | District (OSM) |
| `gnm` | Nearest glacier name |
| `rgi` | Nearest glacier RGI id |

### `glof.geojson`
| Field | Meaning |
|---|---|
| `nm` | Lake name as recorded |
| `yr` | Approximate year of the event |
| `typ` | Dam type (moraine dammed, ice dammed, …) |
| `basin` | River basin |

### `summary.json`
Precomputed aggregates for the dashboard charts: `summary` (headline figures), `ghyp` (glacier area by 50 m elevation band), `lhyp` (lake count and area by 100 m band), `diag` (image pairs and velocity error by year), `lann` (annual lake area 2008–2017), `contact` (expansion rate by distance to ice), `prov` (per-province totals), `spd` (size-matched speed comparison).
