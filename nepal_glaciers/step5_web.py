"""
Step 5 - regenerate the web layers under docs/data/ for GitHub Pages.

Geometry is simplified in an equal-area projection and coordinates are rounded,
which takes the glacier layer from 20 MB to about 2.6 MB and the lakes from
19 MB to 0.7 MB. GitHub Pages gzips on the wire, so the transferred size is
smaller again. The full-resolution files stay in data/ and are what you should
use for analysis - the docs/data/ copies exist only to make the map fast.

Simplification tolerances: 60 m for glaciers, 15 m for lakes. Both are well
below the 120 m velocity pixel and the 30 m lake mapping resolution, so the
displayed shapes do not imply more precision than the sources carry.
"""
import json
import numpy as np, pandas as pd, geopandas as gpd
from .config import BUILD, ROOT, AEA_NEPAL, GLOF_CSV, GLOF_ENCODING, RAW

WEB = ROOT / "docs" / "data"
GLACIER_TOL_M = 60
LAKE_TOL_M = 15


def _round_coords(gj, nd):
    def r(c):
        if isinstance(c[0], (list, tuple)):
            return [r(x) for x in c]
        return [round(c[0], nd), round(c[1], nd)]
    for f in gj["features"]:
        f["geometry"]["coordinates"] = r(f["geometry"]["coordinates"])
        f.pop("id", None)
    return gj


def _write(gdf, cols, tol, path, nd):
    geom = gdf.to_crs(AEA_NEPAL).geometry.simplify(tol, preserve_topology=True).to_crs(4326)
    out = gpd.GeoDataFrame(gdf[cols].copy(), geometry=geom.values, crs=4326)
    json.dump(_round_coords(json.loads(out.to_json()), nd),
              open(path, "w"), separators=(",", ":"))
    return path.stat().st_size


def build():
    WEB.mkdir(parents=True, exist_ok=True)
    gl = gpd.read_file(BUILD / "step4_glaciers_with_lakes.gpkg", layer="glaciers")
    lk = gpd.read_file(BUILD / "step4_lakes.gpkg", layer="lakes")
    vts = pd.read_parquet(BUILD / "step2_velocity_annual.parquet")
    lts = pd.read_parquet(BUILD / "step4_lake_area_annual.parquet")
    qg = json.load(open(BUILD / "qc.json"))
    ql = json.load(open(BUILD / "qc_lakes.json"))

    g = gl.assign(
        g_km2=gl.area_km2_glacier_total.round(3), g_np=gl.area_km2_within_nepal.round(3),
        v=gl.v_mean_2016_2024.round(2), vok=gl.velocity_current_usable.astype(int),
        lake=gl.has_contact_lake_1999_geom.astype(int), nlk=gl.n_contact_lakes.astype(int),
        glof=gl.glof_events_recorded.astype(int),
        zmin=gl.zmin_m.round(0), zmax=gl.zmax_m.round(0),
        npl=gl.rep_point_in_nepal.astype(int), nm=gl.glac_name.fillna(""),
        prov=gl.province.fillna(""), dist=gl.district.fillna(""),
        yr=gl.src_year.fillna(0).astype(int))
    s1 = _write(g, ["rgi_id", "nm", "g_km2", "g_np", "v", "vok", "lake", "nlk",
                    "glof", "zmin", "zmax", "npl", "prov", "dist", "yr"],
                GLACIER_TOL_M, WEB / "glaciers.geojson", 4)

    l = lk.assign(
        l_km2=lk.area_km2.round(4), z=lk.elev_m.astype(int),
        typ=lk.lake_type_himag2017.fillna("unmatched"), d=lk.dist_to_rgi1999_m.round(0),
        chg=lk.area_change_pct.round(1), cls=lk.change_class,
        glof=lk.glof_events_recorded.astype(int), prov=lk.province.fillna(""),
        gnm=lk.nearest_glacier_name.fillna(""), rgi=lk.nearest_rgi_id.fillna(""),
        dist_name=lk.district.fillna(""))
    s2 = _write(l, ["lake_id", "l_km2", "z", "typ", "d", "chg", "cls", "glof",
                    "prov", "dist_name", "gnm", "rgi"],
                LAKE_TOL_M, WEB / "lakes.geojson", 5)

    # --- GLOF points -------------------------------------------------------
    gf = pd.read_csv(GLOF_CSV, encoding=GLOF_ENCODING, low_memory=False)
    gf = gf[gf.Country.astype(str).str.contains("Nepal", case=False, na=False)].copy()
    for c in ("Lat_lake", "Lon_lake"):
        gf[c] = pd.to_numeric(gf[c], errors="coerce")
    gf = gf.dropna(subset=["Lat_lake", "Lon_lake"])
    gf["yr"] = pd.to_numeric(gf.Year_approx, errors="coerce")
    feats = [{"type": "Feature",
              "geometry": {"type": "Point", "coordinates": [round(r.Lon_lake, 5), round(r.Lat_lake, 5)]},
              "properties": {"nm": str(r.Lake_name),
                             "yr": (None if pd.isna(r.yr) else int(r.yr)),
                             "typ": str(r.Lake_type), "basin": str(r.River_Basin)}}
             for r in gf.itertuples()]
    json.dump({"type": "FeatureCollection", "features": feats},
              open(WEB / "glof.geojson", "w"), separators=(",", ":"))

    # --- summary + chart series -------------------------------------------
    s = gl[gl.rep_point_in_nepal]
    hyps = [pd.read_csv(RAW / f"rgi{r}" / f"RGI2000-v7.0-G-{n}-hypsometry.csv", low_memory=False)
            for r, n in [(14, "14_south_asia_west"), (15, "15_south_asia_east")]]
    h = pd.concat(hyps, ignore_index=True).set_index("rgi_id")
    bands = [c for c in h.columns if c != "area_km2"]
    H = h.reindex(s.rgi_id)[bands].to_numpy(float) / 1000.0
    ba = np.nansum(H * s.area_km2_glacier_total.to_numpy()[:, None], axis=0)
    bn = np.array([float(b) for b in bands]); m = ba > 0.05
    ghyp = [{"z": int(z), "a": round(float(a), 2)} for z, a in zip(bn[m], ba[m])]

    b = np.arange(2400, 6000, 100)
    lhyp = [{"z": int(z), "n": int(n), "a": round(float(a), 2)} for z, n, a in
            zip(b[:-1], np.histogram(lk.elev_m, bins=b)[0],
                np.histogram(lk.elev_m, bins=b, weights=lk.area_km2)[0]) if n > 0]

    yr = vts.groupby("year").agg(pairs=("img_pairs", "median"),
                                 err=("v_error_m_yr", "median"),
                                 v=("v_mean_m_yr", "median")).reset_index()
    diag = [{"y": int(r.year), "p": round(float(r.pairs), 1),
             "e": round(float(r.err), 2), "v": round(float(r.v), 2)} for r in yr.itertuples()]

    full = lts.groupby("lake_id").year.nunique()
    ids = set(full[full == full.max()].index)
    tt = lts[lts.lake_id.isin(ids)].groupby("year").area_m2.sum() / 1e6
    lann = [{"y": int(y), "a": round(float(a), 2)} for y, a in tt.items()]

    u = lk[lk.change_usable]
    contact = []
    for lab, mm in [("touching ice", u.dist_to_rgi1999_m <= 60),
                    ("within 1 km", (u.dist_to_rgi1999_m > 60) & (u.dist_to_rgi1999_m <= 1000)),
                    ("1\u20135 km", (u.dist_to_rgi1999_m > 1000) & (u.dist_to_rgi1999_m <= 5000)),
                    ("beyond 5 km", u.dist_to_rgi1999_m > 5000)]:
        d = u[mm]
        contact.append({"l": lab, "n": int(len(d)),
                        "e": round(100 * float((d.change_class == "expanding").mean()), 1)})

    pg = s.groupby("province").agg(gn=("rgi_id", "size"),
                                   ga=("area_km2_within_nepal", "sum")).reset_index()
    pl = lk.groupby("province").agg(ln=("lake_id", "size"), la=("area_km2", "sum"),
                                    gf_=("glof_events_recorded", "sum")).reset_index()
    pv = pg.merge(pl, on="province", how="outer").fillna(0).sort_values("ga", ascending=False)
    prov = [{"p": r.province, "gn": int(r.gn), "ga": round(float(r.ga), 1),
             "ln": int(r.ln), "la": round(float(r.la), 2), "gf": int(r.gf_)} for r in pv.itertuples()]

    c = gl[gl.has_contact_lake_1999_geom & gl.velocity_current_usable]
    n_ = gl[(~gl.has_contact_lake_1999_geom) & gl.velocity_current_usable]
    spd = []
    for lo, hi, lab in [(0.5, 1, "0.5\u20131"), (1, 5, "1\u20135"), (5, 50, "5\u201350")]:
        a = c[(c.area_km2_glacier_total >= lo) & (c.area_km2_glacier_total < hi)]
        bb = n_[(n_.area_km2_glacier_total >= lo) & (n_.area_km2_glacier_total < hi)]
        if len(a) >= 5:
            spd.append({"l": lab, "ca": round(float(a.v_mean_2016_2024.median()), 2),
                        "cn": int(len(a)), "na": round(float(bb.v_mean_2016_2024.median()), 2),
                        "nn": int(len(bb))})

    uu = gl[gl.velocity_current_usable & gl.rep_point_in_nepal]
    summary = dict(
        glaciers=int(len(s)), glacier_km2=round(float(s.area_km2_within_nepal.sum()), 1),
        glaciers_all=int(len(gl)), transboundary=int(gl.is_transboundary.sum()),
        v_median=round(float(uu.v_mean_2016_2024.median()), 2),
        v_p90=round(float(uu.v_mean_2016_2024.quantile(.9)), 2),
        v_max=round(float(uu.v_mean_2016_2024.max()), 1), v_usable=int(len(uu)),
        snr_early=qg["median_snr_early_epoch"], snr_late=qg["median_snr_late_epoch"],
        rgi_year_median=qg["rgi_source_year_median"], velocity_last=qg["velocity_year_last"],
        lakes=ql["lakes_total"], lake_km2=ql["lake_area_km2"], lake_z=ql["lake_elev_median_m"],
        lakes_inside_ice=ql["lakes_inside_rgi1999_outline"],
        lakes_inside_km2=ql["lakes_inside_rgi1999_km2"],
        lake_net_pct=ql["net_area_change_pct"], lakes_assessed=ql["lakes_change_assessed"],
        lakes_expanding=ql["lakes_expanding"], lakes_shrinking=ql["lakes_shrinking"],
        glaciers_lake_contact=ql["glaciers_with_contact_lake"],
        lake_ice_km2=ql["glacier_ice_km2_with_contact_lake"],
        glof_events=qg["glof_events_nepal_georeferenced"],
        glacier_years=qg["glacier_year_records"], lake_years=ql["himag_lake_year_records"],
        lakes_typed=ql["lakes_typed_from_himag"])

    payload = dict(summary=summary, ghyp=ghyp, lhyp=lhyp, diag=diag, lann=lann,
                   contact=contact, prov=prov, spd=spd)
    json.dump(payload, open(WEB / "summary.json", "w"), separators=(",", ":"))

    # Also emit the summary as a plain script. A <script src> tag is not subject
    # to the fetch/CORS restrictions that block relative XHR under file:// and
    # inside sandboxed document previews, so every chart, table and headline
    # figure on the page keeps working even where the GeoJSON cannot be loaded.
    with open(WEB / "summary.js", "w") as fh:
        fh.write("window.SUMMARY=" + json.dumps(payload, separators=(",", ":")) + ";\n")

    print(f"  glaciers.geojson {s1/1e6:.2f} MB | lakes.geojson {s2/1e6:.2f} MB | "
          f"glof.geojson {(WEB/'glof.geojson').stat().st_size/1e3:.0f} KB | "
          f"summary.json/.js {(WEB/'summary.json').stat().st_size/1e3:.0f} KB")


if __name__ == "__main__":
    build()
