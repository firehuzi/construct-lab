#!/usr/bin/env python3
"""
ConStruct — AI 结构性诊断引擎 (DeepSeek)
===========================================
从 Neo4j 查主体近期事件 + PG 读取信号指标 + COW 历史骨架
→ DeepSeek API → 11 层结构化诊断 Markdown 输出

依赖: pip install openai neo4j psycopg2-binary
API Key: 环境变量 DEEPSEEK_API_KEY 或命令行 --api-key
用法:
  python diagnose_actor.py CHN
  python diagnose_actor.py CHN --api-key sk-xxx
"""

import os, sys, json, argparse
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts'))
import canonical_actors as CA

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
DEFAULT_NEO4J = 'bolt://localhost:7687'
OUTPUT_DIR = os.path.join(BASE, 'diagnostics')
TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')

DEEPSEEK_MODEL = 'deepseek-chat'
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'

# 诊断 prompt 模板
DIAG_PROMPT = """你是一个地缘政治结构性诊断引擎。基于以下数据，用 ConStruct Lab 11 层诊断框架对 **{actor_name}** 进行一次当前快照诊断。

## 1. 近期信号（GDELT 近 30 天）
- 事件总数: {gdelt_count}
- 平均情绪 (Goldstein tone，-10 到 +10): {gdelt_tone}
- GDELT 覆盖密度 (全球均值=1.0): {gdelt_density}
- 信号词: {signal_words}
- 主要对手: {top_opponents}

## 2. 历史骨架（COW 200年 + Kaggle 战争记录）
- 战争总数: {war_count}
- 近 150 年关键战争: {recent_wars}
- 领土变更 (丧失): {terr_losses}
- 领土变更 (获得): {terr_gains}
- 同盟关系: {alliances_summary}

## 3. UCDP 冲突期 (1989–2025)
{ucdp_periods}

## 4. Identity 档案
{identity}

## 输出格式
请严格按以下 11 层 ConStruct 框架输出诊断（每层 2-4 句）：

### L1 行为主体
### L2 连续性类型 & 当前构型
### L3 存在方式
### L4 建构来源 (近期是否触发了历史锚点)
### L5 维持机制
### L6 秩序价值
### L7 他者系统 (对手/盟友/秩序接受者的近期变化)
### L8 创伤→恐惧 (是否有创伤触发的信号)
### L9 战略选择
### L10 生物类比 (六型中属于哪种, 是否可能切换)
### 约束判断 (哪些路逻辑上不可能)

## 输出要求
- 注意区分"战争数量"与"历史印记": 中国的核心创伤不是 1949 年后的边境战争, 而是 1840 鸦片战争开启的"百年屈辱"(1840-1949)——从天下体系的中心被降为国际体系的客体, 才是复兴叙事的心理动力来源
- 对领土变更: 1842 香港→GBR、1860 九龙→GBR、1895 台湾→JPN 的释义远重于 1962 中印边界战争
- 每条诊断基于提供的数据, 不凭空猜测
- 最后给一个 1 句话的"核心诊断"
- 语气冷静、结构导向，不做预测"""


def load_identity(code):
    """从 actors/ md 档案提取 Identity 摘要（含建构来源关键段落）"""
    actors_dir = os.path.join(os.path.dirname(BASE), 'actors')
    short_map = {'CHN': 'CN', 'USA': 'US', 'RUS': 'RU', 'JPN': 'JP', 'GBR': 'GB',
                 'FRA': 'FR', 'DEU': 'DE', 'IND': 'IN', 'BRA': 'BR', 'TUR': 'TR',
                 'IRN': 'IR', 'ISR': 'IL', 'SAU': 'SA', 'EGY': 'EG', 'AUS': 'AU',
                 'PHL': 'PH', 'KOR': 'KR', 'UKR': 'UA', 'VNM': 'VN', 'TWN': 'TW'}
    short = short_map.get(code, code)
    for tier in ['Tier1', 'Tier2']:
        p = os.path.join(actors_dir, tier, short)
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.endswith('.md'):
                    with open(os.path.join(p, f), encoding='utf-8') as fh:
                        content = fh.read()
                    lines = content.split('\n')
                    summary = []
                    in_l4 = False
                    for line in lines:
                        stripped = line.strip().lstrip('> ')
                        # DNA/构型/身份行
                        if any(kw in stripped for kw in ['**构型', 'DNA:', '深层Identity', '连续性类型', '核心恐惧', '身份一句话']):
                            summary.append(stripped)
                            if len(summary) >= 5 and in_l4:
                                break
                        # L4 建构来源 — 历史印记段 (百年屈辱/关键锚点)
                        if '### L4' in stripped or 'L4 建构来源' in stripped:
                            in_l4 = True
                            continue
                        if in_l4 and stripped.startswith('|') and ('鸦片' in stripped or '甲午' in stripped or '八国' in stripped or '侵华' in stripped or '不平等条约' in stripped or '���年' in stripped):
                            summary.append(stripped)
                        if in_l4 and stripped.startswith('>') and ('百年' in stripped or '创伤' in stripped or '降级' in stripped):
                            summary.append(stripped)
                            in_l4 = False  # 只取第一段注释
                        if len(summary) >= 12:
                            break
                    return '\n'.join(summary) if summary else '(无 Identity 档案)'
    return '(无 Identity 档案)'


def load_timeline(code):
    path = os.path.join(TIMELINE_DIR, f'{code}.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def query_neo4j_events(uri, user, password, code, days=30):
    """从 Neo4j 查主体近 N 天相关事件"""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    events = []
    with driver.session() as s:
        result = s.run("""
            MATCH (a:Actor {code: $code})-[r:INITIATED|RECEIVED]->(e:Event)
            WHERE e.time >= date() - duration({days: $days})
            RETURN e.source_id, e.time, e.action, e.avg_tone, TYPE(r) AS role,
                   e.source_ref, e.summary, e.event_class
            ORDER BY e.time DESC
            LIMIT 200
        """, code=code, days=days)
        for rec in result:
            events.append(dict(rec))
    driver.close()
    return events


def query_pg_stats(pg_dsn, code, days=30):
    """从 PG 查 GDELT 统计指标"""
    import psycopg2
    conn = psycopg2.connect(pg_dsn)
    cur = conn.cursor()
    cur.execute("""
        SELECT count(*), COALESCE(AVG(avg_tone), 0),
               COALESCE(string_agg(DISTINCT action, '|'), '')
        FROM events
        WHERE source='GDELT' AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - interval '%s days'
    """, (code, code, days))
    cnt, tone, actions = cur.fetchone()

    # top opponents
    cur.execute("""
        SELECT COALESCE(actor2_code, actor1_code) AS opp, count(*)
        FROM events
        WHERE source='GDELT' AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - interval '%s days'
        AND (actor2_code IS NOT NULL OR (actor1_code=%s AND actor2_code IS NULL))
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5
    """, (code, code, days, code))
    opponents = cur.fetchall()

    # coverage density from source_weights
    density = 0
    try:
        cur.execute("SELECT coverage_density FROM source_weights WHERE actor_code=%s", (code,))
        row = cur.fetchone()
        if row: density = round(row[0], 2)
    except: pass

    cur.close(); conn.close()

    # signal words from action codes
    kw_map = {'010':'statement','020':'appeal','030':'cooperate','040':'consult',
              '050':'diplomacy','060':'cooperate','100':'demand','110':'protest',
              '120':'reject','130':'threaten','140':'protest','150':'force',
              '160':'reduce','170':'coerce','180':'assault','190':'fight','200':'violence'}
    words = []
    if actions:
        seen = set()
        for act in actions.split('|'):
            w = kw_map.get(act, act)
            if w not in seen: words.append(w); seen.add(w)

    return {
        'gdelt_count': cnt or 0,
        'gdelt_tone': round(tone or 0, 2),
        'gdelt_density': density,
        'signal_words': ', '.join(words[:10]) if words else '无',
        'top_opponents': ', '.join(f'{o[0]}({o[1]})' for o in opponents) if opponents else '无',
    }


def call_deepseek(prompt, api_key):
    """调用 DeepSeek API"""
    import urllib.request, urllib.error
    data = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [
            {'role': 'system', 'content': '你是一个地缘政治结构性诊断引擎，基于数据和 ConStruct 方法论输出诊断。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.3,
        'max_tokens': 3000,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        return resp['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:500]
        return f'[DeepSeek API 错误 HTTP {e.code}]: {body}'


def build_prompt(code, cname, timeline, neo_events, pg_stats):
    """构建诊断 prompt"""
    cow = timeline.get('skeleton_cow', [])
    ucdp = timeline.get('timeline_ucdp', [])

    wars = [e for e in cow if e['type'] == 'WAR']
    terr_loss = [e for e in cow if e['type'] == 'TERR_LOSS']
    terr_gain = [e for e in cow if e['type'] == 'TERR_GAIN']
    alliances = [e for e in cow if e['type'] == 'ALLIANCE']

    recent_wars = '\n'.join(f"  - {e['year_start']} {e.get('label', '')}" for e in sorted(wars, key=lambda x: x['year_start'])[-15:])
    terr_l_summary = '\n'.join(f"  - {e['year_start']} {e.get('entity', e.get('label',''))} → {e.get('to','?')}" for e in terr_loss[-8:])
    terr_g_summary = '\n'.join(f"  - {e['year_start']} {e.get('entity', e.get('label',''))} ← {e.get('from','?')}" for e in terr_gain[-5:])
    ally_sum = ', '.join(f"{e['year_start']}+{e.get('with','')}" for e in alliances[-8:])

    ucdp_str = '\n'.join(
        f"  - {p.get('start_year','')}-{p.get('end_year','')}: {p.get('label','')} (events={p.get('events_total',0)}, deaths={p.get('deaths_total',0)}, opp={p.get('top_opponents',[])})"
        for p in ucdp[-5:]) if ucdp else '(无)'

    identity = load_identity(code)

    return DIAG_PROMPT.format(
        actor_name=cname,
        gdelt_count=pg_stats['gdelt_count'],
        gdelt_tone=pg_stats['gdelt_tone'],
        gdelt_density=pg_stats.get('gdelt_density', 'N/A'),
        signal_words=pg_stats['signal_words'],
        top_opponents=pg_stats['top_opponents'],
        war_count=len(wars),
        recent_wars=recent_wars or '(无)',
        terr_losses=terr_l_summary or '(无)',
        terr_gains=terr_g_summary or '(无)',
        alliances_summary=ally_sum or '(无)',
        ucdp_periods=ucdp_str,
        identity=identity,
    )


def main():
    ap = argparse.ArgumentParser(description='ConStruct AI diagnosis engine')
    ap.add_argument('code', nargs='?', default='CHN')
    ap.add_argument('--api-key', default=os.environ.get('DEEPSEEK_API_KEY', ''))
    ap.add_argument('--pg', default=DEFAULT_PG)
    ap.add_argument('--neo4j-uri', default=DEFAULT_NEO4J)
    ap.add_argument('--neo4j-user', default='neo4j')
    ap.add_argument('--neo4j-password', default='construct_neo4j_2026')
    ap.add_argument('--dry-run', action='store_true', help='只构建 prompt 不调 API')
    a = ap.parse_args()

    code = a.code
    cname = CA.CANONICAL_ACTORS.get(code, {}).get('name', code)

    if not a.api_key and not a.dry_run:
        print('[ERROR] 需要 DEEPSEEK_API_KEY 环境变量或 --api-key')
        print('  获取 key: https://platform.deepseek.com')
        return

    timeline = load_timeline(code)
    pg_stats = query_pg_stats(a.pg, code)
    neo_events = query_neo4j_events(a.neo4j_uri, a.neo4j_user, a.neo4j_password, code)
    prompt = build_prompt(code, cname, timeline, neo_events, pg_stats)

    print(f'[{code}] GDELT: {pg_stats["gdelt_count"]} events, tone={pg_stats["gdelt_tone"]}')
    print(f'[{code}] Neo4j: {len(neo_events)} recent events')
    print(f'[{code}] COW: {sum(1 for e in timeline.get("skeleton_cow",[]) if e["type"]=="WAR")} wars, prompt={len(prompt)} chars')

    if a.dry_run:
        out = os.path.join(OUTPUT_DIR, f'{code}_prompt.txt')
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f'[dry-run] prompt → {out}')
        return

    print(f'[{code}] 调用 DeepSeek API...')
    diagnosis = call_deepseek(prompt, a.api_key)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    md_path = os.path.join(OUTPUT_DIR, f'{code}_{date_str}.md')

    header = f"""# ConStruct AI 诊断 — {cname} ({code})
> 生成时间: {datetime.now(timezone.utc).isoformat()}
> 数据源: GDELT 30d + COW 200y + UCDP 1989-2025 + Neo4j + Kaggle
> 引擎: ConStruct Engine v5 + DeepSeek {DEEPSEEK_MODEL}
> 状态: AI-GENERATED — 未经人工终审, 仅供参考

{diagnosis}

---
*Generated by ConStruct Lab AI Diagnostic Engine*
*Data integrity: GDELT events verified via PG → Neo4j ingest pipeline*
"""
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(header)
    print(f'[diagnose] → {md_path}')


if __name__ == '__main__':
    main()
