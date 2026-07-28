#!/usr/bin/env python3
"""
ConStruct — actors/ 档案自动交叉引用生成器
=============================================
扫描 actors/ 下每篇 .md，提取年份 → 去 actor_timelines/{code}.json
匹配对应的 COW 骨架事件 + UCDP 冲突 + GDELT 脉冲 → 生成 {code}_crossref.json

不修改原始 md 文件——生成的 JSON 供人工对照后手动挂链接。

输出: actors/crossref/{shortcode}_crossref.json
"""
import os, sys, re, json, csv
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
TIMELINE_DIR = os.path.join(os.path.dirname(BASE), 'construct-engine', 'actor_timelines')
ACTORS_DIR = os.path.join(os.path.dirname(BASE), 'actors')
OUTPUT_DIR = os.path.join(ACTORS_DIR, 'crossref')

# 引入 canonical_actors 和 COW 国家码
CA_PATH = os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, CA_PATH)
import canonical_actors as CA

# 加载 COW 数字码→国家名 (用于 TERR_LOSS/GAIN entity 解析)
COW_CODE_TO_NAME = {}
try:
    cow_codes_path = os.path.join(os.path.expanduser('~'), 'Downloads', '新建文件夹', 'COW-country-codes.csv')
    with open(cow_codes_path, encoding='utf-8', newline='') as f:
        r = csv.reader(f); next(r)
        for row in r:
            try:
                COW_CODE_TO_NAME[int(row[1])] = row[2].strip()
            except (ValueError, IndexError):
                pass
except FileNotFoundError:
    pass  # 非本机跑时 COW 文件不可达, 优雅降级

# canonical_code → Wikipedia 友好的英文名
def wiki_country_name(code):
    a = CA.CANONICAL_ACTORS.get(code, {})
    name = a.get('name', code)
    # special cases
    overrides = {'United States': 'United_States', 'United Kingdom': 'United_Kingdom',
                 'South Korea': 'South_Korea', 'North Korea': 'North_Korea',
                 'Russia': 'Russia', 'China': 'China', 'Japan': 'Japan',
                 'Germany': 'Germany', 'France': 'France', 'India': 'India',
                 'Brazil': 'Brazil', 'Turkey': 'Turkey', 'Iran': 'Iran',
                 'Iraq': 'Iraq', 'Saudi Arabia': 'Saudi_Arabia',
                 'Israel': 'Israel', 'Egypt': 'Egypt',
                 'Pakistan': 'Pakistan', 'Australia': 'Australia',
                 'Ukraine': 'Ukraine', 'Canada': 'Canada',
                 'Italy': 'Italy', 'Spain': 'Spain', 'Mexico': 'Mexico',
                 'Philippines': 'Philippines', 'Vietnam': 'Vietnam'}
    return overrides.get(name, name.replace(' ', '_'))


def build_ref_url(ev, short_code):
    """构建 Wikipedia 引用 URL, 自动解析 COW 数字码和 canonical 短码"""
    etype = ev.get('type', '')
    label = ev.get('label', '') or ev.get('entity', '') or ev.get('with', '')

    if etype == 'WAR' and label and label != short_code:
        if not label.lower().endswith('war'):
            label = label + ' War'
        return f"https://en.wikipedia.org/wiki/{label.replace(' ','_')}"

    if etype in ('TERR_LOSS', 'TERR_GAIN'):
        # COW entity 可能是数字 CCode 或文本
        opp_code = ev.get('from') or ev.get('to') or ''
        if opp_code:
            opp_name = wiki_country_name(opp_code)
        else:
            opp_name = label.replace(' ', '_')
        w_self = wiki_country_name(SHORT_TO_LONG.get(short_code, short_code))
        return f"https://en.wikipedia.org/wiki/{w_self}-{opp_name}_relations"

    if etype == 'ALLIANCE':
        ally = ev.get('with', '') or label
        ally_name = wiki_country_name(ally)
        w_self = wiki_country_name(SHORT_TO_LONG.get(short_code, short_code))
        return f"https://en.wikipedia.org/wiki/{w_self}-{ally_name}_relations"

    return ''

# actors/ 短码 → canonical_actors 长码
SHORT_TO_LONG = {
    'CN': 'CHN', 'US': 'USA', 'RU': 'RUS', 'JP': 'JPN', 'EU': 'EU',
    'IL': 'ISR', 'IR': 'IRN', 'UA': 'UKR',
    'DE': 'DEU', 'FR': 'FRA', 'GB': 'GBR', 'IN': 'IND', 'KR': 'KOR',
    'TR': 'TUR', 'SA': 'SAU', 'EG': 'EGY', 'AUS': 'AUS', 'PH': 'PHL',
    'VN': 'VNM', 'SG': 'SGP', 'RS': 'SRB', 'TW': 'TWN',
    # Tier3 企业/组织 暂不覆盖 (COW 仅国家主体)
}

YEAR_RE = re.compile(r'\b(1[89]\d{2}|20[0-2]\d)\b')


def extract_years(md_path):
    """从 md 文件中提取所有出现的年份 (1800–2026)"""
    years = set()
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            for m in YEAR_RE.finditer(line):
                y = int(m.group())
                if 1800 <= y <= 2026:
                    years.add(y)
    return sorted(years)


def load_timeline(short_code):
    """读 actor_timelines/{longcode}.json"""
    long_code = SHORT_TO_LONG.get(short_code, short_code)
    path = os.path.join(TIMELINE_DIR, f'{long_code}.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def match_events(timeline_data, years, short_code):
    """匹配年份 ↔ COW/ UCDP/ GDELT 事件"""
    result = {'matches': [], 'unmatched_years': [], 'total_events': 0}

    cow = timeline_data.get('skeleton_cow', [])
    ucdp = timeline_data.get('timeline_ucdp', [])
    gdelt = timeline_data.get('recent_gdelt', {})

    # COW 匹配
    for yr in years:
        cow_matches = [e for e in cow if e['year_start'] <= yr <= e.get('year_end', e['year_start'])]
        for e in cow_matches[:3]:
            label = e.get('label', '') or e.get('entity', '') or e.get('with', '')
            ref_url = build_ref_url(e, short_code)
            result['matches'].append({
                'year': yr, 'source': 'COW',
                'type': e.get('type', '?'),
                'label': label,
                'hostility': e.get('hostility', ''),
                'opponent': e.get('from', e.get('to', e.get('with', ''))),
                'reference': f"COW {e.get('source', '')[:30]}",
                'url': ref_url,
            })
            result['total_events'] += 1

    # UCDP 时期匹配
    for p in ucdp:
        if p['start_year'] <= max(years) and p['end_year'] >= min(years):
            # 如果时期与 md 年份有交集，记一条
            overlap = set(range(p['start_year'], p['end_year'] + 1)) & set(years)
            if overlap:
                result['matches'].append({
                    'year': f"{p['start_year']}-{p['end_year']}",
                    'source': 'UCDP',
                    'type': 'conflict_period',
                    'label': p.get('label', ''),
                    'events': p.get('events_total', 0),
                    'deaths': p.get('deaths_total', 0),
                    'opponents': p.get('top_opponents', []),
                    'reference': 'UCDP GED v26.1',
                })
                result['total_events'] += 1

    # GDELT
    if gdelt and gdelt.get('events_30d', 0) > 0:
        result['matches'].append({
            'year': '2026 (rolling)',
            'source': 'GDELT',
            'type': 'recent_pulse',
            'label': f"{gdelt['events_30d']} events 30d, tone={gdelt.get('avg_tone_30d', 0)}",
            'signal_words': gdelt.get('signal_words', []),
            'reference': 'GDELT 2.0',
        })
        result['total_events'] += 1

    # 无匹配年份
    matched_years = set()
    for m in result['matches']:
        if isinstance(m['year'], int):
            matched_years.add(m['year'])
    result['unmatched_years'] = [y for y in years if y not in matched_years]

    return result


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scanned = 0
    for tier in ['Tier1', 'Tier2']:
        tier_dir = os.path.join(ACTORS_DIR, tier)
        if not os.path.isdir(tier_dir):
            continue
        for short_code in os.listdir(tier_dir):
            subdir = os.path.join(tier_dir, short_code)
            if not os.path.isdir(subdir):
                continue
            md_files = [f for f in os.listdir(subdir) if f.endswith('.md')]
            if not md_files:
                continue

            md_path = os.path.join(subdir, md_files[0])
            years = extract_years(md_path)
            if not years:
                continue

            timeline = load_timeline(short_code)
            if not timeline:
                print(f'[skip] {short_code}: no timeline data')
                continue

            result = match_events(timeline, years, short_code)
            result['code'] = short_code
            result['long_code'] = SHORT_TO_LONG.get(short_code, short_code)
            result['years_found'] = years
            result['md_file'] = md_path

            out_path = os.path.join(OUTPUT_DIR, f'{short_code}_crossref.json')
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f'[{short_code}] {len(years)} years in md → {result["total_events"]} cross-refs → {out_path}')
            scanned += 1

    print(f'\nDone. {scanned} crossref files → {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
