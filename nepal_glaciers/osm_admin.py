"""
Administrative boundaries for Nepal, assembled from OpenStreetMap.

Replaces the geoBoundaries ADM1 layer used previously, and adds districts,
which geoBoundaries ADM2 did not cover here.

OSM admin levels in Nepal: 4 = province (7 of them), 6 = district (77).
Overpass returns each boundary as a relation whose member ways are unordered
fragments, so the ways are noded together and polygonized rather than being
concatenated in member order - member order is not guaranteed to be a ring.

Run directly to refresh:  python -m nepal_glaciers.osm_admin
"""
import json

import geopandas as gpd
import requests
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import linemerge, polygonize, unary_union

from .config import RAW, AEA_NEPAL

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "nepal-cryosphere-inventory/1.0 (research)"}
QUERY = """[out:json][timeout:300];
area["ISO3166-1"="NP"][admin_level=2]->.np;
rel(area.np)["boundary"="administrative"]["admin_level"~"^(4|6)$"];
out geom;"""

CACHE = RAW / "osm_admin_nepal.json"


def fetch(force=False):
    if CACHE.exists() and not force:
        return json.load(open(CACHE))
    last = None
    for ep in ENDPOINTS:
        try:
            r = requests.post(ep, data={"data": QUERY}, headers=HEADERS, timeout=400)
            if r.status_code == 200:
                d = r.json()
                RAW.mkdir(parents=True, exist_ok=True)
                json.dump(d, open(CACHE, "w"))
                return d
            last = f"{ep} -> HTTP {r.status_code}"
        except Exception as e:                                   # noqa: BLE001
            last = f"{ep} -> {e!r}"
    raise RuntimeError(f"Overpass unavailable. Last attempt: {last}")


def _polygonise(rel):
    """Node the relation's member ways together and build its polygon."""
    lines = []
    for m in rel.get("members", []):
        if m.get("type") != "way" or "geometry" not in m:
            continue
        if m.get("role") not in ("outer", "inner", "", None):
            continue
        pts = [(p["lon"], p["lat"]) for p in m["geometry"]]
        if len(pts) > 1:
            lines.append(LineString(pts))
    if not lines:
        return None
    merged = linemerge(unary_union(lines))
    polys = [p for p in polygonize(merged) if p.is_valid and not p.is_empty]
    if not polys:
        return None
    # Inner rings come back as separate polygons; keeping the largest
    # disjoint pieces and unioning reconstructs the administrative area.
    geom = unary_union(polys)
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    return geom


def _name(tags):
    """Prefer the English name; fall back to Devanagari, then ref."""
    for k in ("name:en", "int_name", "name", "official_name:en"):
        if tags.get(k):
            return tags[k]
    return tags.get("ref", "unknown")


def build(force=False):
    data = fetch(force=force)
    rows = []
    for rel in data["elements"]:
        if rel.get("type") != "relation":
            continue
        tags = rel.get("tags", {})
        geom = _polygonise(rel)
        if geom is None:
            print(f"  WARNING: could not polygonise relation {rel.get('id')} "
                  f"({_name(tags)})")
            continue
        rows.append({
            "osm_id": rel["id"],
            "admin_level": int(tags.get("admin_level", 0)),
            "name": _name(tags),
            "name_ne": tags.get("name", ""),
            "geometry": geom,
        })

    g = gpd.GeoDataFrame(rows, crs=4326)
    # Small self-intersections are common in OSM boundary data; buffer(0) in an
    # equal-area CRS repairs them without moving the boundary meaningfully.
    inval = ~g.geometry.is_valid
    if inval.any():
        ea = g.to_crs(AEA_NEPAL)
        ea.loc[inval, "geometry"] = ea.loc[inval, "geometry"].buffer(0)
        g = ea.to_crs(4326)
        print(f"  repaired {int(inval.sum())} invalid geometries")

    prov = g[g.admin_level == 4].reset_index(drop=True)
    dist = g[g.admin_level == 6].reset_index(drop=True)
    prov.to_file(RAW / "osm_admin.gpkg", layer="provinces", driver="GPKG")
    dist.to_file(RAW / "osm_admin.gpkg", layer="districts", driver="GPKG")
    print(f"  provinces {len(prov)} | districts {len(dist)}")
    return prov, dist


def assign(points_4326, prov, dist, in_country=None):
    """
    Point-in-polygon province and district for a GeoSeries of points.

    Returns two Series indexed exactly like the input.

    Two things this gets right that the previous implementation did not:

    1. It joins on the index, never by position. A spatial join can emit more
       rows than it was given when a point lands on a shared boundary, and
       assigning those positionally shifts every later value - which is how
       the lake province field came to be scrambled.

    2. Containment is the only rule, with one narrow exception. The national
       outline (geoBoundaries) and the province polygons (OSM) are independent
       datasets and disagree slightly along the border, so a point can be
       inside Nepal by one and outside every province by the other. Pass
       `in_country` (a boolean Series aligned to the points) and those cases
       fall back to the nearest province; everything else stays null. Points
       genuinely outside Nepal are never given a Nepali province, however
       close they sit to the line.
    """
    pts = gpd.GeoDataFrame(geometry=points_4326.values, crs=4326,
                           index=points_4326.index)

    def one(poly, col):
        j = gpd.sjoin(pts, poly[["name", "geometry"]], how="left",
                      predicate="within")
        j = j[~j.index.duplicated(keep="first")]        # shared-boundary ties
        s = j["name"].reindex(pts.index)                # index-aligned, not positional

        if in_country is not None:
            mask = s.isna() & in_country.reindex(pts.index).fillna(False)
            if mask.any():
                n = gpd.sjoin_nearest(pts[mask].to_crs(AEA_NEPAL),
                                      poly[["name", "geometry"]].to_crs(AEA_NEPAL),
                                      how="left")
                n = n[~n.index.duplicated(keep="first")]
                s.loc[mask] = n["name"].reindex(pts[mask].index)
        return s.rename(col)

    return one(prov, "province"), one(dist, "district")


if __name__ == "__main__":
    build(force=False)
