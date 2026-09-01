"""Step 3 - link recorded GLOF source lakes to glaciers, QC, and export."""
import numpy as np, pandas as pd, geopandas as gpd
from .config import BUILD, OUT, GLOF_CSV, GLOF_ENCODING, AEA_NEPAL, EPOCH_EARLY, EPOCH_LATE

GLOF_SEARCH_KM = 3.0   # lake coordinates are reported to varying precision


def drop_z(gdf):
    """Return gdf with 2D geometry. RGI outlines carry an all-zero Z."""
    if gdf.geometry.has_z.any():
        from shapely import force_2d
        gdf = gdf.copy()
        gdf["geometry"] = force_2d(gdf.geometry.values)
    return gdf


def load_glofs():
    d = pd.read_csv(GLOF_CSV, encoding=GLOF_ENCODING, low_memory=False)
    d = d[d.Country.astype(str).str.contains("Nepal", case=False, na=False)].copy()
    for c in ("Lat_lake", "Lon_lake"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["year"] = pd.to_numeric(d.Year_approx, errors="coerce")
    d = d.dropna(subset=["Lat_lake", "Lon_lake"])
    return gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.Lon_lake, d.Lat_lake),
                            crs=4326)


def build():
    gl = gpd.read_file(BUILD / "step1_base.gpkg", layer="glaciers")
    vel = pd.read_parquet(BUILD / "step2_velocity_summary.parquet")
    ts = pd.read_parquet(BUILD / "step2_velocity_annual.parquet")
    inv = gl.merge(vel, on="rgi_id", how="left")

    # ---- GLOF linkage -----------------------------------------------------
    glof = load_glofs()
    inv_ea, glof_ea = inv.to_crs(AEA_NEPAL), glof.to_crs(AEA_NEPAL)
    j = gpd.sjoin_nearest(glof_ea, inv_ea[["rgi_id", "geometry"]],
                          how="left", max_distance=GLOF_SEARCH_KM * 1000,
                          distance_col="dist_m")
    cnt = j.groupby("rgi_id").size().rename("glof_events_recorded")
    last = j.groupby("rgi_id").year.max().rename("glof_year_last")
    inv = inv.merge(cnt, on="rgi_id", how="left").merge(last, on="rgi_id", how="left")
    inv["glof_events_recorded"] = inv.glof_events_recorded.fillna(0).astype(int)
    matched = j.rgi_id.notna().sum()
    print(f"  GLOF: {len(glof)} Nepal events with coordinates, "
          f"{matched} within {GLOF_SEARCH_KM} km of an RGI 7.0 glacier")

    # ---- derived flags ----------------------------------------------------
    a = f"v_mean_{EPOCH_EARLY[0]}_{EPOCH_EARLY[1]}"
    b = f"v_mean_{EPOCH_LATE[0]}_{EPOCH_LATE[1]}"
    inv["size_class"] = pd.cut(inv.area_km2_glacier_total,
                               [0, .5, 1, 5, 10, 50, 1e9],
                               labels=["<0.5", "0.5-1", "1-5", "5-10", "10-50", ">50"])
    # ---- velocity quality flags ------------------------------------------
    # CURRENT SPEED (2016-2024) is well constrained: image-pair counts are in
    # the thousands and v_error rounds to 0 m/yr. Flag it usable where the
    # glacier holds enough 120 m pixels and clears a signal-to-noise bar.
    inv["velocity_current_usable"] = (inv.n_px_total >= 10) & (inv.snr_late > 3)

    # VELOCITY CHANGE is NOT usable and is retained only for transparency.
    # Median early-epoch SNR across Nepal is ~1.6: 2000s speeds sit at the
    # noise floor. Because v = hypot(vx, vy) is positive-definite, noise biases
    # speed upward, so early years read fast and every comparison manufactures
    # an apparent slowdown. Gating on early SNR does not fix this - it selects
    # the noise-inflated glaciers and adds regression to the mean on top.
    # Do not publish v_change_pct as a physical trend.
    inv["velocity_change_interpretable"] = False

    # ---- QC ---------------------------------------------------------------
    qc = {
        "glaciers_intersecting_nepal": int(len(inv)),
        "glaciers_rep_point_in_nepal": int(inv.rep_point_in_nepal.sum()),
        "transboundary_glaciers": int(inv.is_transboundary.sum()),
        "area_km2_within_nepal": round(float(inv.area_km2_within_nepal.sum()), 1),
        "area_km2_glacier_total": round(float(inv.area_km2_glacier_total.sum()), 1),
        "rgi_source_year_min": int(inv.src_year.min()),
        "rgi_source_year_max": int(inv.src_year.max()),
        "rgi_source_year_median": int(inv.src_year.median()),
        "glaciers_with_any_velocity": int(inv.n_px_total.notna().sum()),
        "glaciers_velocity_current_usable": int(inv.velocity_current_usable.sum()),
        "median_snr_early_epoch": round(float(inv.snr_early.median()), 2),
        "median_snr_late_epoch": round(float(inv.snr_late.median()), 2),
        "velocity_year_last": int(ts.year.max()),
        "glacier_year_records": int(len(ts)),
        "glof_events_nepal_georeferenced": int(len(glof)),
        "glaciers_with_recorded_glof": int((inv.glof_events_recorded > 0).sum()),
        "term_type_assigned": int((inv.term_type != 9).sum()),
    }
    for k, v in qc.items():
        print(f"    {k:38s} {v:,}")

    # ---- export -----------------------------------------------------------
    # RGI shapefiles carry an all-zero Z dimension. Keeping it inflates every
    # output by roughly a third and conveys nothing, so drop it here.
    inv = drop_z(inv)
    from .formats import grid, vacuum
    inv = grid(inv)

    OUT.mkdir(parents=True, exist_ok=True)
    gpkg = OUT / "nepal_glacier_inventory.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    inv.to_file(gpkg, layer="glaciers", driver="GPKG")
    glof.to_file(gpkg, layer="glof_events", driver="GPKG")
    gpd.read_file(BUILD / "step1_base.gpkg", layer="provinces").to_file(
        gpkg, layer="provinces", driver="GPKG")

    vacuum(gpkg)

    # Annual velocity: 172,905 rows. Parquet with narrowed dtypes is 3.2 MB
    # against 4.4 MB gzipped CSV, and keeps the types on read.
    ts = ts.copy()
    ts["year"] = ts.year.astype("int16")
    for c in ("n_valid_px", "n_px_total"):
        ts[c] = ts[c].astype("int32")
    for c in ("v_mean_m_yr", "v_max_m_yr", "v_error_m_yr", "img_pairs"):
        if c in ts:
            ts[c] = ts[c].astype("float32")
    ts["rgi_id"] = ts.rgi_id.astype("category")
    ts.to_parquet(OUT / "nepal_glacier_velocity_annual.parquet",
                  compression="zstd", index=False)

    pd.Series(qc).to_json(BUILD / "qc.json", indent=1)
    inv.to_file(BUILD / "step3_inventory.gpkg", layer="glaciers", driver="GPKG")
    print(f"  -> {gpkg}")
    return inv, ts, qc


if __name__ == "__main__":
    build()
