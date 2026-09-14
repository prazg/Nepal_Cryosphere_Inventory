"""
Step 6 - ICIMOD 2020 glacier outlines, and ice contact recomputed against them.

Source: ICIMOD (2026), "Decadal glacier changes from 1990 to 2020 in the Hindu
Kush Himalaya", doi:10.26066/rds.1973447, CC BY 4.0. Landsat 1990/2000/2010/2020,
+-1 year window, mapped at 1:50,000 with a 0.02 km2 minimum area, areas and
topography from the void-filled SRTM v4 DEM in Albers Equal Area.

WHY THIS MATTERS HERE
RGI 7.0's Nepal outlines have a median source year of 1999. Every ice-contact
judgement in the lake inventory was therefore made against a margin roughly two
decades stale, and overstated contact for any glacier that has since retreated.
By how much: 260 lakes touch the 1999 margin, 130 touch the 2020 margin.

WHAT THIS DOES NOT DO
It does not measure glacier change. RGI and ICIMOD disagree in both directions -
1,009 km2 of RGI ice is absent from ICIMOD 2020 and 1,388 km2 of ICIMOD ice is
absent from RGI - so differencing the two mixes real retreat with mapping
method, analyst and imagery differences. A defensible change figure needs
ICIMOD's own 1990/2000/2010 layers, which are part of the same publication but
are not shipped here. The glacier base layer therefore stays RGI 7.0, for
continuity with the velocity extraction, and ICIMOD 2020 is added alongside it.
"""
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from .config import RAW, BUILD, OUT, AEA_NEPAL
from .formats import grid

CONTACT_M = 60.0          # ~2 Sentinel-2 pixels, same bar used against RGI
SHP = RAW / "icimod" / "hkh_glacier_2020.shp"


def load_nepal(shp=SHP):
    """ICIMOD 2020 glaciers clipped to Nepal, with equal-area figures."""
    if not shp.exists():
        raise FileNotFoundError(
            f"ICIMOD 2020 outlines not found at {shp}.\n"
            "  Download 'Decadal glacier changes from 1990 to 2020 in the HKH'\n"
            "  (doi:10.26066/rds.1973447) and place the shapefile there.")
    npl = gpd.read_file(RAW / "npl_adm0.geojson").to_crs(4326).union_all()
    minx, miny, maxx, maxy = npl.bounds

    head = gpd.read_file(shp, max_features=1)
    bb = gpd.GeoSeries([box(minx - .4, miny - .4, maxx + .4, maxy + .4)],
                       crs=4326).to_crs(head.crs).total_bounds
    g = gpd.read_file(shp, bbox=tuple(bb)).to_crs(4326)
    g = g[g.intersects(npl)].reset_index(drop=True)

    pt = gpd.GeoSeries(gpd.points_from_xy(g.Longitude, g.Latitude), crs=4326)
    g["rep_point_in_nepal"] = pt.within(npl).values
    ea = g.to_crs(AEA_NEPAL)
    nea = gpd.GeoSeries([npl], crs=4326).to_crs(AEA_NEPAL).iloc[0]
    g["area_km2_geom"] = (ea.area / 1e6).values
    g["area_km2_within_nepal"] = (ea.intersection(nea).area / 1e6).values
    return grid(g)


def build():
    ic = load_nepal()
    lk = gpd.read_file(OUT / "nepal_glacial_lake_inventory.gpkg", layer="lakes")
    gl = gpd.read_file(OUT / "nepal_glacier_inventory.gpkg", layer="glaciers")

    # ---- lake -> nearest 2020 ice ----------------------------------------
    lk_ea, ic_ea = lk.to_crs(AEA_NEPAL), ic.to_crs(AEA_NEPAL)
    j = gpd.sjoin_nearest(
        lk_ea[["lake_id", "geometry"]],
        ic_ea[["GLIMS_ID", "Area_SqKm", "Elv_min", "geometry"]],
        how="left", distance_col="d")
    j = j.sort_values("d").drop_duplicates("lake_id")
    lk = lk.merge(j[["lake_id", "GLIMS_ID", "Area_SqKm", "Elv_min", "d"]].rename(
        columns={"GLIMS_ID": "nearest_glims_2020",
                 "Area_SqKm": "nearest_glacier_2020_km2",
                 "Elv_min": "nearest_glacier_2020_zmin_m",
                 "d": "dist_to_ice2020_m"}), on="lake_id", how="left")

    lk["ice_contact_2020"] = lk.dist_to_ice2020_m <= CONTACT_M
    lk["ice_contact_1999"] = lk.dist_to_rgi1999_m <= CONTACT_M
    lk["lost_ice_contact_since_1999"] = lk.ice_contact_1999 & ~lk.ice_contact_2020

    n99, n20 = int(lk.ice_contact_1999.sum()), int(lk.ice_contact_2020.sum())
    print(f"  ice contact: {n99} lakes against the 1999 margin, "
          f"{n20} against 2020 ({int(lk.lost_ice_contact_since_1999.sum())} lost contact)")

    # ---- glacier side: flag from the 2020 margin -------------------------
    # Attribute a contact lake to the RGI glacier nearest the lake, so the flag
    # stays joinable to the velocity and hypsometry already keyed on rgi_id.
    contact = lk[lk.ice_contact_2020 & lk.nearest_rgi_id.notna()]
    agg = (contact.groupby("nearest_rgi_id")
           .agg(n_contact_lakes_2020=("lake_id", "size"),
                contact_lake_2020_km2=("area_km2", "sum"))
           .reset_index().rename(columns={"nearest_rgi_id": "rgi_id"}))
    gl = gl.drop(columns=[c for c in agg.columns if c != "rgi_id"], errors="ignore")
    gl = gl.merge(agg, on="rgi_id", how="left")
    for c in ("n_contact_lakes_2020", "contact_lake_2020_km2"):
        gl[c] = gl[c].fillna(0)
    gl["has_contact_lake_2020"] = gl.n_contact_lakes_2020 > 0
    print(f"  glaciers with a lake at the 2020 margin: "
          f"{int(gl.has_contact_lake_2020.sum())} "
          f"(was {int(gl.has_contact_lake_1999_geom.sum())} against 1999)")

    lk.to_file(BUILD / "step6_lakes.gpkg", layer="lakes", driver="GPKG")
    gl.to_file(BUILD / "step6_glaciers.gpkg", layer="glaciers", driver="GPKG")
    ic.to_file(BUILD / "step6_icimod2020.gpkg", layer="icimod_2020", driver="GPKG")
    # Published separately: ICIMOD outlines are finely mapped and would more
    # than double the glacier GeoPackage if bundled into it.
    ic.to_file(OUT / "icimod_hkh_glaciers_2020_nepal.gpkg",
               layer="glaciers_2020", driver="GPKG")
    return ic, lk, gl


if __name__ == "__main__":
    build()
