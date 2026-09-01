# Changelog

## 1.0.0 — 2026-09-01

First release.

### Added
- Glacier inventory: 4,480 glaciers with their representative point in Nepal,
  4,215.4 km² of ice, clipped from RGI 7.0 regions 14 and 15 with
  transboundary-aware equal-area figures.
- Annual ITS_LIVE surface velocity, 1987–2025, 172,905 glacier-year records.
- Glacial lake inventory: 1,429 lakes, 81.04 km², for 2022, with lake type from
  Hi-MAG and a 2016–17 vs 2022–24 change pair.
- Lake-terminating flag for 201 glaciers — the attribute RGI 7.0 leaves
  unassigned (`term_type = 9`) for every glacier in region 15.
- Outburst flood linkage from HMAGLOFDB v4.
- Interactive dashboard and two standalone summary pages.
- Reproducible five-step pipeline with per-tile caching.

### Deliberately excluded
- **Any velocity trend.** A naive 2000s vs 2016–2024 comparison gives a median
  46% slowdown across 96% of glaciers. It tracks the collapse in ITS_LIVE
  measurement error, not glacier dynamics: median signal-to-noise is 1.59 in
  the 2000s against 12.08 today, and speed is positive-definite so noise biases
  it upward. `velocity_change_interpretable` is False for every record.
- **Any hazard or danger ranking.** The inputs required are not in these
  sources. See CONTRIBUTING.md.

### Known limitations
- RGI outlines date from a median of 1999 while lakes are 2022, so ice-contact
  judgements overstate contact for retreating glaciers.
- Small lakes are under-counted: the source reports ~25% detection below
  5,400 m² against ~96% for 20,000–100,000 m².
- The Kalapani–Limpiyadhura boundary is disputed; this build follows
  geoBoundaries gbOpen ADM0.
- ICIMOD's Nepal-specific lake inventory could not be obtained.
