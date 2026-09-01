"""
Step 2 - attach ITS_LIVE annual velocity to every glacier.

This is the "live" half of the inventory. RGI outlines are frozen; the ITS_LIVE
annual composites are reprocessed and republished, so re-running this step
picks up newly added years without touching step 1.

Method: for each 100 km ITS_LIVE tile, rasterise the glacier polygons onto the
tile's own 120 m UTM grid, then compute per-glacier per-year statistics of the
`v` (mean annual speed) band.
"""
import json, warnings
import numpy as np, pandas as pd, geopandas as gpd, xarray as xr, s3fs
from shapely.geometry import shape
from rasterio.features import rasterize
from rasterio.transform import from_origin
from .config import RAW, BUILD, ITSLIVE_CATALOG, ITSLIVE_BUCKET, EPOCH_EARLY, EPOCH_LATE
from .step1_base import fetch

warnings.filterwarnings("ignore", category=RuntimeWarning)


def load_catalog():
    p = RAW / "itslive_catalog_v02.json"
    fetch(ITSLIVE_CATALOG, p)
    cat = json.load(open(p))
    rows = [dict(geometry=shape(f["geometry"]), **f["properties"])
            for f in cat["features"]]
    return gpd.GeoDataFrame(rows, crs=4326)


def tiles_for(glaciers):
    cat = load_catalog()
    hull = glaciers.union_all()
    sub = cat[cat.intersects(hull) & cat.composite_zarr_url.notna()].copy()
    return sub.reset_index(drop=True)


def open_cube(url):
    fs = s3fs.S3FileSystem(anon=True)
    key = url.split(".amazonaws.com/")[1]
    store = s3fs.S3Map(root=f"{ITSLIVE_BUCKET}/{key}", s3=fs, check=False)
    return xr.open_zarr(store, consolidated=True, chunks={})


def zonal_for_tile(ds, gl_utm):
    """Per-glacier, per-year velocity stats for one cube."""
    x, y = ds.x.values, ds.y.values
    res = float(abs(x[1] - x[0]))
    tf = from_origin(x[0] - res / 2, y[0] + res / 2, res, res)
    shp = (len(y), len(x))

    # index 0 is reserved for background, so glaciers are labelled 1..n
    shapes = [(g, i + 1) for i, g in enumerate(gl_utm.geometry)]
    lab = rasterize(shapes, out_shape=shp, transform=tf, fill=0,
                    dtype="int32", all_touched=True)
    if lab.max() == 0:
        return None

    flat = lab.ravel()
    keep = flat > 0
    lbl = flat[keep]
    nglac = len(gl_utm)

    years = pd.to_datetime(ds.time.values).year
    v = ds.v.values.astype("float32")            # (time, y, x) m/yr
    verr = ds.v_error.values.astype("float32")     # (time, y, x)
    npair = ds["count"].values.astype("float32")   # image pairs used
    v0 = ds.v0.values.astype("float32").ravel()[keep]
    dvdt = ds.dv_dt.values.astype("float32").ravel()[keep]

    recs = []
    npx = np.bincount(lbl, minlength=nglac + 1)[1:]
    for ti, yr in enumerate(years):
        vals = v[ti].ravel()[keep]
        ok = np.isfinite(vals)
        if not ok.any():
            continue
        l_ok, v_ok = lbl[ok], vals[ok]
        cnt = np.bincount(l_ok, minlength=nglac + 1)[1:]
        tot = np.bincount(l_ok, weights=v_ok, minlength=nglac + 1)[1:]
        mx = np.zeros(nglac + 1, "float32")
        np.maximum.at(mx, l_ok, v_ok)
        mx = mx[1:]
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
        m = cnt > 0
        def _mean_of(arr2d):
            aa = arr2d.ravel()[keep][ok]
            good = np.isfinite(aa)
            c2 = np.bincount(l_ok[good], minlength=nglac + 1)[1:]
            s2 = np.bincount(l_ok[good], weights=aa[good], minlength=nglac + 1)[1:]
            with np.errstate(invalid="ignore"):
                return np.where(c2 > 0, s2 / np.maximum(c2, 1), np.nan)

        recs.append(pd.DataFrame({
            "rgi_id": gl_utm.rgi_id.values[m], "year": int(yr),
            "v_mean_m_yr": mean[m], "v_max_m_yr": mx[m],
            "v_error_m_yr": _mean_of(verr[ti])[m],
            "img_pairs": _mean_of(npair[ti])[m],
            "n_valid_px": cnt[m], "n_px_total": npx[m]}))

    ts = pd.concat(recs, ignore_index=True) if recs else None

    # static (time-independent) fields
    def agg(arr):
        ok = np.isfinite(arr)
        c = np.bincount(lbl[ok], minlength=nglac + 1)[1:]
        s = np.bincount(lbl[ok], weights=arr[ok], minlength=nglac + 1)[1:]
        with np.errstate(invalid="ignore"):
            return np.where(c > 0, s / np.maximum(c, 1), np.nan)

    stat = pd.DataFrame({"rgi_id": gl_utm.rgi_id.values,
                         "v0_m_yr": agg(v0), "dv_dt_m_yr2": agg(dvdt),
                         "n_px_total": npx})
    return ts, stat[stat.n_px_total > 0]


def build(glaciers=None):
    if glaciers is None:
        glaciers = gpd.read_file(BUILD / "step1_base.gpkg", layer="glaciers")
    tiles = tiles_for(glaciers)
    print(f"  {len(tiles)} ITS_LIVE composite tiles intersect the inventory")

    cache = BUILD / "tile_cache"; cache.mkdir(exist_ok=True)
    ts_parts, st_parts = [], []
    for i, t in tiles.iterrows():
        sub = glaciers[glaciers.intersects(t.geometry)]
        if sub.empty:
            continue
        ct, cs = cache / f"ts_{i}.parquet", cache / f"st_{i}.parquet"
        if ct.exists() and cs.exists():
            ts_parts.append(pd.read_parquet(ct)); st_parts.append(pd.read_parquet(cs))
            print(f"  [{i+1}/{len(tiles)}] cached", flush=True); continue
        try:
            ds = open_cube(t.composite_zarr_url)
        except Exception as e:
            print(f"  [{i+1}/{len(tiles)}] SKIP (open failed): {repr(e)[:90]}")
            continue
        gl_utm = sub.to_crs(int(t.epsg))
        out = zonal_for_tile(ds, gl_utm)
        ds.close()
        if out is None:
            print(f"  [{i+1}/{len(tiles)}] no glacier pixels")
            continue
        ts, stat = out
        if ts is not None:
            ts.to_parquet(ct, index=False); ts_parts.append(ts)
        stat.to_parquet(cs, index=False); st_parts.append(stat)
        print(f"  [{i+1}/{len(tiles)}] epsg{t.epsg} "
              f"{len(sub):,} glaciers -> {len(stat):,} with pixels", flush=True)

    ts = pd.concat(ts_parts, ignore_index=True)
    stat = pd.concat(st_parts, ignore_index=True)

    # A glacier can straddle tiles: combine by pixel-count weighting.
    ts["w"] = ts.n_valid_px
    g = ts.groupby(["rgi_id", "year"])
    ts = pd.DataFrame({
        "v_mean_m_yr": g.apply(lambda d: np.average(d.v_mean_m_yr, weights=d.w),
                               include_groups=False),
        "v_max_m_yr": g.v_max_m_yr.max(),
        "v_error_m_yr": g.apply(lambda d: np.average(d.v_error_m_yr.fillna(0),
                                weights=d.w), include_groups=False),
        "img_pairs": g.img_pairs.max(),
        "n_valid_px": g.n_valid_px.sum(),
        "n_px_total": g.n_px_total.sum()}).reset_index()

    sg = stat.groupby("rgi_id")
    stat = pd.DataFrame({
        "v0_m_yr": sg.apply(lambda d: np.average(d.v0_m_yr.fillna(0),
                            weights=d.n_px_total), include_groups=False),
        "dv_dt_m_yr2": sg.apply(lambda d: np.average(d.dv_dt_m_yr2.fillna(0),
                                weights=d.n_px_total), include_groups=False),
        "n_px_total": sg.n_px_total.sum()}).reset_index()

    # Epoch means and change.
    def epoch(a, b, name):
        w = ts[(ts.year >= a) & (ts.year <= b)].groupby("rgi_id")
        return pd.DataFrame({name: w.v_mean_m_yr.mean(),
                             name + "_err": w.v_error_m_yr.mean(),
                             name + "_pairs": w.img_pairs.median()})
    e0 = epoch(*EPOCH_EARLY, f"v_mean_{EPOCH_EARLY[0]}_{EPOCH_EARLY[1]}")
    e1 = epoch(*EPOCH_LATE, f"v_mean_{EPOCH_LATE[0]}_{EPOCH_LATE[1]}")
    summ = stat.set_index("rgi_id").join([e0, e1])
    a0, b0 = e0.columns[0], e1.columns[0]
    a, b = a0, b0
    summ["v_change_m_yr"] = summ[b] - summ[a]
    summ["v_change_pct"] = 100 * summ.v_change_m_yr / summ[a].replace(0, np.nan)
    # Signal-to-noise: ITS_LIVE speed is positive-definite, so random error
    # biases v UPWARD. Any epoch comparison is meaningless unless v >> v_error
    # in both epochs. Early years have few image pairs and large errors.
    summ["snr_early"] = summ[a] / summ[a + "_err"].replace(0, np.nan)
    summ["snr_late"] = summ[b] / summ[b + "_err"].replace(0, np.nan)
    summ["v_years_observed"] = ts[ts.n_valid_px > 0].groupby("rgi_id").year.nunique()
    summ["v_year_last"] = ts[ts.n_valid_px > 0].groupby("rgi_id").year.max()
    summ = summ.reset_index()

    ts.to_parquet(BUILD / "step2_velocity_annual.parquet", index=False)
    summ.to_parquet(BUILD / "step2_velocity_summary.parquet", index=False)
    print(f"  -> {summ.rgi_id.nunique():,} glaciers with velocity | "
          f"{len(ts):,} glacier-year records | "
          f"years {ts.year.min()}-{ts.year.max()}")
    return ts, summ


if __name__ == "__main__":
    build()
