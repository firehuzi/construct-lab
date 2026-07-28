#!/usr/bin/env python3
"""
ConStruct — 主体历史底座构建器
=================================
从 PG events (UCDP 1989–2025 + GDELT 近 30 天) 自动生成
每主体的"近现代层"时间线 JSON。远代骨架和阐释由人策展。

输出: actor_timelines/{code}.json

依赖: pip install psycopg2-binary
用法:
  python build_actor_timeline.py
  python build_actor_timeline.py --country-code CHN
"""
import os
import sys
import json
import argparse
from collections import defaultdict, Counter
from datetime import datetime

# metadata JSONB → psycopg2 自动解为 dict, 无需 json.loads
def _meta_val(meta, key, default=None):
    if isinstance(meta, dict):
        return meta.get(key, default)
    if isinstance(meta, str):
        try:
            return json.loads(meta).get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default
    return default

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 引入 canonical_actors 做 code↔name 映射
CA_PATH = os.path.join(os.path.dirname(BASE_DIR), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, CA_PATH)
import canonical_actors as CA

import psycopg2

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
OUTPUT_DIR = os.path.join(BASE_DIR, 'actor_timelines')

# UCDP type_of_violence 摘要 (从 metadata JSONB 取)
VIOLENCE_MAP = {'1': 'state-based', '2': 'non-state', '3': 'one-sided'}

# ===== 时期切割 (数据驱动) =====

def detect_period_boundaries(yearly):
    """年度事件数序列 → 时期边界年份列表。
    突变点: 年事件数变化率 > 3x 且事件数 ≥ 30 (过滤微量波动, 避免切太碎)。"""
    years = sorted(yearly.keys())
    if len(years) < 3:
        return [min(years)] if years else []
    boundaries = [years[0]]
    prev_cnt = yearly.get(years[0], 0)
    for i in range(1, len(years)):
        y = years[i]
        cnt = yearly.get(y, 0)
        if prev_cnt > 0 and cnt > 0:
            ratio = max(cnt / prev_cnt, prev_cnt / cnt)
            if ratio > 3.0 and max(cnt, prev_cnt) >= 30:
                boundaries.append(y)
        prev_cnt = cnt
    return boundaries


def build_timeline(events_ucdp, code, actor_name):
    """UCDP 事件列表 → 时期分割 + 每时期摘要。"""
    if not events_ucdp:
        return []

    # 年度聚合
    yearly = Counter()
    for ev in events_ucdp:
        y = ev['year']
        if y:
            yearly[int(y)] += 1
    if not yearly:
        return []

    boundaries = detect_period_boundaries(yearly)
    boundaries.append(max(yearly.keys()) + 1)  # 哨兵

    # 按时期分组
    periods = []
    for i in range(len(boundaries) - 1):
        y_start = boundaries[i]
        y_end = boundaries[i + 1] - 1
        evs = [ev for ev in events_ucdp
               if y_start <= int(ev.get('year', 0)) <= y_end]
        if not evs:
            continue
        etotal = len(evs)
        # 死亡数 (从 metadata JSON 读 deaths_best)
        dtot = 0
        for ev in evs:
            meta = ev.get('metadata')
            if meta:
                dtot += int(_meta_val(meta, 'deaths_best', 0))

        # 冲突类型混合
        vtypes = Counter()
        for ev in evs:
            vt = _meta_val(ev.get('metadata'), 'type_of_violence', '')
            vtypes[VIOLENCE_MAP.get(str(vt), str(vt))] += 1

        # 主要对手 (从 metadata 读 side_a/side_b)
        opponents = Counter()
        for ev in evs:
            md = ev.get('metadata')
            if not md:
                continue
            for side in ['side_a', 'side_b']:
                opp = _meta_val(md, side, '')
                if opp:
                    opp = str(opp)
                    if opp and actor_name not in opp and 'Government' not in opp:
                        opponents[opp] += 1
        top_opponents = [o for o, _ in opponents.most_common(3)]

        # 时期标签 (机器生成, 保守)
        major_type = vtypes.most_common(1)[0][0] if vtypes else 'unknown'
        label = f"{y_start}–{y_end}"
        if dtot > 5000:
            label = f"High-intensity conflict ({major_type})"
        elif etotal > 500:
            label = f"Active conflict ({major_type})"
        elif etotal > 50:
            label = f"Low-intensity ({major_type})"
        else:
            label = f"Sporadic ({major_type})"

        periods.append({
            "start_year": y_start, "end_year": y_end,
            "label": label,
            "events_total": etotal,
            "deaths_total": dtot,
            "top_opponents": top_opponents,
            "conflict_type_mix": dict(vtypes.most_common(3)),
        })

    return periods


# ===== GDELT 近期信号 =====

def recent_gdelt(conn, code):
    cur = conn.cursor()
    cur.execute("""
        SELECT count(*), COALESCE(AVG(avg_tone),0),
               COALESCE(string_agg(DISTINCT action, '|'), '')
        FROM events WHERE source='GDELT'
        AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - INTERVAL '30 days'
    """, (code, code))
    cnt, tone, actions = cur.fetchone()
    cur.close()
    kw_map = {  # GDELT CAMEO → 信号词
        '010': 'statement', '020': 'appeal', '030': 'cooperate',
        '040': 'consult', '050': 'diplomacy', '060': 'cooperate',
        '100': 'demand', '110': 'protest', '120': 'reject',
        '130': 'threaten', '140': 'protest', '150': 'force',
        '160': 'reduce', '170': 'coerce', '180': 'assault',
        '190': 'fight', '200': 'violence',
    }
    words = []
    if actions:
        seen = set()
        for act in actions.split('|'):
            w = kw_map.get(act, act)
            if w not in seen:
                words.append(w); seen.add(w)
    return {
        "events_30d": cnt or 0,
        "avg_tone_30d": round(tone or 0, 2),
        "signal_words": words[:10],
    }


# ===== 主流程 =====

def build_all(pg_dsn, target_code=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = psycopg2.connect(pg_dsn)

    # 加载 UCDP 事件 (全量)
    cur = conn.cursor()
    cur.execute("""
        SELECT time, location, metadata, COALESCE(EXTRACT(YEAR FROM time), 0)::int as year
        FROM events WHERE source='UCDP'
    """)
    ucdp_raw = []
    for t, loc, meta, yr in cur.fetchall():
        ucdp_raw.append({'time': t, 'location': loc, 'metadata': meta, 'year': yr})
    cur.close()
    print(f"[timeline] UCDP events: {len(ucdp_raw)}")

    # canonical 主体 → UCDP country 映射
    targets = {}
    for code, a in CA.CANONICAL_ACTORS.items():
        name = a['name']
        targets[code] = name

    if target_code:
        targets = {target_code: targets.get(target_code, target_code)}

    # 构建 UCDP location 索引: {canonical_code: [ucdp_events]}
    ucdp_by_code = defaultdict(list)
    for ev in ucdp_raw:
        loc = ev['location'] or ''
        for code, cname in targets.items():
            # 前缀模糊匹配 ("Russia" 匹配 "Russia (Soviet Union)")
            if loc.lower().startswith(cname.lower()):
                ucdp_by_code[code].append(ev)
                break

    built = 0
    for code, cname in targets.items():
        ucdp_evs = ucdp_by_code.get(code, [])
        if not ucdp_evs:
            continue
        periods = build_timeline(ucdp_evs, code, cname)
        gdelt = recent_gdelt(conn, code)

        out = {
            "code": code,
            "name": cname,
            "timeline_ucdp": periods,
            "recent_gdelt": gdelt,
            "generated_at": datetime.now().isoformat(),
            "_note": "machine-generated from UCDP GED v26.1 (1989–2025) + GDELT 30d. "
                     "Human-curated layers (skeleton/interpretation) to be added."
        }
        path = os.path.join(OUTPUT_DIR, f"{code}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[timeline] {code} ({cname}): {len(periods)} periods, "
              f"{sum(p['events_total'] for p in periods)} events → {path}")
        built += 1

    conn.close()
    print(f"[timeline] Done. {built} actor timelines written to {OUTPUT_DIR}")


def main():
    ap = argparse.ArgumentParser(description='Build actor timelines from PG UCDP+GDELT')
    ap.add_argument('--pg', default=DEFAULT_PG)
    ap.add_argument('--country-code', default=None)
    a = ap.parse_args()
    build_all(a.pg, a.country_code)


if __name__ == '__main__':
    main()
