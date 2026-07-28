#!/usr/bin/env python3
"""
ConStruct — 双模交互时间轴 (vis.js + TimelineJS)
===================================================
从 PG + actor_timelines 生成两个独立 HTML:
  {code}_skeleton.html  — vis.js Timeline, 全景骨架 (可缩放, 点+区间事件)
  {code}_narrative.html — TimelineJS, 精选叙事 (20-25 关键节点)

零服务器依赖, CDN 加载 JS 库, 双击即开。

依赖: psycopg2-binary (仅数据加载)
用法: python visualize_interactive.py CHN
"""
import os, sys, json, argparse
from datetime import datetime

import psycopg2

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts'))
import canonical_actors as CA

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
OUTPUT_DIR = os.path.join(BASE, 'visuals')
TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')


# ===== 数据加载 (同 visualize_three_layers.py) =====

def load_gdelt(conn, code, days=30):
    cur = conn.cursor()
    cur.execute("""
        SELECT time::date, count(*), COALESCE(AVG(avg_tone),0)
        FROM events WHERE source='GDELT'
        AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - interval '%s days'
        GROUP BY time::date ORDER BY time::date DESC
    """, (code, code, days))
    rows = cur.fetchall(); cur.close()
    return rows

def load_ucdp(conn, code, cname):
    cur = conn.cursor()
    cur.execute("""
        SELECT EXTRACT(YEAR FROM time)::int, count(*),
               COALESCE(SUM((metadata->>'deaths_best')::int), 0)
        FROM events WHERE source='UCDP' AND location ILIKE %s
        GROUP BY 1 ORDER BY 1 DESC
    """, (cname + '%',))
    rows = cur.fetchall(); cur.close()
    return rows

def load_cow(code):
    path = os.path.join(TIMELINE_DIR, f'{code}.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f).get('skeleton_cow', [])


# ===== vis.js Timeline: 全景骨架 =====

VIS_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ConStruct Skeleton — {cname} ({code})</title>
<script src="https://unpkg.com/vis-data@7/peer/umd/vis-data.min.js"></script>
<script src="https://unpkg.com/vis-timeline@7/standalone/umd/vis-timeline-graph2d.min.js"></script>
<link href="https://unpkg.com/vis-timeline@7/styles/vis-timeline-graph2d.min.css" rel="stylesheet" />
<style>
  html, body {{ margin:0; padding:0; font-family: 'Microsoft YaHei', sans-serif; background:#0f131e; color:#d0d4e0; }}

  h1 {{ text-align:center; padding:16px 0 4px; font-size:22px; color:#e8b44c; }}

  .toolbar {{ text-align:center; padding:4px 0 12px; font-size:13px; color:#6a7088; }}
  .toolbar span {{ margin:0 12px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:10px; margin:0 3px; font-size:11px; }}
  .badge-war {{ background:#E53935; color:#fff; }}
  .badge-mid {{ background:#42A5F5; color:#fff; }}
  .badge-ally {{ background:#43A047; color:#fff; }}
  .badge-terr-l {{ background:#EF6C00; color:#fff; }}
  .badge-terr-g {{ background:#8E24AA; color:#fff; }}
  .badge-gdelt {{ background:#C62828; color:#fff; }}
  .badge-ucdp {{ background:#D32F2F; color:#fff; }}

  /* 三层容器: 顶层 GDELT (2em) / 中层 UCDP (3em) / 底层 COW (rest) */
  #gdelt {{ height:100px; margin:0 16px 8px; border:1px solid #2a3040; border-radius:6px; }}
  #ucdp {{ height:140px; margin:0 16px 8px; border:1px solid #2a3040; border-radius:6px; }}
  #cow {{ height:calc(100vh - 380px); margin:0 16px; border:1px solid #2a3040; border-radius:6px; }}

  .mirror {{ margin:12px 16px; padding:10px 16px; background:#1a1520; border-left:3px solid #e8b44c; border-radius:4px; font-size:13px; }}
  .mirror b {{ color:#e8b44c; }}
</style>
</head>
<body>
<h1>ConStruct 认知锚定 — {cname} ({code})</h1>
<div class="toolbar">
  <span><span class="badge badge-gdelt">GDELT</span> 近30天情绪脉冲</span>
  <span><span class="badge badge-ucdp">UCDP</span> 1989–2025 冲突</span>
  <span><span class="badge badge-war">WAR</span> <span class="badge badge-mid">MID</span> <span class="badge badge-ally">ALLIANCE</span> <span class="badge badge-terr-l">TERR−</span> <span class="badge badge-terr-g">TERR+</span> COW 200年骨架</span>
</div>

<div id="gdelt"></div>
<div id="ucdp"></div>
<div class="mirror">{mirror}</div>
<div id="cow"></div>

<script>
var gdelt = {gdelt_json};
var ucdp = {ucdp_json};
var cow = {cow_json};

// GDELT: 近30天情绪柱
new vis.Timeline(document.getElementById('gdelt'), gdelt, {{
  start: new Date(Date.now() - 30*24*3600*1000), end: new Date(),
  zoomMax: 1000*3600*24*7, height:'100px', showCurrentTime:false,
  tooltip: {{followMouse:true, template:function(item){{return item.content;}}}}
}});

// UCDP: 年度冲突
new vis.Timeline(document.getElementById('ucdp'), ucdp, {{
  min: new Date('1989-01-01'), max: new Date('2027-01-01'),
  zoomMin: 1000*3600*24*365, height:'140px', showCurrentTime:false,
  tooltip: {{followMouse:true, template:function(item){{return item.content;}}}}
}});

// COW: 200年骨架
var cowOptions = {{
  min: new Date('1800-01-01'), max: new Date('2030-01-01'),
  zoomMin: 1000*3600*24*365, height:'100%', showCurrentTime:false,
  groupOrder: function(a,b) {{ return a.id - b.id; }},
  tooltip: {{followMouse:true, template:function(item){{return item.content;}}}}
}};
new vis.Timeline(document.getElementById('cow'), cow, undefined, cowOptions);
</script>
</body>
</html>'''


def build_vis(cow_events, ucdp_data, gdelt_data, mirror_text):
    items_gdelt, items_ucdp, items_cow = [], [], []
    gid = uid = cid = 0

    for date, cnt, tone in (gdelt_data or []):
        gid += 1
        color = '#2E7D32' if tone >= 0 else '#C62828'
        items_gdelt.append({'id': gid, 'content': f'{cnt}条', 'start': str(date),
            'title': f'{str(date)}: {cnt}事件, Goldstein={tone}',
            'style': f'background-color:{color}'})

    type_colors = {'state-based': '#D32F2F', 'non-state': '#E67E22', 'one-sided': '#7B1FA2'}
    for yr, cnt, deaths in (ucdp_data or []):
        uid += 1
        evtype = 'state-based'  # default
        items_ucdp.append({'id': uid, 'content': f'<div style="font-size:11px">deaths:{deaths:,}</div>',
            'start': f'{yr}-06-01', 'end': f'{yr}-12-31', 'title': f'{yr}: {cnt}事件, {deaths}死亡'})

    groups_cow = [
        {'id': 1, 'content': 'WAR<span style="font-size:10px;color:#999"> (战争)</span>'},
        {'id': 2, 'content': 'MID<span style="font-size:10px;color:#999"> (争端)</span>'},
        {'id': 3, 'content': 'ALLIANCE<span style="font-size:10px;color:#999"> (同盟)</span>'},
        {'id': 4, 'content': 'TERR−<span style="font-size:10px;color:#999"> (领土丧失)</span>'},
        {'id': 5, 'content': 'TERR+<span style="font-size:10px;color:#999"> (领土获得)</span>'},
    ]
    group_map = {'WAR': 1, 'MID': 2, 'ALLIANCE': 3, 'TERR_LOSS': 4, 'TERR_GAIN': 5}
    type_bg = {1: '#E53935', 2: '#42A5F5', 3: '#43A047', 4: '#EF6C00', 5: '#8E24AA'}

    for ev in cow_events:
        cid += 1
        g = group_map.get(ev['type'], 2)
        sy = ev['year_start']; ey = ev.get('year_end', sy)
        label = ev.get('label', '') or ev.get('entity', '') or ev.get('with', '')
        opp = ev.get('from', ev.get('to', ''))
        title = f"{ev['type']} | {label}"
        if opp: title += f" | {opp}"
        h = ev.get('hostility', '')
        if h: title += f" | hostility={h}"
        if label: label = label[:30]
        items_cow.append({'id': cid, 'group': g, 'content': label or ev['type'],
            'start': f'{sy}-06-15', 'end': f'{ey}-06-15',
            'title': title, 'style': f'background-color:{type_bg.get(g,"#999")}'})

    gdelt_json = json.dumps(items_gdelt, ensure_ascii=False)
    ucdp_json = json.dumps(items_ucdp, ensure_ascii=False)
    cow_json = json.dumps(json.dumps(items_cow, ensure_ascii=False))  # double-encode for JS
    groups_json = json.dumps(groups_cow, ensure_ascii=False)

    # For vis.js data needs groups:
    html = VIS_HTML.replace('{gdelt_json}', gdelt_json).replace('{ucdp_json}', ucdp_json)
    html = html.replace('{mirror}', mirror_text)
    # Inject cow data as DataSet with groups
    html = html.replace('{cow_json}', f'new vis.DataSet({cow_json})')
    # Fix: need groups in third timeline
    html = html.replace("new vis.Timeline(document.getElementById('cow'), cow, undefined, cowOptions)",
        f"new vis.Timeline(document.getElementById('cow'), cow, new vis.DataSet({groups_json}), cowOptions)")
    return html


# ===== TimelineJS: 精选叙事 =====

TJS_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ConStruct Narrative — {cname} ({code})</title>
<link title="timeline-styles" rel="stylesheet" href="https://cdn.knightlab.com/libs/timeline3/latest/css/timeline.css">
<style>
  html, body {{ margin:0; padding:0; background:#0f131e; }}
  #timeline-embed {{ width:100%; height:100vh; }}
</style>
</head>
<body>
<div id="timeline-embed"></div>
<script src="https://cdn.knightlab.com/libs/timeline3/latest/js/timeline.js"></script>
<script>
var timeline_json = {timeline_json};
window.timeline = new TL.Timeline('timeline-embed', timeline_json);
</script>
</body>
</html>'''


def pick_narrative(cow_events, code, cname, max_events=25):
    """从 COW 骨架中选最多 max_events 个关键叙事节点"""
    # 优先级: WAR > TERR_LOSS > ALLIANCE > TERR_GAIN > MID (按 hostility 排)
    wars = [e for e in cow_events if e['type'] == 'WAR']
    losses = [e for e in cow_events if e['type'] == 'TERR_LOSS']
    alliances = [e for e in cow_events if e['type'] == 'ALLIANCE']
    gains = [e for e in cow_events if e['type'] == 'TERR_GAIN']
    mids = sorted([e for e in cow_events if e['type'] == 'MID'],
                  key=lambda e: len(e.get('hostility', '')), reverse=True)

    picked = wars + losses + alliances + gains
    remaining = max_events - len(picked)
    if remaining > 0:
        picked += mids[:remaining]
    picked.sort(key=lambda e: e['year_start'])
    return picked[:max_events]


def build_timelinejs(cow_events, code, cname):
    picked = pick_narrative(cow_events, code, cname)
    slides = [{
        'start_date': {'year': e['year_start'], 'month': 6, 'day': 15},
        'end_date': {'year': e.get('year_end', e['year_start']), 'month': 6, 'day': 15},
        'text': {
            'headline': f"{e['type']}: {e.get('label','') or e.get('entity','') or '—'}",
            'text': e.get('hostility','') or e.get('source','')
        },
        'group': e['type'],
    } for e in picked]

    timeline = {
        'title': {'text': {'headline': f'{cname} ({code}) 历史叙事', 'text': '数据源: COW MID+War+Alliance+Territorial | 精选关键节点'}},
        'events': slides
    }
    html = TJS_HTML.replace('{timeline_json}', json.dumps(timeline, ensure_ascii=False))
    return html


# ===== 主流程 =====

def main():
    ap = argparse.ArgumentParser(description='ConStruct dual interactive timeline')
    ap.add_argument('code', nargs='?', default='CHN')
    ap.add_argument('--pg', default=DEFAULT_PG)
    a = ap.parse_args()

    code = a.code
    cname = CA.CANONICAL_ACTORS.get(code, {}).get('name', code)
    conn = psycopg2.connect(a.pg)
    gdelt_data = load_gdelt(conn, code)
    ucdp_data = load_ucdp(conn, code, cname)
    conn.close()
    cow_events = load_cow(code)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Mirror text
    losses = [e for e in cow_events if e['type'] == 'TERR_LOSS']
    wars = [e for e in cow_events if e['type'] == 'WAR']
    mirror = f'<b>照妖镜:</b> 自 {losses[0]["year_start"] if losses else "?"} 年起 {len(losses)} 次领土变更 | {len(wars)} 次国家间战争 | ' + \
             f'GDELT {len(gdelt_data)} 天 {sum(d[1] for d in gdelt_data)} 事件 | UCDP {sum(d[1] for d in ucdp_data):,} 冲突事件'

    # vis.js skeleton
    html_vis = build_vis(cow_events, ucdp_data, gdelt_data, mirror)
    html_vis = html_vis.replace('{code}', code).replace('{cname}', cname)
    vis_path = os.path.join(OUTPUT_DIR, f'{code}_skeleton.html')
    with open(vis_path, 'w', encoding='utf-8') as f:
        f.write(html_vis)
    print(f'[viz] vis.js skeleton -> {vis_path} ({len(cow_events)} COW + {len(ucdp_data)} UCDP + {len(gdelt_data)} GDELT)')

    # TimelineJS narrative
    html_tjs = build_timelinejs(cow_events, code, cname)
    html_tjs = html_tjs.replace('{code}', code).replace('{cname}', cname)
    tjs_path = os.path.join(OUTPUT_DIR, f'{code}_narrative.html')
    with open(tjs_path, 'w', encoding='utf-8') as f:
        f.write(html_tjs)
    narr_count = min(len(cow_events), 25)
    print(f'[viz] TimelineJS narrative -> {tjs_path} (精选 {narr_count} 关键节点)')


if __name__ == '__main__':
    main()
