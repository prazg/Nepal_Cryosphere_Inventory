"""
Optional format conversion.

The repository versions ONE copy of each dataset, as GeoPackage. GeoPackage is
the choice because it opens directly in QGIS and ArcGIS with no tooling, and
geopandas reads it fine.

CSV and GeoParquet are pure derivatives. Versioning them tripled the size of
data/ for no information: the same two tables were stored three times over,
26.2 MB for 4,679 glaciers and 14.2 MB for 1,429 lakes. They are regenerated
here in a few seconds instead:

    python -m nepal_glaciers.formats        # or: make formats

Generated files are gitignored.
"""
import sqlite3
import geopandas as gpd
from shapely import set_precision
from .config import OUT

# Coordinate grid applied to published geometry. 1e-5 degrees is about 1.1 m -
# roughly thirty times finer than the 30 m imagery the outlines derive from, so
# it is lossless in any sense that matters, and it removes float64 noise digits
# that compress badly. Measured effect on total area: under 0.001%.
GRID_DEG = 1e-5

DATASETS = {
    "nepal_glacier_inventory": "glaciers",
    "nepal_glacial_lake_inventory": "lakes",
}


def grid(gdf):
    """Snap coordinates to GRID_DEG and drop any Z dimension."""
    out = gdf.copy()
    out["geometry"] = set_precision(out.geometry.values, GRID_DEG)
    return out


def vacuum(path):
    con = sqlite3.connect(path)
    con.execute("VACUUM")
    con.close()


def build():
    for stem, layer in DATASETS.items():
        src = OUT / f"{stem}.gpkg"
        if not src.exists():
            print(f"  skip {stem}: {src} not found, run the pipeline first")
            continue
        g = gpd.read_file(src, layer=layer)
        g.to_parquet(OUT / f"{stem}.parquet", compression="zstd")
        g.drop(columns="geometry").to_csv(OUT / f"{stem}.csv", index=False)
        print(f"  {stem}: {len(g):,} features -> .parquet + .csv")
    print("  (both are gitignored; the GeoPackage is the versioned copy)")


if __name__ == "__main__":
    build()
