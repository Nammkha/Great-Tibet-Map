# tools

`build-physical.py` regenerates the rivers, lakes, ranges and peaks that the
widget carries in its `DATA` object, already projected into the 1180x745
viewBox.

The map's projection was never recorded anywhere, so the script recovers it by
fitting the ten labelled towns, then checks the result against the stored
graticule. It reproduces to 0.00-0.11 px in longitude and 0.17-0.58 px in
latitude across 25-40 N, the band Tibet occupies.

Source data is Natural Earth, which is public domain -- the reason the result
can stay under the project's CC0 dedication. The two files are a few megabytes
each and are not committed; fetch them into this directory first:

    B=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
    curl -O $B/ne_10m_rivers_lake_centerlines.geojson
    curl -O $B/ne_10m_lakes.geojson

Then, from the repository root:

    python3 tools/build-physical.py > physical.json

The output is spliced into `var DATA = {...}` in `tibet-three-regions-map.html`.
Range crests and peaks are listed in the script itself rather than taken from
Natural Earth, which ships no range centrelines; they carry the labels and are
not a claim about exact extent.
