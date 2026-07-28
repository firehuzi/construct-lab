#!/usr/bin/env python3
"""
ConStruct Engine v5.0 — 真实数据驱动 (PG+Neo4j)
================================================
从 v4.1 升级: 数据源从 JSON 样本换成 PG (events/actors/price_observations)。

四引擎逻辑不变 (interpret_identity / detect_signals / check_consistency / score_sul),
只换数据加载层:
  1. actors     → PG actors 表
  2. del2(macro) → rules baseline (GDP/军费/利率等, 待接 FRED/WB)
  3. del3(signal)→ PG events (GDELT 近 30 天: count/tone/words)
  4. rules      → 保持 JSON (人工策展)

依赖: pip install psycopg2-binary
用法:
  本机: python engine_v5.py USA
  docker: docker exec construct-n8n-runner python3 /data/scripts/../construct-engine/engine_v5.py USA
"""
import os
import sys
import json

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# 主体码表 (替代 PG actors 表, DNA/d1-d4/icc 全在此)
CANONICAL_PATH = os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts')
if CANONICAL_PATH not in sys.path:
    sys.path.insert(0, CANONICAL_PATH)
import canonical_actors as CA

import psycopg2
from engine import (
    interpret_identity, detect_signals, check_consistency, score_sul, CustomEncoder,
)
from datetime import datetime

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'

# ===== 新数据加载层 =====

def load_actors():
    """从 canonical_actors.py 读主体 DNA (替代 JSON/PG actors 表)。"""
    actors = {}
    for code, a in CA.CANONICAL_ACTORS.items():
        actors[code] = {
            "code": code, "name": a["name"],
            "dna": {"d1": a.get("d1",""), "d2": a.get("d2",""),
                    "d3": a.get("d3",""), "d4": a.get("d4",""),
                    "icc": a.get("icc","")},
            "config": a.get("config",""),
        }
    return actors


def load_rules(code):
    """保持 JSON 规则文件 (人工策展, 不自动生成)。"""
    rules_path = os.path.join(BASE, "rules", f"{code}.json")
    if not os.path.exists(rules_path):
        return {}
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_del_from_pg(pg_dsn, code, rules):
    """从 PG 实时计算事件级 DEL + macro 指标 fallback 到 rules baseline。

    返回原 engine 兼容格式: {'del2': {param: value, ...}, 'del3': {...}}
    """
    conn = psycopg2.connect(pg_dsn)
    cur = conn.cursor()

    # ---- DEL 3: 事件级 (GDELT 近 30 天) ----
    cur.execute("""
        SELECT count(*), COALESCE(AVG(avg_tone), 0),
               COALESCE(string_agg(DISTINCT action, '|'), '')
        FROM events
        WHERE source='GDELT' AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - INTERVAL '30 days'
    """, (code, code))
    ecnt, tone, actions = cur.fetchone()

    # 从 action 码提取 GDELT 信号词
    gdelt_keywords = {
        '010': 'statement', '020': 'appeal', '030': 'cooperate', '040': 'consult',
        '050': 'diplomacy', '060': 'cooperate', '100': 'demand', '110': 'protest',
        '120': 'reject', '130': 'threaten', '140': 'protest', '150': 'force',
        '160': 'reduce', '170': 'coerce', '180': 'assault', '190': 'fight',
        '200': 'violence',
    }
    words = []
    if actions:
        seen = set()
        for act in actions.split('|'):
            kw = gdelt_keywords.get(act, act)
            if kw not in seen:
                words.append(kw); seen.add(kw)

    del3 = {
        "event_count": ecnt or 0,
        "avg_tone": round(tone or 0, 2),
        "threshold": 50,
        "signal_words": words[:10],
    }

    # ---- DEL 2: macro 指标 fallback 到 rules baseline ----
    del2 = {}
    translations = rules.get("del_translations", {})
    for param, rule in translations.items():
        del2[param] = rule.get("baseline", 0)

    # 尝试从 price_observations 覆盖油价
    if "oil_price" in translations:
        cur.execute("""
            SELECT value FROM price_observations
            WHERE symbol='CRUDE_OIL' ORDER BY time DESC LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            del2["oil_price"] = row[0]

    cur.close(); conn.close()
    return {"del2": del2, "del3": del3, "last_run": datetime.now().isoformat()}


# ===== 运行 =====

def run_engine_v5(subject_code, pg_dsn=DEFAULT_PG):
    """用 PG 真实数据驱动四引擎, 对单个主体跑诊断。"""
    actors = load_actors()
    rules = load_rules(subject_code)

    if not actors:
        return {"status": "error", "message": "No actor data from canonical_actors"}
    if not rules:
        return {"status": "error", "message": f"No rules file for {subject_code} (rules/{subject_code}.json)"}

    actor = actors.get(subject_code)
    if not actor:
        return {"status": "error", "message": f"Unknown code '{subject_code}'"}

    del_data = load_del_from_pg(pg_dsn, subject_code, rules)

    sys.stdout.write(f"[EngV5] {subject_code} ({actor['name']}) | DEL events={del_data['del3']['event_count']} tone={del_data['del3']['avg_tone']}\n")

    identity = interpret_identity(subject_code, actor, del_data.get("del2", {}))
    signals = detect_signals(subject_code, identity, del_data)
    consistency = check_consistency(subject_code, identity, signals)
    sul = score_sul(subject_code, identity, signals, consistency)

    result = {
        "timestamp": datetime.now().isoformat(),
        "subject": subject_code,
        "name": actor["name"],
        "del_summary": {
            "event_count_30d": del_data["del3"]["event_count"],
            "avg_tone_30d": del_data["del3"]["avg_tone"],
            "signal_words": del_data["del3"]["signal_words"],
            "macro_baseline": {k: v for k, v in del_data["del2"].items()},
        },
        "identity": identity,
        "signals": signals,
        "consistency": consistency,
        "sul": sul,
    }

    output_path = os.path.join(BASE, "data", f"engine_v5_{subject_code}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, cls=CustomEncoder)

    sys.stdout.write(f"[EngV5] Output → {output_path}\n")
    return result


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "USA"
    pg = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PG
    result = run_engine_v5(code, pg)
    # 简洁打印关键结果
    if result.get("status") != "error":
        ident = result["identity"]
        cons = result["consistency"]
        sul = result["sul"]
        print(f"\n=== {code} 诊断 ===")
        print(f"Identity params: {len(ident.get('params', {}))}")
        for k, v in ident.get("params", {}).items():
            print(f"  {k}: {v['value']} {v['direction']} ({v.get('change_pct', '?')}%)")
        print(f"Signals detected: {len(result['signals'])}")
        for s in result["signals"]:
            print(f"  [{s['severity']}] {s['description']}")
        print(f"Consistency: {cons['consistency']} ({cons['diagnosis']})")
        print(f"SUL: intent={sul['intent']:.2f} capability={sul['capability']:.2f} exec={sul['execution']:.2f} react={sul['reaction']:.2f} opaque={sul['opaque']:.2f} | confidence={sul['confidence']:.2f}")
