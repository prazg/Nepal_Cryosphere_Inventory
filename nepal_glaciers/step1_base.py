"""Step 1 - RGI 7.0 outlines -> Nepal base inventory."""
import zipfile, io, sys
import numpy as np, pandas as pd, geopandas as gpd, requests
from shapely.geometry import box
from .config import (RAW, BUILD, RGI_MIRROR, RGI_REGIONS, BOUNDARIES, AEA_NEPAL)


def fetch(url, dest, timeout=900):
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    print(f"  downloading {dest.name} ...", flush=True)
    r = requests.get(url, timeout=timeout, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    return dest


def fetch_inputs():
    for k, url in BOUNDARIES.items():
        fetch(url, RAW / f"npl_{k}.geojson")
    for reg, stem in RGI_REGIONS.items():
        z = fetch(f"{RGI_MIRROR}/{stem}.zip", RAW / f"RGI7_G_{reg}.zip")
        d = RAW / f"rgi{reg}"
        if not d.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(d)


def build():
    fetch_inputs()
    npl = gpd.read_file(RAW / "npl_adm0.geojson").to_crs(4326)
    npl_u = npl.union_all()
    prov = gpd.read_file(RAW / "npl_adm1.geojson").to_crs(4326)[["shapeName", "geometry"]]
    prov = prov.rename(columns={"shapeName": "province"})

    minx, miny, maxx, maxy = npl_u.bounds
    bbox = box(minx - .3, miny - .3, maxx + .3, maxy + .3)

    frames, hyps = [], []
    for reg, stem in RGI_REGIONS.items():
        shp = RAW / f"rgi{reg}" / f"{stem}.shp"
        g = gpd.read_file(shp, bbox=bbox)
        frames.append(g)
        h = pd.read_csv(RAW / f"rgi{reg}" / f"{stem}-hypsometry.csv", low_memory=False)
        hyps.append(h)
        print(f"  RGI{reg}: {len(g):,} glaciers in Nepal bbox")

    rgi = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True),
                           geometry="geometry", crs=4326)

    # Two membership definitions, both retained.
    pts = gpd.GeoSeries(gpd.points_from_xy(rgi.cenlon, rgi.cenlat), crs=4326)
    rep_in = pts.within(npl_u).values
    touches = rgi.intersects(npl_u).values

    sel = rgi[touches].copy().reset_index(drop=True)
    sel["rep_point_in_nepal"] = rep_in[touches]

    # Equal-area areas: full glacier vs. the part inside Nepal.
    ea = sel.to_crs(AEA_NEPAL)
    npl_ea = gpd.GeoSeries([npl_u], crs=4326).to_crs(AEA_NEPAL).iloc[0]
    sel["area_km2_glacier_total"] = (ea.geometry.area / 1e6).values
    sel["area_km2_within_nepal"] = (ea.geometry.intersection(npl_ea).area / 1e6).values
    sel["frac_within_nepal"] = (sel.area_km2_within_nepal /
                                sel.area_km2_glacier_total).clip(0, 1)
    sel["is_transboundary"] = sel.frac_within_nepal < 0.99

    # Province of the representative point (may be NA for transboundary ice).
    rp = gpd.GeoDataFrame(sel[["rgi_id"]],
                          geometry=gpd.points_from_xy(sel.cenlon, sel.cenlat), crs=4326)
    sel["province"] = gpd.sjoin(rp, prov, how="left",
                                predicate="within")["province"].values

    # Hypsometry-derived debris-free proxy metrics.
    hyp = pd.concat(hyps, ignore_index=True)
    band_cols = [c for c in hyp.columns if c not in ("rgi_id", "area_km2")]
    bands = np.array([float(c) for c in band_cols])
    H = hyp.set_index("rgi_id").reindex(sel.rgi_id)[band_cols].to_numpy(float)
    frac = H / 1000.0  # RGI hypsometry is per-mille of glacier area per band
    with np.errstate(invalid="ignore", divide="ignore"):
        cum = np.nancumsum(frac, axis=1)
        # Area-weighted median elevation from hypsometry (independent of zmed_m)
        idx = (cum >= 0.5).argmax(axis=1)
        sel["z_hyps_median_m"] = bands[idx]
        # Fraction of glacier area below 5000 m - melt-exposed portion
        sel["frac_area_below_5000m"] = np.nansum(frac[:, bands < 5000], axis=1)

    sel["src_year"] = pd.to_datetime(sel.src_date, errors="coerce").dt.year

    out = BUILD / "step1_base.gpkg"
    sel.to_file(out, layer="glaciers", driver="GPKG")
    prov.to_file(out, layer="provinces", driver="GPKG")
    print(f"  -> {len(sel):,} glaciers | "
          f"{sel.area_km2_within_nepal.sum():,.1f} km2 inside Nepal | "
          f"{int(sel.is_transboundary.sum())} transboundary")
    return sel


if __name__ == "__main__":
    build()
