#!/usr/bin/env python3
"""
ConStruct — COW 历史骨架采集器
================================
从 Correlates of War (MID + Interstate War) 生成主体的远代骨架层,
写入 actor_timelines/{code}.json 的 skeleton 字段。

数据源:
  - MID 5.0 (MIDA + MIDB): 军事化争端, 1816-2014
  - Inter-StateWar 4.0: 国家间战争, 1816-2007
  - Formal Alliances 4.1: 正式同盟, 1816-2012
  - Territorial Change v6: 领土变更, 1816-2018
  - COW Country Codes: CCode -> State name 映射

只采事件骨架(不录入 events 表)——这是 Knowledge 层机器预填, 标注 machine-generated,
与你策展的阐释层共存。

依赖: 零 pip 包, stdlib csv+zipfile
用法:
  python cow_collector.py --mid-zip "C:/.../MID-5-Data-and-Supporting-Materials.zip" \
      --war-csv "C:/.../Inter-StateWarData_v4.0.csv" \
      --codes-csv "C:/.../COW-country-codes.csv"
"""
import os, sys, json, csv, zipfile, io, argparse
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_PATH = os.path.join(os.path.dirname(BASE_DIR), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, CA_PATH)
import canonical_actors as CA

OUTPUT_DIR = os.path.join(BASE_DIR, 'actor_timelines')

# COW hostility level -> 可读标签
HOSTLEV = {1: 'no militarized action', 2: 'threat to use force',
           3: 'display of force', 4: 'use of force', 5: 'war'}
FATALITY = {0: 'none', 1: '1-25', 2: '26-100', 3: '101-250',
            4: '251-500', 5: '501-999', 6: '>999'}


def load_cow_codes(csv_path):
    """COW CCode -> State name"""
    mapping = {}
    with open(csv_path, encoding='utf-8', newline='') as f:
        r = csv.reader(f); next(r)  # header
        for row in r:
            if len(row) >= 3:
                abb, code, name = row[0], row[1], row[2]
                try:
                    mapping[int(code)] = name.strip()
                except ValueError:
                    pass
    return mapping


def build_cow_to_canonical(cow_codes):
    """COW StateName -> canonical actor code (模糊前缀匹配)"""
    mapping = {}
    canonical_names = {a['name'].lower(): code for code, a in CA.CANONICAL_ACTORS.items()}
    for ccode, cname in cow_codes.items():
        cl = cname.lower()
        for canon_name, canon_code in canonical_names.items():
            if cl.startswith(canon_name) or canon_name.startswith(cl.split(',')[0]):
                mapping[ccode] = canon_code
                break
        # 手动别名 (COW 用名 vs canonical 用名)
        aliases = {
            'russia': 'RUS', 'russian federation': 'RUS', 'soviet union': 'RUS',
            'united states of america': 'USA', 'united kingdom': 'GBR',
            'china': 'CHN', "people's republic of china": 'CHN',
            'germany': 'DEU', 'france': 'FRA', 'japan': 'JPN',
            'india': 'IND', 'brazil': 'BRA', 'turkey': 'TUR',
            'iran': 'IRN', 'iraq': 'IRQ', 'saudi arabia': 'SAU',
            'israel': 'ISR', 'egypt': 'EGY', 'south korea': 'KOR',
            'north korea': 'PRK', 'pakistan': 'PAK',
            'ukraine': 'UKR', 'australia': 'AUS', 'canada': 'CAN',
            'italy': 'ITA', 'spain': 'ESP', 'mexico': 'MEX',
        }
        if ccode not in mapping and cl in aliases:
            mapping[ccode] = aliases[cl]
    return mapping


def load_midia(mid_zip_path):
    """MID MIDA: 争端级骨架 (dispnum, styear, endyear, hostlev, fatality, outcome)"""
    disputes = []
    with zipfile.ZipFile(mid_zip_path) as z:
        with z.open('MIDA 5.0.csv') as f:
            r = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
            for row in r:
                disputes.append(row)
    return disputes


def load_midb(mid_zip_path):
    """MID MIDB: 参与国级 (dispnum, ccode, sidea)"""
    parts = defaultdict(list)
    with zipfile.ZipFile(mid_zip_path) as z:
        with z.open('MIDB 5.0.csv') as f:
            r = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
            for row in r:
                try:
                    dn = int(row.get('dispnum', 0))
                    cc = int(row.get('ccode', 0))
                    sidea = row.get('sidea', '0') == '1'
                    parts[dn].append({'ccode': cc, 'initiator': sidea})
                except (ValueError, KeyError):
                    pass
    return parts


def load_war(war_csv_path):
    """Inter-StateWar: WarNum, WarName, ccode, StateName, Side, StartYear/EndYear"""
    wars = []
    with open(war_csv_path, encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            wars.append(row)
    return wars


def load_alliances(alliance_zip_path):
    """Formal Alliances: 同盟关系 dyad-year (ccode1, ccode2, defense/neutrality/entente, 起止年)"""
    alliances = []
    with zipfile.ZipFile(alliance_zip_path) as z:
        for n in z.namelist():
            if 'alliance_v4.1_by_dyad' in n and n.endswith('.csv'):
                with z.open(n) as f:
                    r = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                    for row in r:
                        alliances.append(row)
                break
    return alliances


def load_territorial(terr_zip_path):
    """Territorial Change v6: 领土变更 (gainer/loser/entity/area/year)"""
    changes = []
    with zipfile.ZipFile(terr_zip_path) as z:
        for n in z.namelist():
            if n.endswith('.csv'):
                with z.open(n) as f:
                    r = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                    for row in r:
                        changes.append(row)
    return changes


def build_skeleton(disputes, parts, wars, alliances, territorials, cow_to_canon):
    """聚合 COW 数据 -> {canonical_code: [skeleton_events]}"""
    skeleton = defaultdict(list)

    # MID 争端
    for disp in disputes:
        try:
            dn = int(disp.get('dispnum', 0))
            sty = int(disp.get('styear', 0))
            endy = int(disp.get('endyear', sty))
            hl = int(disp.get('hostlev', 0))
            fat = int(disp.get('fatality', -1))
        except (ValueError, KeyError):
            continue
        if sty < 1800:
            continue
        participants = parts.get(dn, [])
        involved_codes = set()
        for p in participants:
            code = cow_to_canon.get(p['ccode'])
            if code:
                involved_codes.add(code)

        entry = {
            'year_start': sty, 'year_end': endy,
            'type': 'MID',
            'hostility': HOSTLEV.get(hl, str(hl)),
            'fatalities': FATALITY.get(fat, str(fat)),
            'involved': sorted(involved_codes),
            'source': 'COW MID 5.0',
        }
        for code in involved_codes:
            skeleton[code].append(entry)

    # 战争
    for war in wars:
        try:
            sty = int(war.get('StartYear1', 0))
            endy = int(war.get('EndYear1', sty))
            cc = int(war.get('ccode', 0))
            name = war.get('WarName', '')
            side = war.get('Side', '1')
        except (ValueError, KeyError):
            continue
        if sty < 1800:
            continue
        code = cow_to_canon.get(cc)
        if not code:
            continue
        entry = {
            'year_start': sty, 'year_end': endy,
            'type': 'WAR',
            'label': name,
            'side': 'initiator' if side == '1' else 'joiner',
            'fatalities': 'see war-level',
            'source': 'COW Inter-StateWar 4.0',
        }
        skeleton[code].append(entry)

    # 同盟
    ALLIANCE_TYPE = {'defense': 'defense', 'neutrality': 'neutrality',
                     'nonaggression': 'nonaggression', 'entente': 'entente'}
    for al in alliances:
        try:
            sty = int(al.get('dyad_st_year', 0))
            endy = int(al.get('dyad_end_year', sty))
            cc1 = int(al.get('ccode1', 0))
            cc2 = int(al.get('ccode2', 0))
        except (ValueError, KeyError):
            continue
        if sty < 1800: continue
        types = [t for t in ['defense','neutrality','nonaggression','entente']
                 if al.get(t, '0') == '1']
        c1 = cow_to_canon.get(cc1)
        c2 = cow_to_canon.get(cc2)
        if c1 and c2:
            entry = {'year_start': sty, 'year_end': endy if endy > sty else sty,
                     'type': 'ALLIANCE', 'with': c2,
                     'alliance_type': types, 'source': 'COW Alliances 4.1'}
            skeleton[c1].append(entry)
            entry2 = dict(entry, **{'with': c1})
            skeleton[c2].append(entry2)

    # 领土变更
    for tc in territorials:
        try:
            yr = int(tc.get('year', 0))
            gainer = int(tc.get('gainer', 0))
            loser = int(tc.get('loser', 0))
            entity = tc.get('entity', '')
            procedur = tc.get('procedur', '')
            gaintype = tc.get('gaintype', '')
        except (ValueError, KeyError):
            continue
        if yr < 1800: continue
        gc = cow_to_canon.get(gainer)
        lc = cow_to_canon.get(loser)
        if gc:
            entry = {'year_start': yr, 'year_end': yr,
                     'type': 'TERR_GAIN', 'entity': entity,
                     'procedure': procedur, 'gain_type': gaintype,
                     'from': lc, 'source': 'COW Territorial Change v6'}
            skeleton[gc].append(entry)
        if lc:
            entry = {'year_start': yr, 'year_end': yr,
                     'type': 'TERR_LOSS', 'entity': entity,
                     'procedure': procedur, 'gain_type': gaintype,
                     'to': gc, 'source': 'COW Territorial Change v6'}
            skeleton[lc].append(entry)

    return skeleton


def main():
    ap = argparse.ArgumentParser(description='COW skeleton builder')
    ap.add_argument('--mid-zip',
        default=r'C:\Users\xheih\Downloads\新建文件夹\MID-5-Data-and-Supporting-Materials.zip')
    ap.add_argument('--war-csv',
        default=r'C:\Users\xheih\Downloads\新建文件夹\Inter-StateWarData_v4.0.csv')
    ap.add_argument('--codes-csv',
        default=r'C:\Users\xheih\Downloads\新建文件夹\COW-country-codes.csv')
    ap.add_argument('--alliance-zip',
        default=r'C:\Users\xheih\Downloads\新建文件夹\version4.1_csv.zip')
    ap.add_argument('--terr-zip',
        default=r'C:\Users\xheih\Downloads\terr-changes-v6.zip')
    ap.add_argument('--country-code', default=None,
        help='只生成单个主体 (如 CHN), 省略则全量')
    a = ap.parse_args()

    print('[COW] 加载数据...')
    cow_codes = load_cow_codes(a.codes_csv)
    cow_to_canon = build_cow_to_canonical(cow_codes)
    disputes = load_midia(a.mid_zip)
    parts = load_midb(a.mid_zip)
    wars = load_war(a.war_csv)
    alliances = load_alliances(a.alliance_zip)
    territorials = load_territorial(a.terr_zip)

    skeleton = build_skeleton(disputes, parts, wars, alliances, territorials, cow_to_canon)
    print(f'[COW] MIDs: {len(disputes)} disputes | Wars: {len(wars)}')
    print(f'[COW] Alliances: {len(alliances)} dyad-years | TerrChanges: {len(territorials)}')
    print(f'[COW] Mapped canonical codes: {len(cow_to_canon)} COW CCode -> canonical')
    print(f'[COW] Skeleton coverage: {len(skeleton)} canonical actors')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    targets = skeleton if not a.country_code else {a.country_code: skeleton.get(a.country_code, [])}

    built = 0
    for code, events in sorted(targets.items()):
        if not events:
            continue
        # 合并到现有 timeline (如果存在)
        tpath = os.path.join(OUTPUT_DIR, f'{code}.json')
        existing = {}
        if os.path.exists(tpath):
            with open(tpath, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        # 按年份排序 COW events
        events.sort(key=lambda e: e['year_start'])

        out = {
            'code': code,
            'name': CA.CANONICAL_ACTORS.get(code, {}).get('name', code),
            'skeleton_cow': events,
            'generated_at': datetime.now().isoformat(),
        }
        # 保留已有的 timeline_ucdp + recent_gdelt
        if 'timeline_ucdp' in existing:
            out['timeline_ucdp'] = existing['timeline_ucdp']
        if 'recent_gdelt' in existing:
            out['recent_gdelt'] = existing['recent_gdelt']
        if 'generated_at' in existing:
            out['ucdp_generated_at'] = existing['generated_at']

        with open(tpath, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        built += 1

    print(f'[COW] Done. {built} timelines written to {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
