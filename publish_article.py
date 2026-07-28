#!/usr/bin/env python3
"""
ConStruct — 结构化诊断文章生成器 (DeepSeek)
==================================================
基于 PG + Neo4j 数据 + COW 骨架，输出 2000-3000 字 Markdown 文章。
文体：结构性诊断，不是新闻摘要，不是学术论文。
→ DeepSeek → Markdown → content/articles/

用法:
  python publish_article.py CHN
  python publish_article.py CHN --api-key sk-xxx
"""

import os, sys, json, argparse, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts'))
import canonical_actors as CA

DEEPSEEK_MODEL = 'deepseek-chat'
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'
PG_DSN = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')
OUTPUT_DIR = os.path.join(BASE, 'content', 'articles')


def load_identity_snippet(code):
    """从 actors/ md 提取关键段落: L4建构来源 + 身份一句话"""
    short_map = {'CHN': 'CN', 'USA': 'US', 'RUS': 'RU', 'JPN': 'JP', 'GBR': 'GB',
                 'FRA': 'FR', 'DEU': 'DE', 'IND': 'IN', 'IDN': 'ID', 'CAN': 'CN',
                 'BRA': 'BR', 'TUR': 'TR', 'IRN': 'IR', 'ISR': 'IL', 'SAU': 'SA',
                 'EGY': 'EG', 'AUS': 'AU', 'PHL': 'PH', 'KOR': 'KR', 'UKR': 'UA',
                 'VNM': 'VN', 'TWN': 'TW', 'PAK': 'PK', 'PRK': 'KP'}
    short = short_map.get(code, code)
    actors_dir = os.path.join(os.path.dirname(BASE), 'actors')
    for tier in ['Tier1', 'Tier2']:
        p = os.path.join(actors_dir, tier, short)
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.endswith('.md'):
                    with open(os.path.join(p, f), encoding='utf-8') as fh:
                        content = fh.read()
                    lines = content.split('\n')
                    snippets = []
                    in_l4 = False
                    for line in lines:
                        stripped = line.strip().lstrip('> ')
                        if '身份一句话' in stripped:
                            snippets.append('# ' + stripped)
                        if '**构型' in stripped or 'DNA:' in stripped or '深层Identity' in stripped:
                            snippets.append(stripped)
                        if 'L4 建构来源' in stripped or 'L4b' in stripped:
                            in_l4 = True; continue
                        if in_l4 and stripped.startswith('|') and any(k in stripped for k in ['鸦片', '甲午', '八国', '侵华', '条约', '百年', '独立', '五族', '驡逐']):
                            snippets.append(stripped)
                        if in_l4 and len(snippets) >= 18: break
                    return '\n'.join(snippets[:18]) if snippets else ''
    return ''


def load_timeline(code):
    # 组织主体成立年——COW 事件只从成立后计算
    FOUNDED = {'EU': 1993, 'NATO': 1949, 'UN': 1945, 'WTO': 1995,
               'IMF': 1944, 'WB': 1944, 'ASEAN': 1967, 'SCO': 2001,
               'BRICS': 2009, 'GCC': 1981, 'OPEC': 1960, 'AL': 1945}
    year_cutoff = FOUNDED.get(code, 1800)  # 国家=1800，组织=成立年

    path = os.path.join(TIMELINE_DIR, f'{code}.json')
    default = {'total_wars': 0, 'recent_wars': ['无'], 'territorial': ['无'],
               'alliance_summary': '无', 'ucdp_conflicts': ['无']}
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    # 过滤: 只保留成立年之后的事件
    cow = data.get('skeleton_cow', [])
    wars = [e for e in cow if e['type'] == 'WAR' and e['year_start'] >= year_cutoff]
    terr = [e for e in cow if e['type'] in ('TERR_LOSS', 'TERR_GAIN') and e['year_start'] >= year_cutoff]
    alliances = [e for e in cow if e['type'] == 'ALLIANCE' and e['year_start'] >= year_cutoff]
    ucdp = data.get('timeline_ucdp', [])
    return {
        'total_wars': len(wars),
        'recent_wars': [f"{e['year_start']} {e.get('label','')}" for e in sorted(wars, key=lambda x: x['year_start'])[-10:]],
        'territorial': [f"{e['year_start']} {e.get('entity', e.get('label',''))} (from {e.get('from','')} to {e.get('to','')})"
                        for e in terr if e['year_start'] >= 1800][-8:],
        'alliance_summary': ', '.join(f"{e['year_start']}+{e.get('with','')}" for e in alliances[-5:]),
        'ucdp_conflicts': [f"{p.get('start_year','')}-{p.get('end_year','')}: {p.get('label','')}"
                           for p in ucdp[-3:]],
    }


def load_gdelt_snapshot(code):
    import psycopg2
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), AVG(avg_tone) FROM events WHERE source='GDELT' AND (actor1_code=%s OR actor2_code=%s) AND time >= NOW() - INTERVAL '48 hours'", (code,code))
    cnt, tone = cur.fetchone()
    cur.execute("SELECT action, COUNT(*) FROM events WHERE source='GDELT' AND (actor1_code=%s OR actor2_code=%s) AND time >= NOW() - INTERVAL '48 hours' GROUP BY action ORDER BY 2 DESC", (code,code))
    actions = cur.fetchall()[:5]
    cur.execute("SELECT actor2_code, COUNT(*) FROM events WHERE source='GDELT' AND actor1_code=%s AND time >= NOW() - INTERVAL '48 hours' GROUP BY actor2_code ORDER BY 2 DESC LIMIT 5", (code,))
    opps = cur.fetchall()
    cur.close(); conn.close()
    return {
        'count': cnt or 0,
        'tone': round(tone or 0, 2),
        'top_actions': ','.join(f'{a}({c})' for a,c in actions),
        'top_opponents': ','.join(f'{o}({c})' for o,c in opps),
    }


def call_deepseek(prompt, api_key):
    data = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [
            {'role': 'system', 'content': (
                '你是一个地缘政治结构性诊断文章的写作者。你的文体要求：\n'
                '- 不是新闻摘要，不是学术论文。是"结构性诊断"——用身份/历史/制度叙事来解释当前行为逻辑。\n'
                '- 语气: 冷静、直接、不下结论性预测，只做结构性判断。\n'
                '- 禁用词: "值得注意的是"、"综上所述"、"在某种程度上"、"不可忽视"、"复杂而多元"、"相辅相成"、"双刃剑"。\n'
                '- 每段开头不要用"根据数据"或"基于分析"。直接从事实切入。\n'
                '- 文章结构: (1) 一个近期信号做引子 (2) 对照深层结构的解释 (3) 历史骨架的约束 (4) 结构性判断——哪些路走得通，哪些逻辑上不可能。\n'
                '- 术语规范: 分析对象统一用中文简称（"美国""中国""俄罗斯""日本"），引用其自我表述时用专有名词（"例外论""天下体系""复兴"）。不混用英文名。\n'
                '- ConStruct 术语: 方法维度（如"方法⑤交易式"）首次出现时加简短注释。构型名（如"天下体系型""冻结局"）同理。\n'
                '- 全球视角: 分析一国行为时，至少用一次全球南方的冲突模式作为对比锚点。\n'
                '- 反方推演: 每条"不可能"判断后面，用一句"反方论点"说明为什么相反论点在结构上不可行。\n'
                '- 置信度标注: 每条核心断言后标注[高/中/低]，格式 `[高，依据: …]`。高=有历史/数据确证；中=有理论支撑但数据不足；低=纯推演。\n'
                '- GDELT 字段: Actor2Name 为空/NULL 表示无明确对手方的单边/内部行动，解读时避免说成"对手是无"。更不要把短期 None 信号当独立证据——必须跟 COW 长期同盟记录叠加后才下结论。\n'
                '- 基准比较: 遇到事件数判断时，必须横向对比同期对手国/同区域国家的数量后再下结论。不孤立解读。\n'
                '- 对华锚定: 对中国周边任何主体（日本、韩国、台湾、菲律宾、印度，以及 Tier2 的亚洲国家），必须单列一段对华关系的结构性分析：中国不是"他者之一"，是该主体 Identity 的构成性约束。\n'
                '- 叙事识别: 每篇结论后面加一段"为什么关于该国的流行叙事都是半真半假的"——不是选一边站，是解剖��条叙事背后的结构驱动力。\n'
                '- 内部政治压力: 每个主体的分析中必须有一段讨论内部政治约束——政权合法性、社会压力、精英分裂等——作为外部行为变量的结构性约束。不要把国家假设为单一意志体。\n'
                '- 情景分支: 每条"最可能路径"判断后面至少列出三种情景（A最可能 B次可能 C极端），不能给人"二选一"的非黑即白印象。\n'
                '- 事件-身份区分: 解释身份驱动的行为时，要区分"结构必然性"和"战术误判"。结构决定"为什么必然发生"，误判解释"为什么是这个时间/这种方式"。不要把两者混在一起说成"不是计算错误"。\n'
                '- 历史敏感性: 涉及中印边境/中越/台湾/克什米尔等争议地区的叙述时，不采用任一方官方名称（如"中越自卫反击战""阿克赛钦属于印度"），用行为模式描述替代具体边界主张。用"打而不占"这类结构性概念，不是政治立场。\n'
                '- 经济工具分析: 讨论经济杠杆时，不采用"X国用投资/贸易分化Y国"这种能动者操纵视角。改写为"Y国内部存在结构性分歧（商业利益/安全依赖/家族派系），X国的经济接触利用了这个分歧但它本身不创造分歧。经济工具的边际效用会递减，存在明确的上限。"\n'
                '- 禁止先例论证: 严禁使用"历史上没有先例"作为"逻辑上不可能"的理由。每个国家行为的第一次之前都没有先例。用成本收益分析替代：该行为触发哪些结构性约束？成本叠加后的概率有多高？概率不是零的时候，识别什么条件下会触发。\n'
                '- 时间窗口: 讨论多方博弈的僵局或等待游戏时，必须分析各方的"时间偏好不对称"——谁的时间窗口更长（基于内部政治周期/战略资源/制度稳定性），谁的最短。时间最短的一方最可能先打破僵局。\n'
                '- 台海南海联动: 分析中国在南海/东海/亚洲任何海域行为时，必须单列一段台湾变量的结构性约束。南海不是孤立海域——它是台湾统一危机的战略纵深。菲律宾/越南的处理方式不是独立的南海策略，是对台危机中防止第二战场的对冲操作。\n'
                '- 输出: (a) 正文前加数据摘要表 (b) 2000-3000字正文 (c) 路径判断（含三情景）(d) 内部政治约束段 (e) 叙事识别段 (f) "我们不知道什么": 最后一段列出本分析可能遗漏的结构性因素——数据源偏差（GDELT西方中心）、不可观测行为（秘密外交/灰色地带）、本文依赖但可能存疑的理论假设。不是低估自己的分析，是承认方法和数据固有的盲区。\n'
                '- 输出纯 Markdown，标题 # 开头，不要用 ## 之外的多级标题。'
            )},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.4,
        'max_tokens': 4000,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
        return resp['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:500]
        return f'[DeepSeek API Error HTTP {e.code}]: {body}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('code', nargs='?', default='CHN')
    ap.add_argument('--api-key', default=os.environ.get('DEEPSEEK_API_KEY', ''))
    a = ap.parse_args()

    if not a.api_key:
        print('[ERROR] 需要 DEEPSEEK_API_KEY 环境变量 或 --api-key')
        return

    code = a.code
    cname = CA.CANONICAL_ACTORS.get(code, {}).get('name', code)
    cfg = CA.CANONICAL_ACTORS.get(code, {}).get('config', '')
    identity = load_identity_snippet(code)
    timeline = load_timeline(code)
    gdelt = load_gdelt_snapshot(code)

    prompt = f"""写一篇关于 **{cname}** 的结构性诊断文章。以下是源数据。

## 近期信号 (GDELT 48h)
- 事件数: {gdelt['count']}
- 平均情绪 (Goldstein scale, -10~+10): {gdelt['tone']}
- 主要行动类型: {gdelt['top_actions']}
- 主要对手/伙伴: {gdelt['top_opponents']}

## 身份档案 (从 ConStruct 档案中提取)
{identity}

## 历史骨架 (COW 200年 + UCDP)
- 近代战争总数: {timeline['total_wars']}
- 近10场战争: {', '.join(timeline['recent_wars'])}
- 领土变更: {', '.join(timeline['territorial'])}
- 同盟关系: {timeline['alliance_summary']}
- UCDP冲突期: {', '.join(timeline['ucdp_conflicts'])}

## ConStruct 构型: {cfg}

## 文章要求
1. **第 1 段**: 从近期 GDELT 信号中挑一个最具体的切入——一个事件类型、一个 tone 变化、一个对手互动。不要泛泛地说"近期地缘政治复杂"。
2. **第 2-3 段**: 对照这个国家深层结构的回应——Identity 决定了它能怎样回应、不能怎样回应。用档案里的"核心恐惧"和"Identity 一句话"来解释行为逻辑。
3. **第 4-5 段**: 对照历史骨架——这个国家过去在类似情况下做了什么。领土变更和战争记录不是背景，是约束条件的直接证据。
4. **第 6-7 段**: 结构性判断——在这个 Identity 约束下，哪些路走得通，哪些路逻辑上不可能。不做预测，只做诊断。
5. 字数: 2000-3000字。Markdown，正文前用 ## 数据摘要生成四列表格（指标/数值/来源/含义），正文后附 ## 路径判断。"""

    print(f'[{code}] prompt={len(prompt)} chars, calling DeepSeek...')
    article = call_deepseek(prompt, a.api_key)
    if article.startswith('[DeepSeek API Error'):
        print(article)
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    path = os.path.join(OUTPUT_DIR, f'{code}_structure_article_{date_str}.md')
    header = f"""# ConStruct 结构诊断 — {cname} ({code})
> {date_str}
> 数据源: GDELT + COW 200年 + UCDP 1989-2025
> 状态: AI生成草稿 — 待人工审定

---
{article}
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header)
    print(f'[article] → {path}')


if __name__ == '__main__':
    main()
