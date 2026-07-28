#!/usr/bin/env python3
"""
ConStruct — 结构矛盾检测器
============================
对 feedback_rules.json 中每个主体的 verification_items 进行 GDELT 行为对照。
检测到矛盾信号 → 降低该假设置信度 → 累积达到阈值 → 推入人工复核队列。
输出到 stdout (n8n Executions 可见) + 更新 feedback_rules.json 的 confidence_delta。
"""

import os, sys, json, argparse
from datetime import datetime, timedelta
import psycopg2

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feedback_rules.json')


def query(db, q, params=None):
    cur = db.cursor()
    cur.execute(q, params or ())
    rows = cur.fetchall()
    cur.close()
    return rows


def detect_contradictions(pg_dsn, dry_run=False):
    db = psycopg2.connect(pg_dsn)
    with open(RULES_FILE, encoding='utf-8') as f:
        rules = json.load(f)

    thresholds = rules['meta']['contradiction_thresholds']
    contradictions = []

    for code, hyp in rules.get('hypotheses', {}).items():
        for item in hyp.get('verification_items', []):
            gd = item.get('gdelt_check', {})
            q = gd.get('query', '')
            contrary = item.get('contrary_signal', '')

            # CHN-1: BRI expansion check — actor CHN + cooperation/diplomacy events 30d trend
            if item['id'] == 'CHN-1':
                rows = query(db, """
                    SELECT AVG(avg_tone), COUNT(*) FROM events
                    WHERE source='GDELT' AND actor1_code='CHN'
                    AND action >= '010' AND action < '070'
                    AND time >= NOW() - INTERVAL '30 days'
                """)
                tone, cnt = rows[0] if rows else (0, 0)
                tone = float(tone or 0); cnt = int(cnt or 0)
                if cnt >= thresholds['min_events_for_check'] and tone < -1:
                    contradictions.append({
                        'code': code, 'item_id': item['id'],
                        'item': item['item'],
                        'evidence': f'CHN 合作/外交类事件 30d tone={tone:.2f} < -1 (预期≥0)',
                        'signal': 'contrary',
                        'confidence_delta': -0.15,
                        'detected_at': datetime.now().isoformat(),
                    })

            # CHN-3: global governance — diplomacy events count trend
            if item['id'] == 'CHN-3':
                rows_30d = query(db, """
                    SELECT COUNT(*) FROM events
                    WHERE source='GDELT' AND (actor1_code='CHN' OR actor2_code='CHN')
                    AND action BETWEEN '040' AND '070'
                    AND time >= NOW() - INTERVAL '30 days'
                """)
                rows_60d = query(db, """
                    SELECT COUNT(*) FROM events
                    WHERE source='GDELT' AND (actor1_code='CHN' OR actor2_code='CHN')
                    AND action BETWEEN '040' AND '070'
                    AND time >= NOW() - INTERVAL '60 days' AND time < NOW() - INTERVAL '30 days'
                """)
                cnt_30 = int(rows_30d[0][0] if rows_30d else 0)
                cnt_60 = int(rows_60d[0][0] if rows_60d else 0)
                if cnt_60 > thresholds['min_events_for_check'] and cnt_30 < cnt_60 * 0.7:
                    contradictions.append({
                        'code': code, 'item_id': item['id'],
                        'item': item['item'],
                        'evidence': f'外交/合作事件 30d={cnt_30} vs 前30d={cnt_60} (下降>{30 if cnt_60 else 0}%)',
                        'signal': 'contrary',
                        'confidence_delta': -0.10,
                        'detected_at': datetime.now().isoformat(),
                    })

            # CHN-5: CHN-USA pair tone after positive diplomacy
            if item['id'] == 'CHN-5':
                rows = query(db, """
                    SELECT AVG(avg_tone), COUNT(*) FROM events
                    WHERE source='GDELT' AND actor1_code='CHN'
                    AND (action BETWEEN '030' AND '060')
                    AND time >= NOW() - INTERVAL '14 days'
                """)
                tone, cnt = rows[0] if rows else (0, 0)
                tone = float(tone or 0); cnt = int(cnt or 0)
                if cnt >= 10 and tone < -2:
                    contradictions.append({
                        'code': code, 'item_id': item['id'],
                        'item': item['item'],
                        'evidence': f'CHN 积极外交事件后 14d 全局 tone={tone:.2f} 仍<-2 (预期无下降)',
                        'signal': 'contrary',
                        'confidence_delta': -0.10,
                        'detected_at': datetime.now().isoformat(),
                    })

        # 累积 confidence_delta
        total_delta = sum(c['confidence_delta'] for c in contradictions if c['code'] == code)
        if total_delta != 0:
            hyp['confidence_delta'] = round(hyp.get('confidence_delta', 0) + total_delta, 2)
            hyp['counter_evidence'] = [c for c in contradictions if c['code'] == code]

    # --- GDELT bias: density anomalies (Tier 2 of gdelt_bias_signals) ---
    try:
        cur = db.cursor()
        cur.execute("SELECT actor_code, coverage_density FROM source_weights")
        densities = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        # resolve names from canonical
        import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'construct-stack', 'scripts'))
        try: import canonical_actors as CA
        except: CA = None
        for code in densities:
            d = densities[code]
            name = CA.CANONICAL_ACTORS[code]['name'] if CA and code in CA.CANONICAL_ACTORS else code
            if d > 5.0:
                contradictions.append({
                    'code': code, 'item_id': 'BIAS-002',
                    'item': 'GDELT过度覆盖',
                    'evidence': f'{name}({code}) density={d:.2f} > 5.0 — 西方媒体框架偏差风险高',
                    'signal': 'bias_over_covered', 'confidence_delta': 0,
                    'detected_at': datetime.now().isoformat(),
                })
            elif d < 0.3:
                contradictions.append({
                    'code': code, 'item_id': 'BIAS-001',
                    'item': 'GDELT覆盖稀疏',
                    'evidence': f'{name}({code}) density={d:.2f} < 0.3 — GDELT对该主体几乎"看不见"',
                    'signal': 'bias_low_density', 'confidence_delta': 0,
                    'detected_at': datetime.now().isoformat(),
                })
    except Exception:
        pass  # source_weights not yet available
    review_triggers = []
    for code, hyp in rules.get('hypotheses', {}).items():
        delta = hyp.get('confidence_delta', 0)
        if delta <= thresholds['confidence_delta_trigger']:
            review_triggers.append({
                'code': code,
                'identity': hyp.get('identity', ''),
                'confidence_delta': delta,
                'new_confidence': round(hyp['confidence'] + delta, 2),
                'action': '人工复核 — 结构假设置信度累计下降超阈值',
            })
            hyp['confidence_delta'] = 0  # reset after trigger

    # 输出
    if contradictions:
        print(f'[STRUCT] {len(contradictions)} 条矛盾信号:')
        for c in contradictions:
            print(f'  [{c["item_id"]}] {c["item"]} — {c["evidence"]}')
            if not dry_run:
                rules.setdefault('contradiction_log', []).append(c)
    else:
        print('[STRUCT] 无矛盾信号')

    if review_triggers:
        print(f'\n[STRUCT] {len(review_triggers)} 条结构复核触发:')
        for r in review_triggers:
            print(f'  ⚠️  {r["code"]} ({r["identity"]}): 置信度 {r["confidence_delta"]:+.2f} → {r["new_confidence"]}')
        dest = os.path.join(os.path.dirname(RULES_FILE), 'cache', 'structure_review_queue.json')
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not dry_run:
            with open(dest, 'w', encoding='utf-8') as f:
                json.dump(review_triggers, f, ensure_ascii=False, indent=2)
            print(f'[STRUCT] 复核队列 → {dest}')

    if not dry_run:
        with open(RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

    db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg', default=DEFAULT_PG)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    detect_contradictions(a.pg, a.dry_run)


if __name__ == '__main__':
    main()
