import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import base64
import re
import json

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from folium import GeoJson, GeoJsonTooltip, LayerControl
import requests

try:
    import yaml
except Exception:
    yaml = None

# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Kentucky Historical Flood StoryMap", layout="wide")

# -----------------------------------------------------------------------------
# GitHub settings (secrets or env)
# -----------------------------------------------------------------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN", ""))
GITHUB_REPO = st.secrets.get("GITHUB_REPO", os.getenv("GITHUB_REPO", ""))
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", os.getenv("GITHUB_BRANCH", "main"))
GITHUB_PATH = st.secrets.get("GITHUB_PATH", os.getenv("GITHUB_PATH", "data/events.yaml"))

GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
} if GITHUB_TOKEN else {}

# -----------------------------------------------------------------------------
# Built-in Kentucky flood events (sample placeholders)
# -----------------------------------------------------------------------------
BUILTIN_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "1937_ohio_river_flood",
        "name": "1937 Ohio River Flood",
        "year": 1937,
        "dates": "Jan 9 – Feb 5, 1937",
        "summary": ("Historic Ohio River basin flood impacting Louisville, Paducah, and many communities along the river."),
        "deaths": 385,
        "damages_usd_bil": 8.7,   # placeholder
        "counties": ["Jefferson", "McCracken", "Daviess", "Campbell", "Kenton", "Henderson"],
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
            {"gage": "Louisville, OH (McAlpine)", "crest_ft": 52.0, "date": "1937-01-27"},
            {"gage": "Paducah, OH", "crest_ft": 60.8, "date": "1937-02-02"},
            {"gage": "Cincinnati, OH", "crest_ft": 79.99, "date": "1937-01-26"},
        ],
        "photos": [
            {"title": "Downtown Louisville under water",
             "url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Louisville_flood_1937.jpg",
             "credit": "Wikimedia Commons"},
        ],
        "resources": [{"label": "NWS summary", "url": "https://www.weather.gov/lmk/1937flood"}],
    },
    {
        "id": "1978_louisville_flash_flood",
        "name": "1978 Louisville Flash Flood",
        "year": 1978,
        "dates": "May 19–20, 1978",
        "summary": "Torrential thunderstorms produced extreme short-duration rainfall in the Louisville metro.",
        "deaths": 5, "damages_usd_bil": 0.2,
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
        "markers": [{"name": "Louisville", "lat": 38.2527, "lon": -85.7585}],
        "river_crests": [{"gage": "Beargrass Creek", "crest_ft": None, "date": "1978-05-20"}],
        "photos": [],
        "resources": [],
    },
    {
        "id": "2021_winter_floods",
        "name": "February 2021 Kentucky Floods",
        "year": 2021,
        "dates": "Feb 26 – Mar 5, 2021",
        "summary": "Prolonged rainfall and snowmelt caused widespread flooding in eastern & south-central Kentucky.",
        "deaths": 3, "damages_usd_bil": 0.1,
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
            {"gage": "North Fork KY River at Jackson", "crest_ft": 43.5, "date": "2021-03-01"},
            {"gage": "Red River at Clay City", "crest_ft": 25.8, "date": "2021-03-01"},
        ],
        "photos": [],
        "resources": [],
    },
]

# -----------------------------------------------------------------------------
# Load external YAML (optional)
# -----------------------------------------------------------------------------
def load_events() -> List[Dict[str, Any]]:
    events = BUILTIN_EVENTS.copy()
    path = Path("data/events.yaml")
    if yaml and path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                extra = yaml.safe_load(f) or []
                if isinstance(extra, list):
                    by_id = {e["id"]: e for e in events}
                    for e in extra:
                        if isinstance(e, dict) and "id" in e:
                            by_id[e["id"]] = {**by_id.get(e["id"], {}), **e}
                    events = list(by_id.values())
        except Exception as e:
            st.warning(f"Could not read data/events.yaml: {e}")
    events.sort(key=lambda x: x.get("year", 0))
    return events

EVENTS = load_events()
EVENT_BY_ID = {e["id"]: e for e in EVENTS}

# -----------------------------------------------------------------------------
# Sidebar — Timeline and event select
# -----------------------------------------------------------------------------
st.sidebar.header("Kentucky Flood History")
years = [e["year"] for e in EVENTS]
sel_year = st.sidebar.slider("Timeline (year)", min_value=min(years), max_value=max(years), value=1937, step=1)
if sel_year not in years:
    sel_year = min(years, key=lambda y: abs(y - sel_year))

label_map = {f'{e["year"]} — {e["name"]}': e["id"] for e in EVENTS}
default_label = next(k for k, v in label_map.items() if EVENT_BY_ID[v]["year"] == sel_year)
selected_label = st.sidebar.selectbox("Choose an event", list(label_map.keys()),
                                      index=list(label_map.keys()).index(default_label))
event = EVENT_BY_ID[label_map[selected_label]]

# Layer toggles
st.sidebar.header("Layers")
show_area = st.sidebar.checkbox("Affected area (polygon)", True)
show_markers = st.sidebar.checkbox("Key locations", True)
show_crests = st.sidebar.checkbox("River crest table", True)
show_photos = st.sidebar.checkbox("Historical photos", True)

st.sidebar.caption("You can extend/override events in **data/events.yaml**.")

# -----------------------------------------------------------------------------
# Map helpers
# -----------------------------------------------------------------------------
def style_area(_): return {"color": "#0F766E", "weight": 3, "fillOpacity": 0.08}
def highlight_area(_): return {"color": "#115E59", "weight": 3, "fillOpacity": 0.12}
KY_CENTER, KY_ZOOM = (37.8, -85.0), 7

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
st.title("Historical Flood Events StoryMap — Kentucky")
st.write("Explore major Kentucky floods with a **timeline**, **map**, and event context.")

c1, c2, c3, c4 = st.columns([2, 1, 1, 2], gap="large")
with c1:
    st.subheader(f'{event["year"]}: {event["name"]}')
    st.caption(event.get("dates", ""))
with c2:
    st.metric("Deaths (approx.)", event.get("deaths", "—"))
with c3:
    d = event.get("damages_usd_bil")
    st.metric("Damages (USD, est.)", f'${d:.1f}B' if isinstance(d, (int, float)) else "—")
with c4:
    st.caption("Counties notably affected:")
    st.write(", ".join(event.get("counties", [])) or "—")

map_col, info_col = st.columns([2.1, 1.0], gap="large")

with map_col:
    m = folium.Map(location=KY_CENTER, zoom_start=KY_ZOOM, tiles="CartoDB positron")

    if show_area and "geojson" in event:
        gj = event["geojson"]
        GeoJson(gj, name="Affected area", style_function=style_area,
                highlight_function=highlight_area).add_to(m)
        # Fit to polygon
        try:
            def bounds_from_geom(coords):
                acc = [90, 180, -90, -180]
                def walk(c):
                    if not c: return
                    if isinstance(c[0], (int, float)):
                        lon, lat = c[0], c[1]
                        acc[0] = min(acc[0], lat); acc[1] = min(acc[1], lon)
                        acc[2] = max(acc[2], lat); acc[3] = max(acc[3], lon)
                    else:
                        for cc in c: walk(cc)
                walk(coords); return [[acc[0], acc[1]],[acc[2], acc[3]]]
            for f in gj.get("features", []):
                g = f.get("geometry", {})
                if g.get("type") in ("Polygon","MultiPolygon"):
                    b = bounds_from_geom(g.get("coordinates"))
                    if b: m.fit_bounds(b, padding=(10,10))
                    break
        except Exception:
            pass

    if show_markers:
        for mk in event.get("markers", []):
            folium.Marker([mk["lat"], mk["lon"]], tooltip=mk.get("name","Location"),
                          icon=folium.Icon(icon="info-sign")).add_to(m)

    LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=740, returned_objects=[])

with info_col:
    st.subheader("Event Overview")
    st.write(event.get("summary", ""))
    st.divider()
    st.subheader("Impacts")
    st.markdown(
        f"- **Deaths:** {event.get('deaths','—')}\n"
        f"- **Estimated damages:** {('$' + str(event['damages_usd_bil']) + 'B') if isinstance(event.get('damages_usd_bil'), (int,float)) else '—'}\n"
        f"- **Counties:** {', '.join(event.get('counties', [])) or '—'}"
    )

if show_crests:
    st.subheader("River Crests (selected sites)")
    df = pd.DataFrame(event.get("river_crests", []))
    if not df.empty:
        df = df.rename(columns={"gage":"Gage / Location","crest_ft":"Crest (ft)","date":"Date"})
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No crest data loaded for this event yet.")

if show_photos and event.get("photos"):
    st.subheader("Historical Photos")
    cols = st.columns(2)
    for i, photo in enumerate(event["photos"]):
        with cols[i % 2]:
            st.image(photo["url"], caption=f"{photo.get('title','')}\n{photo.get('credit','')}",
                     use_container_width=True)

if event.get("resources"):
    st.subheader("Resources")
    for r in event["resources"]:
        st.markdown(f"- [{r['label']}]({r['url']})")

# -----------------------------------------------------------------------------
# CONTRIBUTION FORM → GitHub commit (append to data/events.yaml)
# -----------------------------------------------------------------------------
st.divider()
st.header("Contribute a Kentucky Flood Event")

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

with st.form("submit_event"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Event name*", placeholder="e.g., July 2022 Eastern Kentucky Floods")
        year = st.number_input("Year*", min_value=1800, max_value=2100, value=2022, step=1)
        dates = st.text_input("Dates", placeholder="e.g., Jul 26 – Aug 2, 2022")
        deaths = st.number_input("Deaths (approx.)", min_value=0, value=0)
        damages = st.number_input("Damages (USD billions, est.)", min_value=0.0, value=0.0, step=0.1, format="%.1f")
    with c2:
        counties_str = st.text_input("Counties (comma-separated)", placeholder="Breathitt, Perry, Knott, Letcher")
        summary = st.text_area("Short summary*", height=120)
        markers_json = st.text_area("Markers JSON (optional)", placeholder='[{"name": "Whitesburg", "lat": 37.1187, "lon": -82.8263}]', height=120)
    geojson_text = st.text_area("Affected area GeoJSON (FeatureCollection)*",
                                placeholder='{"type":"FeatureCollection","features":[...]}', height=160)
    photos_json = st.text_area("Photos JSON (optional)", placeholder='[{"title":"Main St.","url":"https://...","credit":"Source"}]')
    resources_json = st.text_area("Resources JSON (optional)", placeholder='[{"label":"NWS Summary","url":"https://..."}]')

    submitted = st.form_submit_button("Submit to GitHub")

def parse_optional_json(txt: str, fallback):
    if not txt.strip():
        return fallback
    try:
        val = json.loads(txt)
        return val if isinstance(val, list) else fallback
    except Exception:
        return fallback

def validate_geojson(txt: str) -> Optional[Dict[str, Any]]:
    try:
        gj = json.loads(txt)
        if isinstance(gj, dict) and gj.get("type") == "FeatureCollection" and isinstance(gj.get("features"), list):
            return gj
    except Exception:
        pass
    return None

def build_event_payload(name, year, dates, summary, deaths, damages, counties_str,
                        markers_json, geojson_text, photos_json, resources_json) -> Optional[Dict[str,Any]]:
    if not (name and summary and geojson_text):
        st.error("Please provide at least **Event name**, **Summary**, and **GeoJSON**.")
        return None
    geojson = validate_geojson(geojson_text)
    if not geojson:
        st.error("GeoJSON must be a valid **FeatureCollection** with a features list.")
        return None
    counties = [c.strip() for c in counties_str.split(",") if c.strip()] if counties_str else []
    markers = parse_optional_json(markers_json, [])
    photos = parse_optional_json(photos_json, [])
    resources = parse_optional_json(resources_json, [])
    eid = slugify(f"{year}_{name}")
    return {
        "id": eid, "name": name, "year": int(year),
        "dates": dates, "summary": summary, "deaths": int(deaths),
        "damages_usd_bil": float(damages) if damages else None,
        "counties": counties, "geojson": geojson,
        "markers": markers, "river_crests": [],  # user can edit later
        "photos": photos, "resources": resources,
    }

def github_get_file(repo: str, path: str, ref: str):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = requests.get(url, headers=GH_HEADERS, params={"ref": ref} if ref else None, timeout=30)
    return r

def github_put_file(repo: str, path: str, message: str, content_b64: str, sha: Optional[str], branch: str):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {"message": message, "content": content_b64, "branch": branch}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=GH_HEADERS, json=payload, timeout=30)
    return r

def append_event_to_yaml_text(yaml_text: str, event_obj: Dict[str,Any]) -> str:
    data = []
    if yaml_text.strip():
        try:
            existing = yaml.safe_load(yaml_text) or []
            if isinstance(existing, list):
                data = existing
        except Exception:
            pass
    # replace or append by id
    by_id = {e.get("id"): e for e in data if isinstance(e, dict) and "id" in e}
    by_id[event_obj["id"]] = event_obj
    new_list = list(by_id.values())
    new_list.sort(key=lambda x: x.get("year", 0))
    return yaml.safe_dump(new_list, sort_keys=False, allow_unicode=True)

if submitted:
    event_obj = build_event_payload(name, year, dates, summary, deaths, damages,
                                    counties_str, markers_json, geojson_text,
                                    photos_json, resources_json)
    if event_obj:
        if not (GITHUB_TOKEN and GITHUB_REPO):
            st.error("Submission disabled: missing `GITHUB_TOKEN` and/or `GITHUB_REPO` in Streamlit Secrets.")
        else:
            try:
                # 1) Fetch existing YAML (if any)
                resp = github_get_file(GITHUB_REPO, GITHUB_PATH, GITHUB_BRANCH)
                sha = None
                existing_yaml = ""
                if resp.status_code == 200:
                    body = resp.json()
                    sha = body.get("sha")
                    content = body.get("content", "")
                    if content:
                        existing_yaml = base64.b64decode(content).decode("utf-8")
                elif resp.status_code != 404:
                    st.error(f"GitHub read error: {resp.status_code} {resp.text}")
                    st.stop()

                # 2) Append/replace event and PUT
                new_yaml = append_event_to_yaml_text(existing_yaml, event_obj)
                new_b64 = base64.b64encode(new_yaml.encode("utf-8")).decode("utf-8")
                commit_msg = f"feat(events): add {event_obj['id']} to {GITHUB_PATH}"
                put = github_put_file(GITHUB_REPO, GITHUB_PATH, commit_msg, new_b64, sha, GITHUB_BRANCH)
                if put.status_code in (200, 201):
                    st.success("Submitted! Your event was written to GitHub.")
                    st.caption(f"Repo: `{GITHUB_REPO}` • Branch: `{GITHUB_BRANCH}` • Path: `{GITHUB_PATH}`")
                else:
                    st.error(f"GitHub write error: {put.status_code} {put.text}")
            except Exception as e:
                st.error(f"Submission failed: {e}")

# Footer
st.caption(
    "Data sources: built-in examples + optional `data/events.yaml`. "
    "Submissions append to your GitHub repo via the GitHub Contents API when configured."
)
