#!/usr/bin/env python3
"""
ConStruct Lab — 事件快评自动化
================================
GDELT 异常检测 → DeepSeek 生成快评 → 审计队列
用法: python quick_take_autopilot.py --mode full
状态: 待接通 PG 真数据 + n8n 日程
"""

import os, json, argparse, logging
from datetime import datetime
import psycopg2
import urllib.request, urllib.error

PG_DSN = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'

AUDIT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'audit_queue', 'review')

ANOMALY_TONE = 3.0    # Goldstein 绝对值 > 3 = 异常
ANOMALY_SPIKE = 2.0   # 事件数 > 2倍日均 = 异常
MIN_EVENTS = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('quick_take')


def fetch_gdelt(hours=48):
    """"从 PG 拉最近N小时 GDELT, 返回 actor 级别汇总"""
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT e.actor1_code, COUNT(*) as cnt, AVG(e.avg_tone) as tone,
               MAX(e.time) as latest, STRING_AGG(DISTINCT e.actor2_code, ',') as opps,
               STRING_AGG(DISTINCT e.action, ',') as actions,
               COALESCE(w.coverage_density, 0) as density
        FROM events e
        LEFT JOIN source_weights w ON e.actor1_code = w.actor_code
        WHERE e.source='GDELT' AND e.time >= NOW() - INTERVAL '%s hours'
        AND e.actor1_code IS NOT NULL
        GROUP BY e.actor1_code, w.coverage_density HAVING COUNT(*) >= %s
        ORDER BY cnt DESC
    """ % (hours, MIN_EVENTS))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{'actor': r[0], 'cnt': r[1], 'tone': round(r[2] or 0, 2),
             'latest': str(r[3]), 'opps': r[4] or '', 'actions': r[5] or '',
             'density': round(r[6] or 0, 2)} for r in rows]


def detect_anomalies(rows):
    """检测异常: tone 极端 or 事件暴增"""
    anomalies = []
    for r in rows:
        tone = abs(r['tone'])
        if tone > ANOMALY_TONE:
            anomalies.append({**r, 'type': 'tone_spike', 'reason': f'情绪极端: {r["tone"]}'})
    return anomalies[:3]  # 每日最多 3 条


def generate(anomaly):
    # 追加 coverage_density
    dens = ''
    try:
        conn2 = psycopg2.connect(PG_DSN)
        cur2 = conn2.cursor()
        cur2.execute("SELECT coverage_density FROM source_weights WHERE actor_code=%s", (anomaly['actor'],))
        row = cur2.fetchone()
        if row: dens = f' {row[0]:.2f}'
        cur2.close(); conn2.close()
    except: pass

    prompt = f"""你是一个 ConStruct Lab 的结构分析员。根据以下 GDELT 异常信号生成一篇 500-800 字事件快评。

【异常信号】
- 主体: {anomaly['actor']}
- 48h 事件数: {anomaly['cnt']}
- 平均情绪: {anomaly['tone']}
- GDELT 覆盖密度: {anomaly.get('density', dens)}
- 对手/伙伴: {anomaly['opps']}
- 行动类型: {anomaly['actions']}

请按以下结构输出（Markdown）：
## [标题：一句话概括 + 结构判断]

### 1. 事件事实（1-2句）

### 2. 结构锚定（3-5句：触发哪个主体的 Identity/Method/Fear）

### 3. 历史参照（2-3句：COW/UCDP 有无类似先例）

### 4. 走向判断（1-2句）

### 5. 反洗脑提示（1句）

### 6. 我们不知道什么（1-2句: 本分析遗漏的因素——GDELT西方中心偏差/秘密外交/不可观测行为）

注意：不模糊词, 每个判断锚定在数据上, 不足时标注置信度。"""

    data = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'system', 'content': '你是结构驱动的分析员。'},
                      {'role': 'user', 'content': prompt}],
        'temperature': 0.3, 'max_tokens': 2000,
    }).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {DEEPSEEK_API_KEY}')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        return resp['choices'][0]['message']['content']
    except Exception as e:
        return f'# 生成失败\n\n{e}'


def save(content, anomaly):
    os.makedirs(AUDIT_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(AUDIT_DIR, f'quick_take_{anomaly["actor"]}_{ts}.md')
    header = f"""---
generated_at: {datetime.now().isoformat()}
actor: {anomaly['actor']}
tone: {anomaly['tone']}
status: pending_review
---
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + content)
    logger.info(f'[quick_take] → {path}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['detect','full'], default='full')
    a = ap.parse_args()

    if not DEEPSEEK_API_KEY:
        logger.error('DEEPSEEK_API_KEY not set')
        return

    rows = fetch_gdelt()
    logger.info(f'Fetched {len(rows)} actors')
    anomalies = detect_anomalies(rows)

    if not anomalies:
        logger.info('No anomalies')
        return

    if a.mode == 'detect':
        for an in anomalies:
            logger.info(f'  [{an["actor"]}] {an["reason"]}')
        return

    for an in anomalies:
        logger.info(f'Generating: [{an["actor"]}] {an["reason"]}')
        content = generate(an)
        save(content, an)


if __name__ == '__main__':
    main()
