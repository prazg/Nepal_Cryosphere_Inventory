"""
Configuration for the Nepal live glacier inventory.

Every URL in this file was verified reachable on 2026-09-01 from this machine.
If a build fails, re-run `python -m nepal_glaciers.check_sources` before debugging code.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
BUILD = ROOT / "build"
OUT = Path(os.environ.get("NEPAL_OUT", ROOT / "data"))
for d in (RAW, BUILD):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- RGI 7.0 ---
# Canonical citation/landing page (requires Earthdata login for direct download):
#   https://nsidc.org/data/nsidc-0770/versions/7
# The NSIDC DAAC path returns HTTP 401 without credentials, so this pipeline
# pulls the identical RGI 7.0 release archives from the RGI/OGGM working mirror
# at the University of Bremen. Same files, no auth. Checked 2026-09-01.
RGI_MIRROR = ("https://cluster.klima.uni-bremen.de/~fmaussion/misc/"
              "rgi7_data/l6_rgi7b2_zip/RGI2000-v7.0-G-global")
# Nepal (80.06-88.20E) straddles the RGI first-order region 14/15 boundary,
# so BOTH regions must be fetched. Region 14 contributes a small number of
# glaciers in far-western Nepal. Do not drop it.
RGI_REGIONS = {
    14: "RGI2000-v7.0-G-14_south_asia_west",
    15: "RGI2000-v7.0-G-15_south_asia_east",
}

# ------------------------------------------------------------- Boundaries ---
# geoBoundaries gbOpen, ADM0/ADM1. Open licence, pinned to commit 9469f09.
# NOTE: Nepal's northwestern boundary (Kalapani / Limpiyadhura) is disputed
# between Nepal and India. gbOpen ADM0 follows one interpretation. Glaciers in
# that sliver may be included or excluded depending on the boundary you use.
GB_COMMIT = "9469f09"
GB = ("https://github.com/wmgeolab/geoBoundaries/raw/"
      f"{GB_COMMIT}/releaseData/gbOpen/NPL")
BOUNDARIES = {"adm0": f"{GB}/ADM0/geoBoundaries-NPL-ADM0.geojson",
              "adm1": f"{GB}/ADM1/geoBoundaries-NPL-ADM1.geojson"}

# --------------------------------------------------------------- ITS_LIVE ---
# Global datacube catalogue. Each feature carries both an image-pair
# `zarr_url` and an annual-composite `composite_zarr_url`.
ITSLIVE_CATALOG = "https://its-live-data.s3.amazonaws.com/datacubes/catalog_v02.json"
ITSLIVE_BUCKET = "its-live-data"
# IMPORTANT COVERAGE NOTE, verified by listing the bucket on 2026-09-01:
# the ITS_LIVE v2/v2.1 *regional velocity mosaics* exist for RGI regions
# 01-12, 14, 17-19 but NOT for 13, 15 or 16. Nepal is almost entirely RGI 15,
# so those mosaics cannot be used here. The per-tile annual composites used
# below DO cover Nepal. This is the single most common way to get this wrong.

# -------------------------------------------------------------- Projection --
# Albers equal-area centred on Nepal. Used for every area computation so that
# km2 figures are not latitude-distorted.
AEA_NEPAL = ("+proj=aea +lat_1=27 +lat_2=30 +lat_0=28.5 +lon_0=84 "
             "+datum=WGS84 +units=m +no_defs")

# ------------------------------------------------------------------- GLOF ---
# HMAGLOFDB - Shrestha et al. (2023), doi:10.5194/essd-15-3941-2023.
# Not redistributed by this repository by default; see data/source/README.md.
# Place the CSV in data/source/ or point GLOF_CSV at it:
#     export GLOF_CSV=/path/to/HMAGLOFDB_v4_0_13122025.csv
SOURCE = ROOT / "data" / "source"
GLOF_ENCODING = "cp1252"


def glof_csv() -> Path:
    """Locate the GLOF database, or explain clearly how to obtain it."""
    env = os.environ.get("GLOF_CSV")
    if env:
        p = Path(env)
        if p.exists():
            return p
        raise FileNotFoundError(f"GLOF_CSV is set to {p}, which does not exist.")
    hits = sorted(SOURCE.glob("HMAGLOFDB_v*.csv"))
    if hits:
        return hits[-1]          # highest version present
    raise FileNotFoundError(
        "HMAGLOFDB not found.\n"
        f"  Expected a file matching HMAGLOFDB_v*.csv in {SOURCE}\n"
        "  or the GLOF_CSV environment variable pointing at one.\n"
        "  Source: Shrestha et al. (2023), doi:10.5194/essd-15-3941-2023\n"
        "  See data/source/README.md for where to download it.")


# Backwards-compatible module-level name; resolved lazily so that importing
# config does not fail on a fresh clone that has not fetched the GLOF file yet.
class _LazyGlof:
    def __fspath__(self):
        return str(glof_csv())

    def __str__(self):
        return str(glof_csv())


GLOF_CSV = _LazyGlof()

# Epochs for the velocity-change metric.
EPOCH_EARLY = (2000, 2009)
EPOCH_LATE = (2016, 2024)   # 2025 excluded: partial year, image-pair count drops ~5x
