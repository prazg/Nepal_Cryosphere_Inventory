# Nepal Cryosphere Inventory

An open, rebuildable inventory of **4,480 glaciers** (4,215 km² of ice) and **1,429 glacial lakes** (81.04 km²) in Nepal, with annual ice surface velocity to 2025 and every georeferenced outburst flood on record.

**[→ Open the interactive map](https://prazg.github.io/Nepal_Cryosphere_Inventory/)**

The link goes live once Pages is enabled — see [Deploying](#deploying).

---

## What this adds to the source data

The sources are all public. Three things here are not.

**A lake-terminating flag.** RGI 7.0 records `term_type = 9` — unassigned — for *every* glacier in region 15, so it cannot tell you which Nepali glaciers end in water. Matching mapped lakes back to glacier outlines supplies that flag: **201 glaciers**, holding 886 km² of ice, have a lake at their mapped margin.

**A clipped, transboundary-aware national inventory.** Nepal straddles the RGI region 14/15 boundary, so fetching only region 15 — the obvious choice — silently drops 34 glaciers in the far west. Areas are computed in an equal-area projection and split into whole-glacier and inside-Nepal figures, so the 358 transboundary glaciers do not quietly inflate the national total.

**Explicit quality gates.** Every derived number carries a flag saying whether it can be trusted. One of them says no for the entire dataset. See [What this data cannot tell you](#what-this-data-cannot-tell-you).

## Headline numbers

| | |
|---|---|
| Glaciers, representative point in Nepal | 4,480 |
| Glaciers intersecting the border | 4,679 |
| Ice area inside Nepal, strict subset | 4,215.4 km² |
| Ice area inside Nepal, all intersecting glaciers | 4,266.9 km² |
| Median surface speed, 2016–2024 | 1.79 m/yr |
| Glacial lakes, 2022 | 1,429 (81.04 km²) |
| Median lake elevation | 4,923 m |
| Net lake area change, 2016–17 → 2022–24 | +5.1% |
| Glaciers with a lake at the margin | 201 |
| Georeferenced outburst floods | 58 |
| Glacier-year velocity records | 172,905 |

## Findings you can rely on

- **Lakes touching ice are the ones growing.** 32.9% of ice-contact lakes expanded between 2016–17 and 2022–24, against 8.9% of detached lakes. The gradient is monotonic with distance to ice.
- **Ice contact was overstated by half.** 260 lakes touch the 1999 RGI margin; only 130 touch ICIMOD's 2020 margin. 143 have been left behind by a retreating terminus. Hi-MAG independently classifies 98 of them as proglacial and only 16 as supraglacial, so these are lakes filling ground the terminus has vacated, not ponds on the ice surface.
- **Nepal's glaciers are slow.** Median 2016–2024 speed 1.79 m/yr, 90th percentile 4.87, fastest 40.1.
- Ice area peaks between 5,000 and 6,200 m; lakes cluster about a thousand metres lower.
- Ice is concentrated in a handful of the 77 districts: Manang (487 km²), Taplejung (430), Solukhumbu (426) and Dolpa (379) hold about 40% of it.

The net lake change of +5.1% sits close to the +5.5% the source study reports for all of High Mountain Asia. That agreement checks the clipping and matching in this build — it is not independent confirmation of the change itself.

## What this data cannot tell you

**There is no usable ice-velocity trend here.** A naive comparison of 2000–2009 against 2016–2024 gives a median 46% slowdown with 96% of glaciers slowing. It is an artefact.

Speed is `hypot(vx, vy)`, so it cannot go below zero and random error biases it *upward*. Early years rest on tens of image pairs with errors of 2–18 m/yr; recent years on thousands with errors rounding to zero. Median signal-to-noise across Nepal is **1.59** in the 2000s against **12.08** today — the older velocities sit at the noise floor. Screening on early signal-to-noise makes it worse: it selects the glaciers noise inflated, and regression to the mean reproduces the same slowdown at n=214.

`velocity_change_interpretable` is `False` for every record. The epoch fields are kept only so the artefact stays auditable. This is a statement about *this dataset processed this way*, not about Himalayan glaciers; published work on High Mountain Asia velocity trends has not been verified here.

**This is not a hazard ranking.** There is no danger or PDGL score, deliberately. Outburst likelihood needs moraine dam geometry, freeboard, ice content in the dam, slope stability above the lake, and downstream exposure — none of which is in these sources. The inventory supplies the objective ingredients and stops. A composite index built only from area, growth and ice contact would look authoritative and carry very little.

**Lakes do not measurably speed up their glaciers here.** Raw medians suggest contact-lake glaciers flow faster (2.11 vs 1.81 m/yr), but that reverses under size matching (1–5 km²: 2.15 vs 2.67; 5–50 km²: 5.75 vs 7.04) because lake-contact glaciers are systematically larger. Absence of evidence on small samples, not evidence of absence.

## Limitations that govern everything

**Ice contact is now judged against 2020, velocity still against 1999.** ICIMOD's 2020 outlines fixed the contact problem: use `ice_contact_2020`, not `dist_to_rgi1999_m`. But the velocity extraction is still keyed to RGI geometry, so 2016–2024 speed sampled inside a ~1999 outline includes ground that has since deglaciated, and glacier-wide means remain biased low. Re-running the velocity step against ICIMOD 2020 would fix that; it has not been done.

**Do not difference RGI and ICIMOD to get glacier change.** The apparent 16.5% area loss is not a measurement. Only 1.1 km² of RGI's Nepal ice falls below ICIMOD's 0.02 km² threshold, so that is not the explanation — but the two inventories disagree in both directions: 1,009 km² of RGI ice is absent from ICIMOD, and 1,388 km² of ICIMOD ice is absent from RGI, more than the apparent loss itself. Only 76% of RGI's ice is mapped as ice by both. A defensible figure needs ICIMOD's own 1990/2000/2010 layers, which exist in the same publication but are not included here.

**Two definitions of "in Nepal".** 4,679 glaciers intersect the border; 4,480 have their representative point inside it. Headline figures use the second. Filter on `rep_point_in_nepal` or `frac_within_nepal` as your work requires.

**The border is contested.** Kalapani–Limpiyadhura in the northwest is disputed between Nepal and India. This build follows geoBoundaries gbOpen ADM0 (commit 9469f09).

**Small lakes are under-counted.** The lake source reports detection near 96% for lakes of 20,000–100,000 m² and 100% above that, but roughly 25% below 5,400 m². Small lakes have caused destructive floods.

**GLOF linkage is proximity, not causation.** Nearest feature within 3 km of the reported lake coordinate. Verify individual matches.

## Sources

| Source | Role | Period | Updates? | Licence |
|---|---|---|---|---|
| [ITS_LIVE](https://nsidc.org/apps/itslive/) annual composites | Ice surface velocity | 1987–2025 | **Yes** | — |
| [Kumar & Vijay (2026)](https://doi.org/10.5281/zenodo.17948783) | Lake extents, change pair | 2022; 2016–17 vs 2022–24 | Method is re-runnable | CC BY 4.0 |
| [Hi-MAG, Chen et al. (2021)](https://zenodo.org/record/4275164) | Lake **type**, annual areas | 2008–2017 | No | CC BY 4.0 |
| HMAGLOFDB v4 | Outburst floods | to 2025 | Yes, annual | — |
| geoBoundaries gbOpen NPL | National outline | — | — | CC BY 4.0 |
| [OpenStreetMap](https://www.openstreetmap.org/) `admin_level` 4 and 6 | Provinces (7) and districts (77) | live | Yes | ODbL |

Two things worth knowing about access. **The NSIDC path for RGI 7.0 returns HTTP 401 without Earthdata credentials**, so the pipeline pulls the identical release archives from the RGI/OGGM mirror at Universität Bremen; NSIDC-0770 remains the citation. And **the ITS_LIVE v2/v2.1 regional velocity mosaics do not exist for RGI region 15** — they cover regions 01–12, 14 and 17–19 only. Nepal is almost entirely region 15, so this build uses the per-tile annual composites, which do cover it. Both traps are documented in `nepal_glaciers/config.py`.

**ICIMOD is the obvious missing source.** Their 2015 glacial lakes for the Koshi, Gandaki and Karnali basins (DOI 10.26066/RDS.1971946) would be the authoritative Nepal-specific inventory. Their GeoNetwork API exposes only images publicly; the shapefile sits behind a download flow this pipeline cannot complete. If you can obtain it, substituting it in is the single highest-value improvement to this repository.

## Repository layout

```
.
├── docs/                    GitHub Pages root
│   ├── index.html           combined interactive map + charts
│   ├── glaciers.html        glacier-only summary page
│   ├── lakes.html           lake-only summary page
│   ├── data/                simplified GeoJSON for the map (3.2 MB)
│   │                        plus summary.js, which the page loads without fetch
│   └── vendor/leaflet/      Leaflet, vendored (BSD-2-Clause)
├── data/                    full-resolution outputs — 25 MB total
│   ├── nepal_glacier_inventory.gpkg          13.1 MB  glaciers, glof_events, provinces
│   ├── nepal_glacial_lake_inventory.gpkg      9.3 MB  lakes
│   ├── nepal_glacier_velocity_annual.parquet  3.2 MB  172,905 glacier-years
│   ├── nepal_lake_area_annual_himag.parquet   0.1 MB  6,724 lake-years
│   └── source/                                HMAGLOFDB goes here
├── nepal_glaciers/          the pipeline
│   ├── config.py            every verified endpoint and constant
│   ├── osm_admin.py         OSM province and district boundaries, point-in-polygon
│   ├── step1_base.py        RGI 7.0 → Nepal base inventory
│   ├── step2_velocity.py    ITS_LIVE annual velocity (resumable, per-tile cache)
│   ├── step3_export.py      GLOF linkage, QC, glacier export
│   ├── step4_lakes.py       lake inventory + lake-terminating flag
│   └── step5_web.py         simplified web layers for docs/
├── .github/workflows/       Pages deploy + data-consistency checks
├── DATA_DICTIONARY.md       every field in every file
├── CONTRIBUTING.md
├── CHANGELOG.md
├── Makefile
├── pyproject.toml
├── requirements.txt
├── setup-github.sh          prepares the repo for its first push
├── CITATION.cff
└── LICENSE                  CC BY 4.0
```

`raw/` and `build/` are gitignored — both are fully regenerable.

## Rebuilding

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all          # ~25 minutes, mostly network
```

Step 2 downloads roughly 1.6 GB of ITS_LIVE cubes and caches per tile in `build/tile_cache/`, so an interrupted run resumes where it stopped. Delete the cache to force a full refetch.

To pick up new ITS_LIVE years or a new HMAGLOFDB release without refetching RGI:

```bash
make refresh      # velocity → export → lakes → web
```

## Deploying

The site is static — nothing is compiled. A helper prepares the repository and then hands control back to you:

```bash
./setup-github.sh prazg Nepal_Cryosphere_Inventory
```

Links throughout this repository already point at `prazg/Nepal_Cryosphere_Inventory`, so the script's substitution step is a no-op here; it still warns about oversized files, runs `git init`, stages everything, and stops. It does not push: that needs your credentials, and those should not go through a script you did not write. It prints the three commands to run yourself.

Then in the repository: **Settings → Pages → Source: GitHub Actions.** The included `deploy-pages.yml` workflow publishes `docs/` on every push that touches it. If you would rather avoid Actions, delete that workflow and choose **Deploy from a branch → `main` → `/docs`** instead; both work, and `.nojekyll` is already in place so Jekyll leaves the data directory alone.

A second workflow, `validate.yml`, runs on every push and pull request. It does not rebuild the inventory — that needs about 1.6 GB of downloads — but it checks that the committed web layers agree with `summary.json`, that required attributes are present on every feature, that the dashboard JavaScript parses, and that every local asset `index.html` references actually exists. Those are the things that break in practice.

**Two directories are called `data`, and the difference matters.** `docs/data/` (3.2 MB) is what the website reads — **it must be pushed or the map has nothing to draw.** `data/` at the repository root holds the full-resolution analysis files and the site never touches it. Omitting the root `data/` is a reasonable choice; omitting `docs/data/` breaks the map.

**On size.** `data/` is 25 MB and the whole repository about 30 MB, which git handles without complaint. The largest single file is 13.1 MB, so GitHub's browser uploader would also accept it — but that uploader caps how many files you can add at once, and this is 40 files across nested directories, so `git push` from the command line is far more reliable.

If you would rather keep the repository minimal, uncomment `data/*.gpkg` in `.gitignore` and run `make release` to bundle `data/` as a single Release asset. The repository then drops to about 5 MB. **The website is unaffected either way** — it reads `docs/data/`, never `data/`.

Only one copy of each dataset is versioned, as GeoPackage. CSV and GeoParquet are derivatives; `make formats` regenerates both in seconds. Storing all three tripled `data/` for no information.

**Before you push, check one more thing:** the map loads basemap tiles from Esri, OpenTopoMap and OpenStreetMap. These are third-party services with their own usage policies and no service guarantee to this project. For anything beyond light use, swap in your own tile source in `BASES` near the top of the `<script>` block in `docs/index.html`.

Third, `data/source/` may contain a copy of HMAGLOFDB. **Confirm its redistribution terms before publishing.** The ESSD paper describing it is CC BY 4.0, but I have not verified that the same licence attaches to the database file as ICIMOD distributes it, and this is not a licensing opinion. If in doubt, add `data/source/*.csv` to `.gitignore`; `data/source/README.md` tells anyone cloning where to get it.

To preview locally before pushing:

```bash
make serve        # then open http://localhost:8000
```

**Opening `docs/index.html` on its own will not show the map.** The GeoJSON layers have to be fetched, and browsers block `fetch` on `file://` URLs; the same applies inside document previews that isolate a single file. The page detects this and says so in the map area. The charts, tables and headline figures are unaffected — they come from `data/summary.js`, which loads through a `<script>` tag and is not subject to those restrictions. If the geometry cannot be found locally the page also tries the published site before giving up, so a stray copy of `index.html` still works once Pages is live.

**On the map library.** The map uses **Leaflet**, vendored into `docs/vendor/leaflet/`, deliberately rather than a WebGL library. WebGL map libraries such as MapLibre GL spawn a Web Worker from a `blob:` URL, and several sandboxed environments — including some in-app document previews — refuse that with `SecurityError: Failed to construct 'Worker'`. Leaflet uses no workers, so the map runs anywhere the page itself runs. It is also 145 KB against 803 KB.

Vendoring means no CDN dependency: the map works offline and under a strict content-security policy. If the local copy is missing the page falls back to unpkg then jsDelivr. If all sources fail, the map area explains why and **the rest of the page still works** — the charts, tables and figures come from `data/summary.json` and never touch the map.

Glaciers and lakes are drawn with Leaflet's canvas renderer; SVG cannot handle 6,100 polygons. Filtering restyles paths in place rather than rebuilding layers, and slider events are coalesced to one pass per animation frame.

## Field reference

Every field in every published file is documented in [DATA_DICTIONARY.md](DATA_DICTIONARY.md), including which quality flag governs it.

## Citation

Cite this inventory *and*, separately, every upstream dataset. See `CITATION.cff`. This is a derived work and is not endorsed by any of the source projects.

## Licence

Code and derived data CC BY 4.0. Upstream sources keep their own terms — see `LICENSE`.
