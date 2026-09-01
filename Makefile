.PHONY: all base velocity export lakes web formats serve release clean
all: base velocity export lakes web

base:      ; python -m nepal_glaciers.step1_base
velocity:  ; python -m nepal_glaciers.step2_velocity
export:    ; python -m nepal_glaciers.step3_export
lakes:     ; python -m nepal_glaciers.step4_lakes
web:       ; python -m nepal_glaciers.step5_web

# Refresh only the layers that actually change upstream.
refresh: velocity export lakes web

# CSV and GeoParquet copies of the two inventories. Not versioned - the
# GeoPackage is the canonical copy and these regenerate in seconds.
formats:   ; python -m nepal_glaciers.formats

# Bundle data/ as a single asset to attach to a GitHub Release, for anyone who
# would rather keep the repository itself small.
release:
	@cd data && zip -qr ../nepal-cryosphere-data-v1.0.0.zip . -x 'source/*'
	@ls -lh nepal-cryosphere-data-v1.0.0.zip

serve:     ; cd docs && python -m http.server 8000

clean:     ; rm -rf build/ docs/data/*.geojson docs/data/summary.js* docs/data/summary.json
