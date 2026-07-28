#!/usr/bin/env python3
"""
ConStruct — 补充历史战争数据集采集器
========================================
合并两个源, 注入 actor_timelines skeleton_cow:
  ① Kaggle War Records — 10,684 条, CSV (War Name/Start Year/Region/Source)
  ② GlobalConflicts    — 67 个冲突 JSON (Context/Date/Belligerents/Casualties)

补 COW/UCDP 缺失的近代事件 (如 1840 鸦片战争), 标注来源 'SUPPLEMENT'
"""
import os, sys, json, csv, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CA_PATH = os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, CA_PATH)
import canonical_actors as CA

TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')

KAGGLE_PATH = r'C:\Users\xheih\.cache\kagglehub\datasets\pritamthapa44\war-records\versions\1\wars_17000BC_2014AD_merged.csv'
GCF_DIR = r'D:\Projects\地缘推演台\GlobalConflicts'
CHINATIMELINE_DIR = r'D:\Projects\地缘推演台\chinatimeline-data'

# 已下载 (可选, 下载失败则跳过)
CHED_DIR = r'D:\Projects\地缘推演台\CHED-data'

# Region 名 → canonical code 映射 (包含常见变体)
REGION_ALIASES = {
    'china': 'CHN', 'chinese': 'CHN', 'china (prc)': 'CHN',
    'japan': 'JPN', 'japanese': 'JPN',
    'russia': 'RUS', 'russian': 'RUS', 'soviet union': 'RUS', 'soviet': 'RUS',
    'united states': 'USA', 'american': 'USA', 'usa': 'USA',
    'united kingdom': 'GBR', 'british': 'GBR', 'britain': 'GBR', 'england': 'GBR',
    'france': 'FRA', 'french': 'FRA',
    'germany': 'DEU', 'german': 'DEU', 'prussia': 'DEU',
    'india': 'IND', 'indian': 'IND',
    'brazil': 'BRA', 'brazilian': 'BRA',
    'turkey': 'TUR', 'ottoman': 'TUR', 'turkish': 'TUR',
    'iran': 'IRN', 'persia': 'IRN', 'persian': 'IRN',
    'iraq': 'IRQ', 'iraqi': 'IRQ',
    'saudi arabia': 'SAU', 'saudi': 'SAU',
    'israel': 'ISR', 'israeli': 'ISR',
    'egypt': 'EGY', 'egyptian': 'EGY',
    'south korea': 'KOR', 'korean': 'KOR', 'korea': 'KOR',
    'north korea': 'PRK',
    'pakistan': 'PAK', 'pakistani': 'PAK',
    'ukraine': 'UKR', 'ukrainian': 'UKR',
    'australia': 'AUS', 'australian': 'AUS',
    'canada': 'CAN', 'canadian': 'CAN',
    'italy': 'ITA', 'italian': 'ITA',
    'spain': 'ESP', 'spanish': 'ESP',
    'mexico': 'MEX', 'mexican': 'MEX',
    'philippines': 'PHL', 'filipino': 'PHL', 'philippine': 'PHL',
    'vietnam': 'VNM', 'vietnamese': 'VNM',
    'indonesia': 'IDN', 'indonesian': 'IDN',
    'netherlands': 'NLD', 'dutch': 'NLD',
    'poland': 'POL', 'polish': 'POL',
    'sweden': 'SWE', 'swedish': 'SWE',
    'austria': 'AUT', 'austrian': 'AUT',
    'belgium': 'BEL', 'belgian': 'BEL',
    'greece': 'GRC', 'greek': 'GRC',
    'portugal': 'PRT', 'portuguese': 'PRT',
    'serbia': 'SRB', 'serbian': 'SRB', 'yugoslavia': 'SRB',
    'taiwan': 'TWN', 'taiwanese': 'TWN', 'taiwan (roc)': 'TWN',
    'south africa': 'ZAF',
    'nigeria': 'NGA', 'nigerian': 'NGA',
    'ethiopia': 'ETH', 'ethiopian': 'ETH',
    'myanmar': 'MMR', 'burma': 'MMR', 'burmese': 'MMR',
    'syria': 'SYR', 'syrian': 'SYR',
    'libya': 'LBY', 'libyan': 'LBY',
    'lebanon': 'LBN', 'lebanese': 'LBN',
    'afghanistan': 'AFG', 'afghan': 'AFG',
    'cuba': 'CUB', 'cuban': 'CUB',
    'colombia': 'COL', 'colombian': 'COL',
    'venezuela': 'VEN', 'venezuelan': 'VEN',
    'chile': 'CHL', 'chilean': 'CHL',
    'argentina': 'ARG', 'argentine': 'ARG',
    'peru': 'PER', 'peruvian': 'PER',
    'bolivia': 'BOL', 'bolivian': 'BOL',
    'paraguay': 'PRY', 'paraguayan': 'PRY',
    'uruguay': 'URY', 'uruguayan': 'URY',
    'denmark': 'DNK', 'danish': 'DNK',
    'norway': 'NOR', 'norwegian': 'NOR',
    'finland': 'FIN', 'finnish': 'FIN',
    'hungary': 'HUN', 'hungarian': 'HUN',
    'romania': 'ROU', 'romanian': 'ROU',
    'bulgaria': 'BGR', 'bulgarian': 'BGR',
    'czech': 'CZE', 'czechoslovakia': 'CZE',
    'slovakia': 'SVK',
    'switzerland': 'CHE', 'swiss': 'CHE',
    'mongolia': 'MNG', 'mongol': 'MNG',
    'thailand': 'THA', 'thai': 'THA', 'siam': 'THA',
    'bangladesh': 'BGD', 'bangladeshi': 'BGD',
    'singapore': 'SGP', 'singaporean': 'SGP',
    'malaysia': 'MYS', 'malaysian': 'MYS',
    'morocco': 'MAR', 'moroccan': 'MAR',
    'algeria': 'DZA', 'algerian': 'DZA',
    'sudan': 'SDN', 'sudanese': 'SDN',
    'somalia': 'SOM', 'somali': 'SOM',
    'yemen': 'YEM', 'yemeni': 'YEM',
    'croatia': 'HRV', 'croatian': 'HRV',
}


def resolve_region(region_name):
    """Region 字符串 → canonical 代码"""
    rl = region_name.lower().strip().rstrip('.')
    # 直接匹配 canonical 代码
    if region_name.upper() in CA.CANONICAL_ACTORS:
        return region_name.upper()
    # 精确匹配别名
    if rl in REGION_ALIASES:
        return REGION_ALIASES[rl]
    # 前缀匹配
    for alias, code in REGION_ALIASES.items():
        if rl.startswith(alias) or alias.startswith(rl):
            return code
    # canonical name 直接匹配
    for code, a in CA.CANONICAL_ACTORS.items():
        if a['name'].lower() == rl:
            return code
    return None


def load_kaggle():
    """Kaggle CSV → [{war_name, year_start, regions, source}]"""
    events = []
    with open(KAGGLE_PATH, encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            name = row.get('War Name', '')
            yr_str = row.get('Start Year', '')
            region = row.get('Region', '')
            src = row.get('Source', 'Kaggle')
            if not name or not yr_str:
                continue
            try:
                yr = int(float(yr_str))
            except (ValueError, TypeError):
                continue
            if yr < 1800:  # 仅近代, 与 COW 时间对齐
                continue
            regions = [r.strip() for r in region.split(',') if r.strip()]
            events.append({
                'year_start': yr, 'year_end': yr,
                'type': 'WAR',
                'label': name,
                'regions': regions,
                'source': f'Kaggle War Records ({src})',
            })
    return events


def load_global_conflicts():
    """GlobalConflicts JSONs → [{war_name, year_start, year_end, belligerents, source}]
    改进: 兼容多种内部结构 (dict / list-of-dicts / 嵌套 Context)"""
    events = []
    for fname in sorted(os.listdir(GCF_DIR)):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(GCF_DIR, fname), encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            continue
        if not data:
            continue

        # Unwrap outer layer
        keys = list(data.keys())
        if not keys:
            continue
        inner = data[keys[0]]
        if not isinstance(inner, dict):
            continue

        name = keys[0].replace('_', ' ')
        date_str = inner.get('Date', '') or ''
        belligerents = inner.get('Belligerents', {})

        # Handle nested Context (some files wrap belligerents differently)
        if isinstance(belligerents, str):
            regions = [r.strip() for r in belligerents.split(',')]
        elif isinstance(belligerents, dict):
            regions = list(belligerents.keys())
        elif isinstance(belligerents, list):
            regions = [str(r) for r in belligerents if isinstance(r, str)]
        else:
            regions = []

        # Also scan Context key for belligerent info
        ctx = inner.get('Context', {})
        if isinstance(ctx, dict):
            ctx_bl = ctx.get('Part_of', [])
            if isinstance(ctx_bl, list):
                regions.extend([r for r in ctx_bl if isinstance(r, str)])

        # 年份提取 — try Date field, Context.Summary, then filename
        yrs = re.findall(r'\b(1[89]\d{2}|20[0-2]\d)\b', date_str)
        if not yrs and isinstance(ctx, dict):
            ctx_sum = ctx.get('Summary', '')
            yrs = re.findall(r'\b(1[89]\d{2}|20[0-2]\d)\b', ctx_sum)
        if not yrs:
            yrs = re.findall(r'\b(1[89]\d{2}|20[0-2]\d)\b', fname)
        if not yrs:
            continue
        y1 = int(min(yrs)); y2 = int(max(yrs)) if len(yrs) > 1 else y1

        events.append({
            'year_start': y1, 'year_end': y2,
            'type': 'WAR',
            'label': name,
            'regions': regions,
            'source': 'GlobalConflicts (GitHub)',
        })
    return events


def load_chinatimeline():
    """chinatimeline CSV 事件 → [{year_start, label, regions, source}]"""
    events = []
    csv_files = [
        ('US_CN_TradeWar/TradeWar_Events.csv', {'US': 'USA', 'China': 'CHN', 'Both': 'BOTH'}),
        ('ideology/CCP_Ideology_Events.csv', {'China': 'CHN'}),
        ('OneBeltOneRoad/OBOR_Events.csv', {'China': 'CHN'}),
    ]
    for rel_path, group_map in csv_files:
        full = os.path.join(CHINATIMELINE_DIR, rel_path)
        if not os.path.exists(full):
            continue
        with open(full, encoding='utf-8', newline='') as f:
            r = csv.DictReader(f)
            for row in r:
                date_str = row.get('date', '')
                name = row.get('name', '')
                grp = row.get('group', '')
                yrs = re.findall(r'\b(20[0-2]\d)\b', date_str)
                if not yrs or not name:
                    continue
                yr = int(yrs[0])
                # map group to canonical code(s)
                regions = []
                grp_clean = grp.strip()
                if grp_clean in group_map:
                    code = group_map[grp_clean]
                    if code == 'BOTH':
                        regions = ['CHN', 'USA']
                    else:
                        regions = [code]
                elif ',' in grp:
                    for g in grp.split(','):
                        g = g.strip()
                        if g in group_map:
                            c = group_map[g]
                            if c not in regions:
                                regions.append(c)
                if not regions:
                    continue
                events.append({
                    'year_start': yr, 'year_end': yr,
                    'type': 'POLITICAL_EVENT',
                    'label': name,
                    'regions': regions,
                    'source': 'chinatimeline (GitHub)',
                })
    return events


def inject_to_timelines(all_events, dry_run=False):
    """去重后注入 actor_timelines skeleton_cow, 标注 SUPPLEMENT"""
    injected = 0
    for code in CA.CANONICAL_ACTORS:
        cname = CA.CANONICAL_ACTORS[code]['name'].lower()
        matched = []
        for ev in all_events:
            for r in ev['regions']:
                rc = resolve_region(r)
                if rc == code:
                    matched.append(ev); break

        if not matched:
            continue

        # 加载已有 timeline
        tpath = os.path.join(TIMELINE_DIR, f'{code}.json')
        existing = {}
        if os.path.exists(tpath):
            with open(tpath, encoding='utf-8') as f:
                existing = json.load(f)

        skeleton = existing.get('skeleton_cow', [])
        existing_names = {(e.get('label', ''), e.get('year_start', 0)) for e in skeleton}

        new_events = []
        for ev in matched:
            key = (ev['label'], ev['year_start'])
            if key not in existing_names:
                new_events.append({
                    'year_start': ev['year_start'],
                    'year_end': ev['year_end'],
                    'type': ev.get('type', 'WAR'),
                    'label': ev['label'],
                    'hostility': '',
                    'involved': [code],
                    'source': ev['source'],
                })
                existing_names.add(key)

        if new_events:
            skeleton.extend(new_events)
            skeleton.sort(key=lambda e: e['year_start'])
            existing['skeleton_cow'] = skeleton
            if not dry_run:
                with open(tpath, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            injected += len(new_events)
            print(f'[{code}] +{len(new_events)} events → {tpath}')
    return injected


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Merge supplementary war datasets')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    print('[WAR] Loading Kaggle...')
    kaggle = load_kaggle()
    print(f'[WAR] Kaggle: {len(kaggle)} events (1800+)')

    print('[WAR] Loading GlobalConflicts...')
    gcf = load_global_conflicts()
    print(f'[WAR] GlobalConflicts: {len(gcf)} events')

    print('[WAR] Loading chinatimeline...')
    cntl = load_chinatimeline()
    print(f'[WAR] chinatimeline: {len(cntl)} events')

    all_events = kaggle + gcf + cntl
    print(f'[WAR] Total: {len(all_events)} events, resolving to 47 canonical actors...')

    injected = inject_to_timelines(all_events, dry_run=a.dry_run)
    suffix = ' (dry-run, 未写文件)' if a.dry_run else ''
    print(f'[WAR] Injected {injected} new events across {len(CA.CANONICAL_ACTORS)} actors{suffix}')


if __name__ == '__main__':
    main()
