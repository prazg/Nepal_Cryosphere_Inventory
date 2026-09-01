# Source data placed here by hand

Everything else the pipeline needs is downloaded automatically into `raw/`
(gitignored). One file is not.

## HMAGLOFDB — glacial lake outburst flood database

`nepal_glaciers/config.py` looks for `HMAGLOFDB_v*.csv` in this directory, and
takes the highest version number it finds. You can override that:

```bash
export GLOF_CSV=/path/to/HMAGLOFDB_v4_0_13122025.csv
```

If the file is absent the pipeline stops with a message telling you exactly
what it wanted and where to get it, rather than failing obscurely later.

**Source:** Shrestha, F. et al. (2023). *A comprehensive and version-controlled
database of glacial lake outburst floods in High Mountain Asia.* Earth System
Science Data 15, 3941–3961. https://doi.org/10.5194/essd-15-3941-2023 —
distributed by ICIMOD at https://rds.icimod.org

## Before you push this repository publicly

A copy of the CSV may already be sitting in this directory. **Check the
redistribution terms yourself before publishing it.** The ESSD paper is
CC BY 4.0, but I have not verified that the same licence attaches to the
database file as distributed by ICIMOD, and I am not in a position to
give you a licensing opinion.

If you would rather not redistribute it, add this to `.gitignore`:

```
data/source/*.csv
```

The pipeline then works for anyone who downloads the file themselves, and the
instructions above tell them how.
