#!/usr/bin/env python3
"""ConStruct world map generator — output: world_map.html + world_map_data.js"""

import os, sys, json, argparse, psycopg2
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CA_PATH = os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(CA_PATH))
import canonical_actors as CA

TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')
OUTPUT_DIR = os.path.join(BASE, 'visuals')
DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'

CAPITALS_EXTRA = {
    'Syria': (33.51, 36.29), 'Afghanistan': (34.53, 69.17), 'Mexico': (19.43, -99.13),
    'Iraq': (33.32, 44.42), 'Somalia': (2.04, 45.34), 'Sudan': (15.50, 32.56),
    'Libya': (32.88, 13.19), 'Yemen': (15.35, 44.21), 'Nigeria': (9.08, 7.40),
    'Ethiopia': (9.02, 38.75), 'Myanmar': (19.75, 96.13), 'Colombia': (4.71, -74.07),
    'DR Congo': (-4.32, 15.31), 'South Sudan': (4.85, 31.58), 'Mali': (12.65, -8.00),
    'Palestine': (31.95, 35.23), 'Venezuela': (10.48, -66.90),
    'Burkina Faso': (12.36, -1.53), 'Niger': (13.51, 2.11), 'Cameroon': (3.85, 11.52),
    'Chad': (12.11, 15.05), 'CAR': (4.36, 18.58), 'Mozambique': (-25.97, 32.59),
    'Senegal': (14.69, -17.44), 'Guinea': (9.64, -13.58), 'Sierra Leone': (8.48, -13.23),
    'Liberia': (6.43, -9.43), 'Ivory Coast': (5.35, -4.03), 'Ghana': (5.60, -0.17),
    'Angola': (-8.84, 13.23), 'Zimbabwe': (-17.83, 31.05), 'Zambia': (-15.42, 28.28),
    'Tanzania': (-6.17, 35.74), 'Kenya': (-1.29, 36.82), 'Uganda': (0.31, 32.58),
    'Rwanda': (-1.94, 30.06), 'Burundi': (-3.38, 29.36), 'Congo': (-4.38, 15.28),
    'Malawi': (-13.98, 33.79), 'Namibia': (-22.56, 17.08), 'Botswana': (-24.65, 25.91),
    'South Africa': (-25.75, 28.19), 'Eswatini': (-26.50, 31.50),
    'Madagascar': (-18.91, 47.53), 'Mauritania': (18.08, -15.98),
    'Djibouti': (11.59, 43.15), 'Eritrea': (15.33, 38.93),
    'Guatemala': (14.63, -90.52), 'Honduras': (14.07, -87.21),
    'El Salvador': (13.69, -89.22), 'Nicaragua': (12.13, -86.25),
    'Costa Rica': (9.93, -84.08), 'Panama': (8.98, -79.52),
    'Haiti': (18.59, -72.31), 'Cuba': (21.52, -77.78),
    'Ecuador': (-0.23, -78.52), 'Peru': (-12.05, -77.04),
    'Bolivia': (-16.50, -68.15), 'Paraguay': (-23.44, -58.44),
    'Uruguay': (-34.90, -56.16), 'Bangladesh': (23.81, 90.41),
    'Sri Lanka': (6.93, 79.86), 'Nepal': (27.72, 85.32), 'Cambodia': (11.56, 104.92),
    'Laos': (17.97, 102.63), 'Mongolia': (47.92, 106.92),
    'Kyrgyzstan': (42.87, 74.59), 'Tajikistan': (38.54, 68.78),
    'Turkmenistan': (37.96, 58.38), 'Uzbekistan': (41.31, 69.28),
    'Kazakhstan': (51.16, 71.43), 'Georgia': (41.72, 44.78),
    'Armenia': (40.18, 44.51), 'Azerbaijan': (40.41, 49.87),
    'Moldova': (47.02, 28.84), 'Belarus': (53.90, 27.57), 'Albania': (41.33, 19.82),
    'Bosnia': (43.86, 18.41), 'Kosovo': (42.60, 20.90), 'Cyprus': (35.17, 33.37),
    'Lebanon': (33.89, 35.50), 'Jordan': (31.96, 35.95), 'Kuwait': (29.37, 47.98),
    'Bahrain': (26.12, 50.56), 'Qatar': (25.35, 51.18), 'Oman': (23.61, 58.59),
    'UAE': (24.45, 54.38), 'United Arab Emirates': (24.45, 54.38),
    'Slovenia': (46.05, 14.50), 'Croatia': (45.81, 15.98), 'Slovakia': (48.15, 17.11),
    'Lithuania': (54.69, 25.28), 'Latvia': (56.95, 24.10), 'Estonia': (59.44, 24.75),
}

TERRITORY_COORDS = {
    'Hong Kong': (22.30, 114.17), 'Taiwan': (23.70, 121.00),
    'Macau': (22.20, 113.55), 'Manchuria': (46.00, 126.00),
    'Guam': (13.44, 144.79), 'Hawaii': (21.31, -157.83),
    'Alaska': (64.20, -149.49), 'Philippines': (12.88, 121.77),
    'Korea': (37.57, 126.98), 'Vietnam': (14.06, 108.28),
    'Singapore': (1.35, 103.82), 'Malaysia': (3.14, 101.69),
    'Myanmar': (19.75, 96.13), 'India': (20.59, 78.96),
    'Pakistan': (30.38, 69.35), 'Bangladesh': (23.81, 90.41),
    'Sri Lanka': (6.93, 79.86), 'Portugal': (38.72, -9.13),
    'Spain': (40.42, -3.70), 'Gibraltar': (36.14, -5.35),
    'Panama': (8.98, -79.52), 'Suez': (29.97, 32.55),
    'Crimea': (45.35, 34.31), 'Donetsk': (48.02, 37.80),
    'Luhansk': (48.57, 39.30), 'South Ossetia': (42.23, 43.97),
    'Abkhazia': (43.00, 41.02), 'Transnistria': (46.85, 29.60),
    'Nagorno-Karabakh': (39.82, 46.75), 'Kosovo': (42.60, 20.90),
    'Golan Heights': (32.99, 35.75), 'West Bank': (31.95, 35.30),
    'Gaza': (31.50, 34.47), 'Sinai': (29.50, 33.80),
    'Cyprus': (35.17, 33.37), 'Falkland Islands': (-51.80, -59.52),
    'Falklands': (-51.80, -59.52), 'Puerto Rico': (18.22, -66.59),
    'Greenland': (64.18, -51.72), 'Svalbard': (78.22, 15.63),
    'Alsace-Lorraine': (48.69, 6.18), 'Karelia': (61.88, 32.00),
    'Sakhalin': (50.56, 142.95), 'Kuril': (46.50, 151.50),
}

# Base coords from canonical 47
CAPITALS = {}
for code, a in CA.CANONICAL_ACTORS.items():
    latlon = {'CHN': (39.90, 116.40), 'USA': (38.90, -77.04), 'RUS': (55.75, 37.61),
              'JPN': (35.68, 139.76), 'DEU': (52.52, 13.40), 'FRA': (48.85, 2.35),
              'GBR': (51.51, -0.13), 'IND': (28.61, 77.23), 'BRA': (-15.79, -47.88),
              'TUR': (39.93, 32.86), 'IRN': (35.69, 51.39), 'ISR': (31.77, 35.23),
              'EGY': (30.04, 31.24), 'SAU': (24.71, 46.68), 'AUS': (-35.28, 149.13),
              'KOR': (37.57, 126.98), 'PRK': (39.03, 125.75), 'UKR': (50.45, 30.52),
              'PAK': (33.68, 73.05), 'PHL': (14.60, 120.98), 'VNM': (21.03, 105.85),
              'TWN': (25.03, 121.57), 'IDN': (-6.21, 106.85), 'CAN': (45.42, -75.70),
              'ITA': (41.90, 12.49), 'ESP': (40.42, -3.70), 'MEX': (19.43, -99.13),
              'SRB': (44.79, 20.45), 'SGP': (1.35, 103.82), 'NGA': (9.08, 7.40),
              'AFG': (34.53, 69.17), 'BGD': (23.81, 90.41), 'MMR': (19.75, 96.13),
              'THA': (13.75, 100.50), 'MYS': (3.14, 101.69),
              'ARG': (-34.61, -58.38), 'CHL': (-33.45, -70.67),
              'COL': (4.71, -74.07), 'PER': (-12.05, -77.04),
              'ZAF': (-25.75, 28.19), 'SWE': (59.33, 18.07),
              'NLD': (52.37, 4.90), 'POL': (52.23, 21.01), 'BEL': (50.85, 4.35),
              'GRC': (37.98, 23.73), 'PRT': (38.72, -9.13), 'CZE': (50.08, 14.42),
              'AUT': (48.21, 16.37), 'CHE': (46.95, 7.45), 'DNK': (55.68, 12.57),
              'NOR': (59.91, 10.75), 'FIN': (60.17, 24.94), 'HUN': (47.50, 19.04),
              'ROU': (44.43, 26.10), 'BGR': (42.70, 23.32), 'HRV': (45.81, 15.98),
              'IRQ': (33.32, 44.42), 'SYR': (33.51, 36.29), 'LBN': (33.89, 35.50),
              'LBY': (32.88, 13.19), 'SDN': (15.50, 32.56), 'SOM': (2.04, 45.34),
              'YEM': (15.35, 44.21), 'ETH': (9.02, 38.75), 'CUB': (21.52, -77.78),
              'VEN': (10.48, -66.90), 'DZA': (36.75, 3.04), 'MAR': (34.02, -6.84),
              'GHA': (5.60, -0.17), 'KEN': (-1.29, 36.82), 'TZA': (-6.17, 35.74),
              'UGA': (0.31, 32.58), 'MOZ': (-25.97, 32.59), 'AGO': (-8.84, 13.23),
              'ZWE': (-17.83, 31.05), 'CMR': (3.85, 11.52), 'ZMB': (-15.42, 28.28),
              'TCD': (12.11, 15.05), 'NER': (13.51, 2.11), 'MLI': (12.65, -8.00),
              'BFA': (12.36, -1.53), 'BOL': (-16.50, -68.15)}.get(code)
    if latlon:
        CAPITALS[code] = latlon


def load_cow_territorial():
    flows = []
    for code in CA.CANONICAL_ACTORS:
        tpath = os.path.join(TIMELINE_DIR, f'{code}.json')
        if not os.path.exists(tpath):
            continue
        with open(tpath, encoding='utf-8') as f:
            data = json.load(f)
        for e in data.get('skeleton_cow', []):
            if e['type'] in ('TERR_LOSS', 'TERR_GAIN') and e.get('year_start', 0) >= 1800:
                fr = code if e['type'] == 'TERR_LOSS' else e.get('from', '')
                to = e.get('to', '') if e['type'] == 'TERR_LOSS' else code
                if fr and to:
                    flows.append({'from': fr, 'to': to, 'year': e['year_start'],
                                  'type': e['type'], 'label': e.get('entity', e.get('label', ''))})
    return flows


def load_ucdp_yearly(pg_dsn):
    conn = psycopg2.connect(pg_dsn)
    cur = conn.cursor()
    cur.execute(
        "SELECT location, EXTRACT(YEAR FROM time)::int AS yr, "
        "SUM((metadata->>'deaths_best')::int) AS deaths, COUNT(*) AS events "
        "FROM events WHERE source='UCDP' AND location IS NOT NULL "
        "GROUP BY location, yr ORDER BY yr")
    rows = cur.fetchall()
    cur.close(); conn.close()
    yearly = {}
    for loc, yr, deaths, evts in rows:
        clean = loc.split('(')[0].strip()
        if clean not in yearly:
            yearly[clean] = {}
        yearly[clean][int(yr)] = {'deaths': int(deaths or 0), 'events': int(evts or 0)}
    return yearly


def load_gdelt_all(pg_dsn):
    conn = psycopg2.connect(pg_dsn)
    cur = conn.cursor()
    cur.execute(
        "SELECT actor1_code, AVG(avg_tone), COUNT(*) FROM events "
        "WHERE source='GDELT' AND time >= NOW() - INTERVAL '48 hours' "
        "AND actor1_code IS NOT NULL GROUP BY actor1_code")
    tones = {r[0]: {'tone': round(r[1] or 0, 2), 'count': int(r[2] or 0)} for r in cur.fetchall() if r[0]}

    # --- source_weights (coverage density) ---
    density = {}
    try:
        cur.execute("SELECT actor_code, coverage_density FROM source_weights")
        density = {r[0]: round(r[1], 2) for r in cur.fetchall() if r[0]}
    except Exception:
        pass  # 表不存在则跳过
    # --- end density ---

    cur.execute(
        "SELECT domain, COUNT(*) FROM events "
        "WHERE source='GDELT' AND event_class='structural' AND domain IS NOT NULL "
        "AND time >= NOW() - INTERVAL '90 days' GROUP BY domain")
    structural = {r[0]: r[1] for r in cur.fetchall()}
    cur.execute(
        "SELECT domain, time::date, COUNT(*) FROM events "
        "WHERE source='GDELT' AND event_class='structural' AND domain IS NOT NULL "
        "AND time >= NOW() - INTERVAL '90 days' GROUP BY domain, time::date ORDER BY time::date")
    timeline = {}
    for dom, d, cnt in cur.fetchall():
        if dom not in timeline: timeline[dom] = {}
        timeline[dom][d.isoformat()] = int(cnt)
    cur.close(); conn.close()
    return tones, structural, timeline, density


def build_outputs(flows, ucdp_yearly, gdelt_tones, gdelt_structural, gdelt_timeline, gdelt_density, output_dir):
    code_to_name = {c: a['name'] for c, a in CA.CANONICAL_ACTORS.items()}

    # Country coords
    country_coords = dict(CAPITALS_EXTRA)
    for code, a in CA.CANONICAL_ACTORS.items():
        if CAPITALS.get(code):
            country_coords[a['name']] = CAPITALS[code]

    # === world_map_data.js ===
    data_vars = [
        ('ucdpData', {k: {str(y): v for y, v in d.items()} for k, d in ucdp_yearly.items()}),
        ('coords', country_coords),
        ('structData', gdelt_structural),
        ('timelineData', gdelt_timeline),
        ('cnNames', code_to_name),
    ]
    lines = ['// ConStruct world_map_data.js — ' + datetime.now().isoformat()]
    for vn, obj in data_vars:
        lines.append(f'var {vn} = {json.dumps(obj, ensure_ascii=False)};')
    dp = os.path.join(output_dir, 'world_map_data.js')
    with open(dp, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'[data] → {dp}')

    # GDELT dots
    gdelt_js = []
    for code, a in CA.CANONICAL_ACTORS.items():
        lat, lon = CAPITALS.get(code, (0, 0))
        g = gdelt_tones.get(code, {})
        tone = g.get('tone', 0); cnt = g.get('count', 0)
        if cnt < 2: continue
        tc = '#2E7D32' if tone >= 0 else '#C62828'
        dens = gdelt_density.get(code)
        dens_str = f' · dens={dens}' if dens else ''
        gdelt_js.append(
            f'L.circleMarker([{lat},{lon}],{{radius:3.5,fillColor:"{tc}",color:"#fff",weight:1,fillOpacity:0.85}})'
            f'.bindTooltip("{a["name"]}: tone={tone} ({cnt} ev){dens_str}").addTo(gdeltLayer);')

    # COW flows
    flow_js = []
    for fl in flows[-20:]:
        label = fl.get('label', '') or fl.get('entity', '')
        fr_coord = TERRITORY_COORDS.get(label) if fl['type'] == 'TERR_LOSS' else None
        to_coord = TERRITORY_COORDS.get(label) if fl['type'] == 'TERR_GAIN' else None
        fr_lat, fr_lon = fr_coord or CAPITALS.get(fl['from'], (0, 0))
        to_lat, to_lon = to_coord or CAPITALS.get(fl['to'], (0, 0))
        if fr_lat == 0 or to_lat == 0: continue
        c = '#EF6C00' if fl['type'] == 'TERR_LOSS' else '#8E24AA'
        flow_js.append(
            f'L.polyline([[{fr_lat},{fr_lon}],[{to_lat},{to_lon}]],{{color:"{c}",weight:1.5,opacity:0.4,dashArray:"6,4"}})'
            f'.bindTooltip("{fl["year"]}: {fl.get("label","") or ""} {fl["from"]}→{fl["to"]}").addTo(flowLayer);')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ConStruct 全球冲突时间地图</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css"/>
<style>
html,body{{margin:0;padding:0;height:100%;width:100%;font-family:"Microsoft YaHei",sans-serif;background:#0a0a1a;overflow:hidden}}
#map{{position:absolute;top:0;left:0;right:260px;bottom:0}}
#sidebar{{position:absolute;top:0;right:0;width:260px;height:100vh;background:rgba(15,19,30,0.95);border-left:1px solid #2a3450;display:flex;flex-direction:column;z-index:1000;overflow-y:auto;box-sizing:border-box}}
#sidebar{{width:260px;background:rgba(15,19,30,0.95);border-left:1px solid #2a3450;display:flex;flex-direction:column;z-index:1000;overflow-y:auto}}
.sidebar-hdr{{padding:12px;border-bottom:1px solid #2a3450;color:#e8b44c;font-size:13px;font-weight:bold}}
.domain-card{{padding:10px 12px;cursor:pointer;border-bottom:1px solid rgba(42,52,80,0.4);transition:background 0.2s}}
.domain-card:hover{{background:rgba(42,52,80,0.4)}}
.domain-card.active{{background:rgba(42,52,80,0.6);border-left:3px solid #e8b44c;padding-left:9px}}
.domain-card .name{{font-size:12px;margin-bottom:3px}}
.domain-card .count{{font-size:20px;font-weight:bold}}
.domain-card .sub{{font-size:9px;color:#8895B0;margin-top:2px}}
#chart-area{{padding:12px;flex:1}}
#chart-canvas{{width:100%;height:180px;border-radius:6px;background:rgba(20,25,40,0.6)}}
#chart-detail{{font-size:10px;color:#8895B0;margin-top:8px;line-height:1.5}}
#slider-bar{{padding:8px 12px;border-top:1px solid #2a3450;font-size:11px;color:#d0d4e0}}
#slider-bar input{{width:100%;accent-color:#e8b44c;margin:4px 0}}
.legend{{background:rgba(15,19,30,0.9);padding:8px 10px;border-radius:4px;color:#d0d4e0;font-size:10px;line-height:1.5}}
.legend b{{color:#e8b44c}}
h1{{position:absolute;top:8px;left:60px;z-index:900;color:#e8b44c;font-size:15px;text-shadow:0 2px 6px rgba(0,0,0,.9);margin:0;pointer-events:none}}
</style>
</head>
<body>
<h1>ConStruct 全球冲突时间地图 — UCDP 1989-2025</h1>
<div id="map"></div>
<div id="sidebar">
  <div class="sidebar-hdr">📊 结构领域</div>
  <div id="cards"></div>
  <div id="chart-area">
    <canvas id="chart-canvas" width="232" height="180"></canvas>
    <div id="chart-detail"></div>
  </div>
  <div id="slider-bar">
    年份: <span id="yr-label" style="color:#e8b44c;font-weight:bold">2025</span>
    <input type="range" id="year-range" min="1989" max="2025" value="2025" step="1" oninput="onYearChange()">
  </div>
</div>
<script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"></script>
<script src="world_map_data.js"></script>
<script>
window.addEventListener('error', function(e){{
  var d = document.createElement('div');
  d.style.cssText = 'position:absolute;top:40px;left:10px;background:#900;color:#fff;padding:8px;z-index:9999;font:11px monospace;max-width:600px';
  d.textContent = 'JS ERR: ' + (e.message||e.error||e);
  document.body.appendChild(d);
}});

var map = L.map('map',{{center:[25,10],zoom:2,maxZoom:8,maxBounds:[[-60,-180],[85,180]]}});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'&copy;OSM|ConStruct Lab',maxZoom:18,noWrap:true}}).addTo(map);

var circleLayer = L.layerGroup().addTo(map);
var DOMAIN_COLORS = {{FN:'#2196F3', AI:'#9C27B0', SUPPLY:'#FF9800', ENERGY:'#4CAF50', SOCIAL:'#F44336', MINERAL:'#FF5722'}};
var DOMAIN_LABELS = {{FN:'金融秩序', AI:'AI技术结构', SUPPLY:'产业链贸易', ENERGY:'能源结构', SOCIAL:'社会结构', MINERAL:'关键矿物'}};
var currentDomain = 'ucdp';

function sizeColor(deaths){{
  if (deaths > 50000) return [22,'#B71C1C'];
  if (deaths > 10000) return [18,'#D32F2F'];
  if (deaths > 5000)  return [14,'#E53935'];
  if (deaths > 1000)  return [10,'#FF7043'];
  if (deaths > 100)   return [7,'#FFCA28'];
  return [5,'#42A5F5'];
}}

// === Build sidebar domain cards ===
function buildCards(){{
  var html = '<div class="domain-card active" data-domain="ucdp" onclick="switchDomain(this.dataset.domain)">' +
    '<div class="name" style="color:#E53935">🔥 UCDP 冲突死亡</div>' +
    '<div class="count" style="color:#E53935">126国</div>' +
    '<div class="sub">1989-2025 · 按年份切换</div></div>';
  for (var k in DOMAIN_LABELS){{
    var c = DOMAIN_COLORS[k]||'#888';
    var cnt = structData[k]||0;
    html += '<div class="domain-card" data-domain="'+k+'" onclick="switchDomain(this.dataset.domain)">' +
      '<div class="name" style="color:'+c+'">● '+DOMAIN_LABELS[k]+'</div>' +
      '<div class="count" style="color:'+c+'">'+(cnt||0)+'</div>' +
      '<div class="sub">近90天结构事件</div></div>';
  }}
  document.getElementById('cards').innerHTML = html;
}}

function switchDomain(domain){{
  currentDomain = domain;
  document.querySelectorAll('.domain-card').forEach(function(c){{
    c.classList.toggle('active', c.dataset.domain===domain);
  }});
  var sliderBar = document.getElementById('slider-bar');
  var chartArea = document.getElementById('chart-area');
  if (domain==='ucdp'){{
    sliderBar.style.display = ''; chartArea.style.display = 'none';
    onYearChange();
  }} else {{
    sliderBar.style.display = 'none'; chartArea.style.display = '';
    drawStructChart(domain);
  }}
}}

function onYearChange(){{
  var yr = parseInt(document.getElementById('year-range').value);
  document.getElementById('yr-label').textContent = yr;
  circleLayer.clearLayers();
  for (var c in ucdpData){{
    if (!coords[c]) continue;
    var d = ucdpData[c] && ucdpData[c][String(yr)];
    if (!d) continue;
    var sc = sizeColor(d.deaths);
    L.circleMarker(coords[c],{{radius:sc[0],fillColor:sc[1],color:'#333',weight:1,fillOpacity:0.65}})
      .bindTooltip('<b>'+c+' ('+yr+')</b><br>Deaths:'+d.deaths.toLocaleString()+'<br>Events:'+d.events.toLocaleString())
      .addTo(circleLayer);
  }}
}}

// === Canvas chart for structural domains ===
function drawStructChart(domain){{
  var daily = timelineData[domain]||{{}};
  var today = new Date(), vals=[], labels=[], maxV=0, total=0;
  for (var i=89; i>=0; i--){{
    var d = new Date(today); d.setDate(d.getDate()-i);
    var k = d.toISOString().slice(0,10);
    var v = daily[k]||0; vals.push(v); labels.push(k);
    if (v>maxV) maxV=v; total+=v;
  }}
  var canvas = document.getElementById('chart-canvas');
  var ctx = canvas.getContext('2d');
  var W=canvas.width, H=canvas.height, P=20, R=10;
  ctx.clearRect(0,0,W,H);

  // Grid
  ctx.strokeStyle='rgba(136,149,176,0.15)'; ctx.lineWidth=0.5;
  for (var g=0; g<=4; g++){{
    var gy = P + g*(H-P-R)/(4);
    ctx.beginPath(); ctx.moveTo(P,gy); ctx.lineTo(W-P,gy); ctx.stroke();
  }}

  // Area fill
  var col = DOMAIN_COLORS[domain]||'#888';
  ctx.fillStyle = col+'30';
  ctx.beginPath(); ctx.moveTo(P, H-R);
  for (var i=0; i<vals.length; i++){{
    var x = P+(i/(vals.length-1))*(W-2*P);
    var y = H-R-(maxV?(vals[i]/maxV)*(H-P-R-10):0);
    ctx.lineTo(x,y);
  }}
  ctx.lineTo(W-P, H-R); ctx.closePath(); ctx.fill();

  // Line
  ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.beginPath();
  for (var i=0; i<vals.length; i++){{
    var x = P+(i/(vals.length-1))*(W-2*P);
    var y = H-R-(maxV?(vals[i]/maxV)*(H-P-R-10):0);
    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // Last dot
  var lx = W-P, ly = H-R-(maxV?(vals[vals.length-1]/maxV)*(H-P-R-10):0);
  ctx.fillStyle = col; ctx.beginPath(); ctx.arc(lx,ly,3,0,Math.PI*2); ctx.fill();

  document.getElementById('chart-detail').innerHTML =
    '<b style="color:'+col+'">'+DOMAIN_LABELS[domain]+' ('+domain+')</b><br>' +
    '近90天合计: <b style="color:#e8b44c">'+(total||0)+'</b> 条<br>'+
    '峰值: <b>'+maxV+'</b>/天 &nbsp; 最新: <b>'+(vals[vals.length-1]||0)+'</b>';
}}

// === Init ===
buildCards();

// Layer groups
var gdeltLayer = L.layerGroup().addTo(map);
var flowLayer = L.layerGroup().addTo(map);

{''.join(gdelt_js)}

{''.join(flow_js)}

// Legend
var legend = L.control({{position:'bottomright'}});
legend.onAdd = function(m){{
  var div = L.DomUtil.create('div','legend');
  div.innerHTML = '<b>UCDP 年度死亡</b><br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#B71C1C;margin-right:5px"></span>&gt;50K<br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#D32F2F;margin-right:5px"></span>10K-50K<br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#E53935;margin-right:5px"></span>5K-10K<br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#FF7043;margin-right:5px"></span>1K-5K<br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#42A5F5;margin-right:5px"></span>&lt;1K<br>'+
    '<br><b>GDELT 情绪 (48h)</b><br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#2E7D32;margin-right:5px"></span>正向/中性<br>'+
    '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#C62828;margin-right:5px"></span>负向<br>'+
    '<br><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#EF6C00;margin-right:5px"></span>COW 领土丧失';
  return div;
}};
legend.addTo(map);

L.control.layers(null,{{
  'UCDP 冲突圆 (年份)': circleLayer,
  'COW 领土变更线': flowLayer,
  'GDELT 情绪点': gdeltLayer
}},{{position:'topright',collapsed:false}}).addTo(map);

switchDomain('ucdp');
</script>
<div style="position:absolute;bottom:2px;right:4px;z-index:1000;color:rgba(255,255,255,0.3);font-size:9px">边界与数据依据 UCDP/GDELT/COW 规范 | ConStruct Lab</div>
</body></html>'''
    hp = os.path.join(output_dir, 'world_map.html')
    with open(hp, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[map] → {hp}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg', default=DEFAULT_PG)
    ap.add_argument('--output-dir', default=None)
    a = ap.parse_args()
    out_dir = a.output_dir or OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)

    flows = load_cow_territorial()
    print(f'COW territorial flows: {len(flows)}')
    ucdp = load_ucdp_yearly(a.pg)
    print(f'UCDP yearly: {len(ucdp)} countries')
    tones, structural, timeline, density = load_gdelt_all(a.pg)
    print(f'GDELT tones: {len(tones)} | struct: {list(structural.keys())} | density: {len(density)} actors')

    build_outputs(flows, ucdp, tones, structural, timeline, density, out_dir)


if __name__ == '__main__':
    main()
