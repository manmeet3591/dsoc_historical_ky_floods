import os
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from folium import GeoJson, GeoJsonTooltip, LayerControl

# Optional: load external YAML if present
try:
    import yaml  # pyyaml
except Exception:
    yaml = None

# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Kentucky Historical Flood StoryMap",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Built-in Kentucky flood events data (edit/extend via data/events.yaml)
# Geometry is rough and intended for visualization; replace with authoritative
# polygons as you curate your collection.
# -----------------------------------------------------------------------------
BUILTIN_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "1937_ohio_river_flood",
        "name": "1937 Ohio River Flood",
        "year": 1937,
        "dates": "Jan 9 – Feb 5, 1937",
        "summary": (
            "Historic Ohio River basin flood impacting Louisville, Paducah, "
            "and many communities along the river. Record crests in multiple locations."
        ),
        "deaths": 385,           # Replace with your sourced value if different
        "damages_usd_bil": 8.7,  # 2024$ est. (placeholder) — update per your sources
        "counties": ["Jefferson", "McCracken", "Daviess", "Campbell", "Kenton", "Henderson"],
        # Rough envelope polygon along the Ohio corridor in KY (lon, lat)
        "geojson": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"event": "1937 Ohio River Flood"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-89.0, 37.2], [-88.3, 37.1], [-87.7, 37.3], [-86.3, 37.7],
                        [-85.7, 38.0], [-85.0, 38.7], [-84.6, 38.9], [-84.4, 39.0],
                        [-83.9, 38.8], [-84.6, 38.2], [-85.4, 37.9], [-86.8, 37.4],
                        [-87.5, 37.1], [-88.8, 36.9], [-89.0, 37.2]
                    ]]
                }
            }]
        },
        "markers": [
            {"name": "Louisville", "lat": 38.2527, "lon": -85.7585},
            {"name": "Paducah", "lat": 37.0834, "lon": -88.6000},
            {"name": "Owensboro", "lat": 37.7742, "lon": -87.1133},
        ],
        "river_crests": [
            # Replace values with sourced crests; these are illustrative
            {"gage": "Louisville, OH (McAlpine)", "crest_ft": 52.0, "date": "1937-01-27"},
            {"gage": "Paducah, OH", "crest_ft": 60.8, "date": "1937-02-02"},
            {"gage": "Cincinnati, OH", "crest_ft": 79.99, "date": "1937-01-26"},
        ],
        "photos": [
            {
                "title": "Downtown Louisville under water",
                "url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Louisville_flood_1937.jpg",
                "credit": "Wikimedia Commons"
            },
            {
                "title": "Sandbagging efforts",
                "url": "https://upload.wikimedia.org/wikipedia/commons/3/39/Ohio_River_Flood_1937_Louisville.jpg",
                "credit": "Wikimedia Commons"
            },
        ],
        "resources": [
            {"label": "NOAA/NWS event summary (external)", "url": "https://www.weather.gov/lmk/1937flood"},
        ],
    },
    {
        "id": "1978_louisville_flash_flood",
        "name": "1978 Louisville Flash Flood",
        "year": 1978,
        "dates": "May 19–20, 1978",
        "summary": (
            "Torrential thunderstorms produced extreme short-duration rainfall in the Louisville metro, "
            "triggering damaging flash flooding."
        ),
        "deaths": 5,            # placeholder
        "damages_usd_bil": 0.2, # placeholder
        "counties": ["Jefferson", "Oldham", "Bullitt"],
        "geojson": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"event": "1978 Louisville Flash Flood"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-86.1, 38.4], [-85.9, 38.4], [-85.5, 38.4], [-85.3, 38.2],
                        [-85.5, 38.0], [-85.9, 37.9], [-86.2, 38.0], [-86.1, 38.4]
                    ]]
                }
            }]
        },
        "markers": [
            {"name": "Louisville", "lat": 38.2527, "lon": -85.7585},
        ],
        "river_crests": [
            {"gage": "Beargrass Creek (local)", "crest_ft": None, "date": "1978-05-20"},
        ],
        "photos": [
            {
                "title": "Urban flooding, Louisville 1978",
                "url": "https://upload.wikimedia.org/wikipedia/commons/5/57/Flash_flood_generic.jpg",
                "credit": "Example / Replace with KY archival photo"
            }
        ],
        "resources": [],
    },
    {
        "id": "2021_winter_floods",
        "name": "February 2021 Kentucky Floods",
        "year": 2021,
        "dates": "Feb 26 – Mar 5, 2021",
        "summary": (
            "Prolonged late-winter rainfall and snowmelt led to widespread river and flash flooding, "
            "especially across eastern and south-central Kentucky."
        ),
        "deaths": 3,             # placeholder
        "damages_usd_bil": 0.1,  # placeholder
        "counties": ["Breathitt", "Floyd", "Pike", "Madison", "Estill", "Jackson"],
        "geojson": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"event": "February 2021 KY Floods"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-84.6, 38.2], [-83.0, 38.3], [-82.2, 37.6], [-82.5, 37.1],
                        [-83.2, 37.0], [-84.0, 37.4], [-84.6, 38.2]
                    ]]
                }
            }]
        },
        "markers": [
            {"name": "Jackson", "lat": 37.5534, "lon": -83.3830},
            {"name": "Prestonsburg", "lat": 37.6698, "lon": -82.7749},
        ],
        "river_crests": [
            {"gage": "North Fork KY River at Jackson", "crest_ft": 43.5, "date": "2021-03-01"},  # placeholder
            {"gage": "Red River at Clay City", "crest_ft": 25.8, "date": "2021-03-01"},          # placeholder
        ],
        "photos": [
            {
                "title": "Eastern KY high water, 2021",
                "url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Flood_generic.jpg",
                "credit": "Example / Replace with KY archival photo"
            }
        ],
        "resources": [],
    },
]

# -----------------------------------------------------------------------------
# Optional: load/merge external data events.yaml if present
# -----------------------------------------------------------------------------
def load_events() -> List[Dict[str, Any]]:
    events = BUILTIN_EVENTS.copy()

    yaml_path = Path("data/events.yaml")
    if yaml and yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                extra = yaml.safe_load(f) or []
                if isinstance(extra, list):
                    # Merge by id (override builtin fields if same id)
                    by_id = {e["id"]: e for e in events}
                    for e in extra:
                        if not isinstance(e, dict) or "id" not in e:
                            continue
                        by_id[e["id"]] = {**by_id.get(e["id"], {}), **e}
                    events = list(by_id.values())
        except Exception as e:
            st.warning(f"Could not read data/events.yaml: {e}")

    # Sort by year
    events.sort(key=lambda x: x.get("year", 0))
    return events

EVENTS = load_events()
EVENT_BY_ID = {e["id"]: e for e in EVENTS}

# -----------------------------------------------------------------------------
# Sidebar — Event picker & timeline (Kentucky only)
# -----------------------------------------------------------------------------
st.sidebar.header("Kentucky Flood History")
years = [e["year"] for e in EVENTS]
year_min, year_max = min(years), max(years)

sel_year = st.sidebar.slider("Timeline (year)", min_value=year_min, max_value=year_max, value=1937, step=1)
# Candidate events matching the selected year (or nearest)
if sel_year not in years:
    # Find nearest year present
    nearest = min(years, key=lambda y: abs(y - sel_year))
    sel_year = nearest

# Build a list for selection UI
label_map = {f'{e["year"]} — {e["name"]}': e["id"] for e in EVENTS}
default_label = next(k for k, v in label_map.items() if EVENT_BY_ID[v]["year"] == sel_year)
selected_label = st.sidebar.selectbox("Choose an event", list(label_map.keys()), index=list(label_map.keys()).index(default_label))
selected_id = label_map[selected_label]
event = EVENT_BY_ID[selected_id]

# Layer toggles
st.sidebar.header("Layers")
show_area = st.sidebar.checkbox("Affected area (polygon)", value=True)
show_markers = st.sidebar.checkbox("Key locations", value=True)
show_crests = st.sidebar.checkbox("River crest table", value=True)
show_photos = st.sidebar.checkbox("Historical photos", value=True)

st.sidebar.caption("Tip: You can add or edit events in **data/events.yaml** (no code changes needed).")

# -----------------------------------------------------------------------------
# Map helpers
# -----------------------------------------------------------------------------
def style_area(_):
    return {"color": "#0F766E", "weight": 3, "fillOpacity": 0.08}

def highlight_area(_):
    return {"color": "#115E59", "weight": 3, "fillOpacity": 0.12}

# Kentucky-centric default
KY_CENTER = (37.8, -85.0)
KY_ZOOM = 7

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
st.title("Historical Flood Events StoryMap — Kentucky")
st.write("Explore major Kentucky floods on a **timeline** and **map**, with context on **impacts**, **river crests**, and **photos**.")

# Top summary cards
c1, c2, c3, c4 = st.columns([2, 1, 1, 2], gap="large")
with c1:
    st.subheader(f'{event["year"]}: {event["name"]}')
    st.caption(event.get("dates", ""))
with c2:
    st.metric("Deaths (approx.)", event.get("deaths", "—"))
with c3:
    damages = event.get("damages_usd_bil")
    st.metric("Damages (USD, est.)", f'${damages:.1f}B' if isinstance(damages, (int, float)) else "—")
with c4:
    st.caption("Counties notably affected:")
    st.write(", ".join(event.get("counties", [])) or "—")

# Map + Right panel
map_col, info_col = st.columns([2.1, 1.0], gap="large")

with map_col:
    # Base Folium map
    m = folium.Map(location=KY_CENTER, zoom_start=KY_ZOOM, tiles="CartoDB positron")

    # Affected area polygon
    if show_area and "geojson" in event:
        gj = event["geojson"]
        tooltip = None
        # Try to show a friendly tooltip if fields exist
        try:
            tooltip = GeoJsonTooltip(
                fields=[],  # keep empty to avoid folium assertions; popup handled below
                aliases=[],
                sticky=True,
                localize=True,
            )
        except Exception:
            tooltip = None

        GeoJson(
            gj,
            name="Affected area",
            style_function=style_area,
            highlight_function=highlight_area,
            tooltip=tooltip
        ).add_to(m)

        # Fit map to the polygon bounds if possible
        try:
            # Collect bounds
            bounds = None
            for f in gj.get("features", []):
                geom = f.get("geometry", {})
                if geom.get("type") in ("Polygon", "MultiPolygon"):
                    # crude bounds walker
                    def walk(c, acc):
                        if not c:
                            return
                        if isinstance(c[0], (int, float)):  # lon, lat
                            lon, lat = c[0], c[1]
                            acc[0] = min(acc[0], lat); acc[1] = min(acc[1], lon)
                            acc[2] = max(acc[2], lat); acc[3] = max(acc[3], lon)
                        else:
                            for cc in c:
                                walk(cc, acc)
                    acc = [ 90, 180, -90, -180 ]  # minLat, minLon, maxLat, maxLon
                    walk(geom.get("coordinates"), acc)
                    bounds = [[acc[0], acc[1]], [acc[2], acc[3]]]
                    break
            if bounds:
                m.fit_bounds(bounds, padding=(10, 10))
        except Exception:
            pass

    # Key location markers
    if show_markers:
        for mk in event.get("markers", []):
            folium.Marker(
                location=[mk["lat"], mk["lon"]],
                tooltip=mk.get("name", "Location"),
                icon=folium.Icon(icon="info-sign")
            ).add_to(m)

    LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=740, returned_objects=[])

with info_col:
    st.subheader("Event Overview")
    st.write(event.get("summary", ""))

    st.divider()
    st.subheader("Impacts")
    st.markdown(
        f"- **Deaths:** {event.get('deaths', '—')}\n"
        f"- **Estimated damages:** {('$' + str(event['damages_usd_bil']) + 'B') if isinstance(event.get('damages_usd_bil'), (int, float)) else '—'}\n"
        f"- **Counties:** {', '.join(event.get('counties', [])) or '—'}"
    )

# River crests (table)
if show_crests:
    st.subheader("River Crests (selected sites)")
    df = pd.DataFrame(event.get("river_crests", []))
    if not df.empty:
        df = df.rename(columns={"gage": "Gage / Location", "crest_ft": "Crest (ft)", "date": "Date"})
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No crest data loaded for this event yet.")

# Photo gallery
if show_photos and event.get("photos"):
    st.subheader("Historical Photos")
    pc = st.columns(2)
    for i, photo in enumerate(event["photos"]):
        with pc[i % 2]:
            st.image(photo["url"], caption=f"{photo.get('title','')}\n{photo.get('credit','')}", use_container_width=True)

# Resources / Links
if event.get("resources"):
    st.subheader("Resources")
    for r in event["resources"]:
        st.markdown(f"- [{r['label']}]({r['url']})")

# Advanced: authoring tools
with st.expander("➕ Add / edit events (authoring)"):
    st.write(
        "Create a file at `data/events.yaml` to extend/override events without code changes.\n\n"
        "**YAML schema example:**"
    )
    st.code("""\
- id: 1937_ohio_river_flood
  name: 1937 Ohio River Flood
  year: 1937
  dates: "Jan 9 – Feb 5, 1937"
  summary: "Your sourced summary here."
  deaths: 385
  damages_usd_bil: 8.7
  counties: ["Jefferson", "McCracken"]
  geojson:
    type: FeatureCollection
    features:
      - type: Feature
        properties: { event: "1937 Ohio River Flood" }
        geometry:
          type: Polygon
          coordinates:
            - [[-89.0, 37.2], [-88.3, 37.1], [-87.7, 37.3], [-86.3, 37.7], [-89.0, 37.2]]
  markers:
    - { name: "Louisville", lat: 38.2527, lon: -85.7585 }
  river_crests:
    - { gage: "Louisville, OH (McAlpine)", crest_ft: 52.0, date: "1937-01-27" }
  photos:
    - { title: "Downtown Louisville", url: "https://…", credit: "Source" }
  resources:
    - { label: "NWS summary", url: "https://…" }
""", language="yaml")

st.caption(
    "Note: Values provided here include placeholders. Replace with sourced figures and authoritative geometries. "
    "This app is scoped to **Kentucky** and starts in a Kentucky-centric view."
)
