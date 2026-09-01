"""
Step 4 - Nepal glacial lake inventory, linked to the RGI 7.0 glacier inventory.

Three sources, each doing a different job:

  KV2026  Kumar & Vijay (2026), Zenodo 10.5281/zenodo.17948783, CC-BY-4.0.
          Automated Landsat-8/Sentinel-1/Sentinel-2 mapping, built on RGI 7.0
          with a 12.5 km buffer. Supplies CURRENT lake extents (2022) and a
          matched change pair (2016-17 vs 2022-24). No lake-type attribute.

  Hi-MAG  Chen et al. (2021), Zenodo 4275164, CC-BY-4.0. Annual 30 m lakes
          2008-2017, semi-automatic with manual correction. Supplies the
          LAKE TYPE label (proglacial / supraglacial / unconnected) and an
          annual area time series. Ends 2017.

  HMAGLOFDB v4  Recorded outburst floods (project directory).

Lake type is taken from Hi-MAG where a lake matches, because Hi-MAG classified
against glacier outlines contemporaneous with its own imagery. Geometry
relative to RGI 7.0 is computed as a SUPPLEMENT, never as the primary type,
because RGI outlines for Nepal date from a median of 1999 while the lakes are
2022 - roughly two decades of terminus retreat sit between them.
"""
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import box
from .config import RAW, BUILD, OUT, AEA_NEPAL, GLOF_CSV, GLOF_ENCODING
from .step3_export import drop_z

# A lake is "glacial" for our purposes if within this distance of RGI 7.0 ice.
# KV2026 used 12.5 km when building their zones of interest; we keep the same
# so we neither add nor remove lakes relative to the published inventory.
GLACIAL_BUFFER_KM = 12.5
CONTACT_M = 60.0          # ~2 Sentinel-2 pixels: "touching the 1999 margin"
MATCH_M = 150.0           # centroid tolerance when matching lakes across sources
GLOF_MATCH_M = 3000.0


def _nepal():
    npl = gpd.read_file(RAW / "npl_adm0.geojson").to_crs(4326)
    prov = gpd.read_file(RAW / "npl_adm1.geojson").to_crs(4326)[["shapeName", "geometry"]]
    return npl.union_all(), prov.rename(columns={"shapeName": "province"})


def _load_kv(stem, npl_u, area_col="Area"):
    minx, miny, maxx, maxy = npl_u.bounds
    g = gpd.read_file(RAW / "kv26" / f"{stem}.shp",
                      bbox=box(minx - .2, miny - .2, maxx + .2, maxy + .2))
    if g.crs is None:
        g = g.set_crs(4326)
    return g.to_crs(4326)


def _himag_nepal(npl_u):
    """Hi-MAG annual lakes clipped to Nepal, all years."""
    import glob
    minx, miny, maxx, maxy = npl_u.bounds
    bb = box(minx - .2, miny - .2, maxx + .2, maxy + .2)
    parts = []
    for p in sorted(glob.glob("raw/himag/**/Hi_MAG_database_*.shp", recursive=True)):
        g = gpd.read_file(p).to_crs(4326)
        g = g[g.intersects(bb)]
        parts.append(g)
    h = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)
    h["GL_Area_m2"] = h.GL_Area
    return h


def build():
    npl_u, prov = _nepal()
    gl = gpd.read_file(BUILD / "step3_inventory.gpkg", layer="glaciers")

    # ---- current lake layer (KV2026, 2022) --------------------------------
    lk = _load_kv("Glacial_Lake_2022", npl_u)
    lk = lk[lk.intersects(npl_u)].reset_index(drop=True)
    lk = lk.rename(columns={"ID": "lake_id", "Lake_Elev": "elev_m",
                            "Area": "area_m2_src", "Image_ID": "src_image"})
    print(f"  KV2026 2022: {len(lk):,} lakes intersect Nepal")

    ea = AEA_NEPAL
    lk_ea = lk.to_crs(ea)
    lk["area_km2"] = lk_ea.area / 1e6
    npl_ea = gpd.GeoSeries([npl_u], crs=4326).to_crs(ea).iloc[0]
    lk["area_km2_within_nepal"] = lk_ea.intersection(npl_ea).area / 1e6
    lk["frac_within_nepal"] = (lk.area_km2_within_nepal / lk.area_km2).clip(0, 1)
    lk["centroid_in_nepal"] = lk_ea.centroid.to_crs(4326).within(npl_u).values

    # ---- geometry relative to RGI 7.0 ice ---------------------------------
    gl_ea = gl.to_crs(ea)[["rgi_id", "glac_name", "area_km2_glacier_total",
                           "zmin_m", "v_mean_2016_2024", "velocity_current_usable",
                           "geometry"]]
    j = gpd.sjoin_nearest(lk_ea[["lake_id", "geometry"]], gl_ea, how="left",
                          distance_col="dist_m")
    j = j.drop_duplicates("lake_id")
    lk = lk.merge(j.drop(columns="geometry").rename(columns={
        "rgi_id": "nearest_rgi_id", "glac_name": "nearest_glacier_name",
        "area_km2_glacier_total": "nearest_glacier_km2",
        "zmin_m": "nearest_glacier_zmin_m",
        "v_mean_2016_2024": "nearest_glacier_v_m_yr",
        "velocity_current_usable": "nearest_glacier_v_usable",
        "dist_m": "dist_to_rgi1999_m"}).drop(columns="index_right", errors="ignore"),
        on="lake_id", how="left")
    lk = lk[lk.dist_to_rgi1999_m <= GLACIAL_BUFFER_KM * 1000].reset_index(drop=True)

    # Supplementary geometric class. NOT the primary type - see module docstring.
    lk["geom_class_vs_rgi1999"] = np.where(
        lk.dist_to_rgi1999_m == 0, "within 1999 ice outline",
        np.where(lk.dist_to_rgi1999_m <= CONTACT_M, "at 1999 ice margin",
                 np.where(lk.dist_to_rgi1999_m <= 1000, "within 1 km of 1999 ice",
                          "detached (>1 km)")))

    # ---- lake type from Hi-MAG -------------------------------------------
    him = _himag_nepal(npl_u)
    h17 = him[him.GL_Year == 2017].to_crs(ea)
    h17 = h17.assign(geometry=h17.centroid)
    cand = gpd.sjoin_nearest(lk_ea[["lake_id", "geometry"]], 
                             h17[["GL_Type", "GL_ID", "geometry"]],
                             how="left", max_distance=MATCH_M, distance_col="d")
    cand = cand.sort_values("d").drop_duplicates("lake_id")
    lk = lk.merge(cand[["lake_id", "GL_Type", "GL_ID", "d"]].rename(columns={
        "GL_Type": "lake_type_himag2017", "GL_ID": "himag_id",
        "d": "himag_match_dist_m"}), on="lake_id", how="left")
    print(f"  lake type from Hi-MAG 2017: {lk.lake_type_himag2017.notna().sum():,}"
          f" of {len(lk):,} lakes matched within {MATCH_M:.0f} m")

    # ---- Hi-MAG annual area time series ----------------------------------
    hall = him.to_crs(ea)
    hall = hall.assign(geometry=hall.centroid)
    ts = gpd.sjoin_nearest(lk_ea[["lake_id", "geometry"]],
                           hall[["GL_Year", "GL_Area_m2", "geometry"]],
                           how="inner", max_distance=MATCH_M, distance_col="d")
    ts = (ts.sort_values("d").drop_duplicates(["lake_id", "GL_Year"])
            .rename(columns={"GL_Year": "year", "GL_Area_m2": "area_m2"})
            [["lake_id", "year", "area_m2"]].sort_values(["lake_id", "year"]))
    print(f"  Hi-MAG annual series: {ts.lake_id.nunique():,} lakes, "
          f"{len(ts):,} lake-year records, {ts.year.min()}-{ts.year.max()}")

    # ---- 2016-17 vs 2022-24 change (KV2026 matched pair) ------------------
    e0 = _load_kv("Glacial_lakes_2016_2017_median", npl_u).to_crs(ea)
    e1 = _load_kv("Glacial_lakes_2022_2024_median", npl_u).to_crs(ea)
    for d in (e0, e1):
        d["a_km2"] = d.area / 1e6
    e0c = e0.assign(geometry=e0.centroid)
    m = gpd.sjoin_nearest(lk_ea[["lake_id", "geometry"]],
                          e1.assign(geometry=e1.centroid)[["a_km2", "Num_Images", "geometry"]],
                          how="left", max_distance=MATCH_M, distance_col="d")
    m = m.sort_values("d").drop_duplicates("lake_id").rename(
        columns={"a_km2": "area_km2_2022_2024", "Num_Images": "n_images_late"})
    m0 = gpd.sjoin_nearest(lk_ea[["lake_id", "geometry"]],
                           e0c[["a_km2", "Num_Images", "geometry"]],
                           how="left", max_distance=MATCH_M, distance_col="d0")
    m0 = m0.sort_values("d0").drop_duplicates("lake_id").rename(
        columns={"a_km2": "area_km2_2016_2017", "Num_Images": "n_images_early"})
    lk = (lk.merge(m[["lake_id", "area_km2_2022_2024", "n_images_late"]], on="lake_id", how="left")
            .merge(m0[["lake_id", "area_km2_2016_2017", "n_images_early"]], on="lake_id", how="left"))
    lk["area_change_km2"] = lk.area_km2_2022_2024 - lk.area_km2_2016_2017
    lk["area_change_pct"] = 100 * lk.area_change_km2 / lk.area_km2_2016_2017.replace(0, np.nan)

    # KV2026's own change criteria: drop lakes <0.01 km2, require >=3 clear
    # images in each period, and treat +-0.005 km2 as within noise.
    lk["change_usable"] = ((lk.area_km2_2016_2017 >= 0.01) &
                           (lk.n_images_early >= 3) & (lk.n_images_late >= 3) &
                           lk.area_change_km2.notna())
    lk["change_class"] = np.where(~lk.change_usable, "not assessed",
                          np.where(lk.area_change_km2 > 0.005, "expanding",
                          np.where(lk.area_change_km2 < -0.005, "shrinking", "stable")))

    # ---- province and GLOF ------------------------------------------------
    cpt = gpd.GeoDataFrame(lk[["lake_id"]],
                           geometry=lk_ea.centroid.to_crs(4326), crs=4326)
    lk["province"] = gpd.sjoin(cpt, prov, how="left", predicate="within")["province"].values

    glof = pd.read_csv(GLOF_CSV, encoding=GLOF_ENCODING, low_memory=False)
    glof = glof[glof.Country.astype(str).str.contains("Nepal", case=False, na=False)].copy()
    for c in ("Lat_lake", "Lon_lake"):
        glof[c] = pd.to_numeric(glof[c], errors="coerce")
    glof["year"] = pd.to_numeric(glof.Year_approx, errors="coerce")
    glof = glof.dropna(subset=["Lat_lake", "Lon_lake"])
    gpts = gpd.GeoDataFrame(glof, geometry=gpd.points_from_xy(glof.Lon_lake, glof.Lat_lake),
                            crs=4326).to_crs(ea)
    gj = gpd.sjoin_nearest(gpts, lk_ea[["lake_id", "geometry"]], how="left",
                           max_distance=GLOF_MATCH_M, distance_col="d")
    cnt = gj.groupby("lake_id").size().rename("glof_events_recorded")
    lastyr = gj.groupby("lake_id").year.max().rename("glof_year_last")
    lk = lk.merge(cnt, on="lake_id", how="left").merge(lastyr, on="lake_id", how="left")
    lk["glof_events_recorded"] = lk.glof_events_recorded.fillna(0).astype(int)
    print(f"  GLOF: {gj.lake_id.notna().sum()} of {len(gpts)} Nepal events matched "
          f"to a 2022 lake within {GLOF_MATCH_M/1000:.0f} km")

    lk["size_class"] = pd.cut(lk.area_km2, [0, .02, .1, .5, 1, 1e9],
                              labels=["<0.02", "0.02-0.1", "0.1-0.5", "0.5-1", ">1"])

    # ---- back-propagate to the glacier inventory -------------------------
    # This is what fills the RGI term_type = 9 gap.
    contact = lk[(lk.dist_to_rgi1999_m <= CONTACT_M) & lk.nearest_rgi_id.notna()]
    agg = contact.groupby("nearest_rgi_id").agg(
        n_contact_lakes=("lake_id", "size"),
        contact_lake_km2=("area_km2", "sum"),
        largest_contact_lake_km2=("area_km2", "max")).reset_index()
    agg = agg.rename(columns={"nearest_rgi_id": "rgi_id"})
    gl2 = gl.merge(agg, on="rgi_id", how="left")
    for c in ("n_contact_lakes", "contact_lake_km2", "largest_contact_lake_km2"):
        gl2[c] = gl2[c].fillna(0)
    gl2["has_contact_lake_1999_geom"] = gl2.n_contact_lakes > 0
    # Hi-MAG proglacial label agrees?
    pro = lk[lk.lake_type_himag2017.astype(str).str.contains("proglacial", na=False)]
    gl2["has_proglacial_lake_himag"] = gl2.rgi_id.isin(
        pro[pro.dist_to_rgi1999_m <= CONTACT_M].nearest_rgi_id)
    print(f"  glaciers flagged lake-contact: {int(gl2.has_contact_lake_1999_geom.sum())} "
          f"(Hi-MAG proglacial agreement: {int(gl2.has_proglacial_lake_himag.sum())})")

    lk = drop_z(lk.set_geometry(lk.geometry))
    gl2 = drop_z(gl2)
    lk.to_file(BUILD / "step4_lakes.gpkg", layer="lakes", driver="GPKG")
    ts.to_parquet(BUILD / "step4_lake_area_annual.parquet", index=False)
    gl2.to_file(BUILD / "step4_glaciers_with_lakes.gpkg", layer="glaciers", driver="GPKG")
    return lk, ts, gl2


if __name__ == "__main__":
    build()
