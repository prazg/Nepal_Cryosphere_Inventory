# Contributing

## The most useful thing you could add

**The ICIMOD glacial lake inventory.** ICIMOD's 2015 lakes for the Koshi,
Gandaki and Karnali basins (doi:10.26066/RDS.1971946) are the authoritative
Nepal-specific dataset. Their GeoNetwork API exposes only images publicly and
the shapefile sits behind a download flow this pipeline cannot complete. If you
can obtain it, adding it as a third lake source — or substituting it for
Kumar & Vijay — is the single highest-value improvement here.

Two others worth doing:

- **Current glacier outlines.** Almost every caveat in this repository traces
  back to RGI 7.0's Nepal outlines dating from a median of 1999. A 2020s
  outline set would let `dist_to_rgi1999_m` become a real ice-contact distance
  and would remove the low bias in glacier-wide velocity means.
- **Seasonal lake extents.** The current data is one summer maximum per period.
  Supraglacial ponds that fill and drain within a season are invisible.

## Ground rules for changes

**Every number needs a quality flag.** If a derived field can be wrong under
some conditions, ship the field *and* a boolean saying when to trust it. See
`velocity_current_usable` and `change_usable` for the pattern.

**Do not add a hazard or danger score.** This is deliberate, not an oversight.
Outburst likelihood needs moraine dam geometry, freeboard, ice content in the
dam, slope stability above the lake, and downstream exposure. None of that is
in these sources. A composite index built from area, growth and ice contact
would look authoritative and carry very little, and people make decisions from
numbers that look authoritative.

**Verify endpoints before writing code against them.** Two of the traps
documented in `config.py` — the NSIDC 401, and ITS_LIVE having no velocity
mosaic for RGI region 15 — were found by probing, not by reading docs.

**Check for confounding before reporting a difference between groups.** Two
apparent findings in this project reversed or dissolved under scrutiny: the
glacier slowdown (a decline in measurement noise, not dynamics) and
lake-terminating glaciers flowing faster (glacier size, not lakes). Both looked
convincing first time.

## Rebuilding

```bash
pip install -r requirements.txt
make all        # ~25 minutes, mostly network
make refresh    # velocity, export, lakes and web only
make serve      # preview the site at localhost:8000
```

Step 2 caches per ITS_LIVE tile in `build/tile_cache/`, so an interrupted run
resumes. Delete the cache to force a refetch.

## After changing the pipeline

Run `make web` so `docs/data/` matches `data/`. The `validate` workflow checks
that the web layers and `summary.json` agree with each other, and it will fail
the build if they drift.
