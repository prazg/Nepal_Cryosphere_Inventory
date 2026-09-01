.PHONY: all base velocity export lakes web serve clean
all: base velocity export lakes web

base:      ; python -m nepal_glaciers.step1_base
velocity:  ; python -m nepal_glaciers.step2_velocity
export:    ; python -m nepal_glaciers.step3_export
lakes:     ; python -m nepal_glaciers.step4_lakes
web:       ; python -m nepal_glaciers.step5_web

# Refresh only the layers that actually change upstream.
refresh: velocity export lakes web

serve:     ; cd docs && python -m http.server 8000

clean:     ; rm -rf build/ docs/data/*.geojson docs/data/summary.json
