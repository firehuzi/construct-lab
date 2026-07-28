#!/usr/bin/env python3
"""
ConStruct — ACLED 冲突事件采集器
===================================
ACLED API v2: Email+Password → OAuth Token → 分页拉取全量事件
→ PG events 表 (source='ACLED', verification=pending, 数据独立于 UCDP/GDELT)

认证: 无 IP 限制, Token 24h 有效, Refresh Token 14d
依赖: pip install requests psycopg2-binary (requests 进 venv)
用法:
  python acled_collector.py --email xx@xx.com --password xxx
  python acled_collector.py --email xx@xx.com --password xxx --dry-run
"""

import os, sys, json, time, argparse
from datetime import datetime

import requests
import psycopg2

BASE = os.path.dirname(os.path.abspath(__file__))
# 引入 canonical_actors 映射
CA_PATH = os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts')
if CA_PATH not in sys.path:
    sys.path.insert(0, CA_PATH)
import canonical_actors as CA

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
ACLED_AUTH_URL = 'https://acleddata.com/oauth/token'
ACLED_API_URL = 'https://acleddata.com/api/acled/read'
TOKEN_FILE = os.path.join(os.path.dirname(BASE), 'construct-stack', 'cache', 'acled_token.json')

# country name → canonical code 快速映射
COUNTRY_TO_CODE = {}
for code, a in CA.CANONICAL_ACTORS.items():
    COUNTRY_TO_CODE[a['name'].lower()] = code
    # 别名
    aliases = {
        'russia': 'RUS', 'china': 'CHN', 'united states': 'USA', 'united kingdom': 'GBR',
        'germany': 'DEU', 'france': 'FRA', 'japan': 'JPN', 'india': 'IND',
        'iran': 'IRN', 'iraq': 'IRQ', 'israel': 'ISR', 'egypt': 'EGY',
        'south korea': 'KOR', 'north korea': 'PRK', 'turkey': 'TUR',
        'saudi arabia': 'SAU', 'pakistan': 'PAK', 'ukraine': 'UKR',
        'australia': 'AUS', 'brazil': 'BRA', 'philippines': 'PHL',
        'vietnam': 'VNM', 'canada': 'CAN', 'mexico': 'MEX',
    }
    for alias, c in aliases.items():
        COUNTRY_TO_CODE[alias] = c


def get_token(email, password):
    """获取 ACLED OAuth Token (优先读缓存, 过期则刷新)"""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    # 尝试读缓存
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                cached = json.load(f)
            if cached.get('email') == email and cached.get('expires_at', 0) > time.time() + 3600:
                print(f'[ACLED] 使用缓存 Token (有效期至 {datetime.fromtimestamp(cached["expires_at"]).strftime("%H:%M")})')
                return cached['access_token']
        except (json.JSONDecodeError, KeyError):
            pass

    print('[ACLED] 获取新 OAuth Token...')
    resp = requests.post(ACLED_AUTH_URL, data={
        'username': email, 'password': password,
        'grant_type': 'password', 'client_id': 'acled', 'scope': 'authenticated',
    }, timeout=30)
    if resp.status_code != 200:
        print(f'[ACLED] 认证失败 HTTP {resp.status_code}: {resp.text[:300]}')
        return None
    data = resp.json()
    token = data.get('access_token')
    if not token:
        print(f'[ACLED] Token 响应缺失: {json.dumps(data)[:200]}')
        return None
    expires_in = data.get('expires_in', 86400)
    with open(TOKEN_FILE, 'w') as f:
        json.dump({
            'email': email, 'access_token': token,
            'expires_at': time.time() + expires_in,
            'refresh_token': data.get('refresh_token'),
        }, f)
    print(f'[ACLED] Token 获取成功 ({expires_in}s 有效)')
    return token


def fetch_events(email, password, target_countries=None, max_pages=10):
    """分页拉取 ACLED 事件 (每页 5000 条, 不计速率限制)"""
    token = get_token(email, password)
    if not token:
        return []
    headers = {'Authorization': f'Bearer {token}'}
    all_events = []
    page = 0
    params = {'limit': 5000}
    if target_countries:
        params['country'] = '|'.join(target_countries)
    while page < max_pages:
        url = ACLED_API_URL
        if page > 0:
            params['page'] = page
        resp = requests.get(url, params=params, headers=headers, timeout=120)
        if resp.status_code == 401:
            # Token 过期, 重新获取
            print('[ACLED] Token 过期, 刷新...')
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            token = get_token(email, password)
            if not token:
                break
            headers = {'Authorization': f'Bearer {token}'}
            continue
        if resp.status_code != 200:
            print(f'[ACLED] API 错误 HTTP {resp.status_code}: {resp.text[:300]}')
            break
        data = resp.json()
        if isinstance(data, list):
            batch = data
        elif 'data' in data:
            batch = data['data']
        else:
            print(f'[ACLED] 未知响应格式 page={page}')
            break
        if not batch:
            break
        all_events.extend(batch)
        page += 1
        sys.stdout.write(f'\r[ACLED] page={page} events={len(all_events)}')
        sys.stdout.flush()
        if len(batch) < 5000:
            break  # 最后一页
    sys.stdout.write('\n')
    return all_events


def match_subject(ev):
    """ACLED 事件 → canonical actor code (按 country 字段)"""
    country = (ev.get('country', '') or '').lower()
    if country in COUNTRY_TO_CODE:
        return COUNTRY_TO_CODE[country]
    # 前缀匹配
    for cname, code in COUNTRY_TO_CODE.items():
        if country.startswith(cname):
            return code
    return None


def event_to_record(ev):
    """ACLED JSON → PG events 行"""
    code = match_subject(ev)
    if not code:
        return None
    ts = ev.get('event_date', '')  # YYYY-MM-DD
    if not ts:
        return None
    acled_id = str(ev.get('data_id', ev.get('event_id_cnty', '')))
    # ACLED 事件类型映射到 action 码
    etype = ev.get('event_type', '')
    act_map = {'Battles': '190', 'Explosions/Remote violence': '180',
               'Violence against civilians': '200', 'Protests': '140', 'Riots': '145',
               'Strategic developments': '050'}
    action = act_map.get(etype, '190')
    # Goldstein scale 估算 (基于 ACLED 事件类型)
    gs_map = {'Battles': -7.0, 'Explosions/Remote violence': -8.0,
              'Violence against civilians': -9.0, 'Protests': -3.0,
              'Riots': -5.0, 'Strategic developments': -1.0}
    gs = gs_map.get(etype, -5.0)
    sub_type = ev.get('sub_event_type', '') or ''
    fatalities = int(ev.get('fatalities', 0) or 0)

    return {
        'time': ts,
        'source': 'ACLED',
        'source_id': f'ACLED-{acled_id}',
        'source_ref': 'ACLED',
        'actor1_code': code,
        'actor2_code': None,
        'action': action,
        'goldstein_scale': gs,
        'avg_tone': gs / 10.0,
        'confidence': 0.75,  # ACLED 人工编码, 置信度高
        'event_class': 'actor',
        'domain': None,
        'summary': f'{etype}: {sub_type} ({fatalities} deaths)',
        'url': f'https://acleddata.com/data/{acled_id}',
        'metadata': json.dumps({'acled_type': etype, 'sub_type': sub_type,
                                'fatalities': fatalities, 'region': ev.get('region',''),
                                'location': ev.get('location',''), 'source_scale': ev.get('source_scale','')}),
    }


def insert_to_pg(events, pg_dsn, dry_run=False):
    """批量 INSERT 到 PG (ON CONFLICT 去重)"""
    conn = psycopg2.connect(pg_dsn)
    cur = conn.cursor()
    n = 0
    for ev in events:
        rec = event_to_record(ev)
        if not rec:
            continue
        if dry_run:
            n += 1
            continue
        cur.execute("""
            INSERT INTO events (time, source, source_id, source_ref, actor1_code, actor2_code,
                action, goldstein_scale, avg_tone, confidence, event_class, domain,
                verification_status, summary, url, metadata)
            VALUES (%s,'ACLED',%s,'ACLED',%s,%s,%s,%s,%s,%s,'actor',NULL,'pending',%s,%s,%s)
            ON CONFLICT (time, source_id) DO UPDATE
            SET metadata=EXCLUDED.metadata, summary=EXCLUDED.summary,
                fatalities=(EXCLUDED.metadata->>'fatalities')::int
        """, (rec['time'], rec['source_id'], rec['actor1_code'], rec['actor2_code'],
              rec['action'], rec['goldstein_scale'], rec['avg_tone'], rec['confidence'],
              rec['summary'], rec['url'], rec['metadata']))
        n += 1
    conn.commit()
    cur.close()
    conn.close()
    action = ' (dry-run)' if dry_run else ''
    print(f'[ACLED] 写入 PG: {n} 行{action}')


def main():
    ap = argparse.ArgumentParser(description='ACLED collector')
    ap.add_argument('--email', default=os.environ.get('ACLED_EMAIL', ''))
    ap.add_argument('--password', default=os.environ.get('ACLED_PASSWORD', ''))
    ap.add_argument('--pg', default=DEFAULT_PG)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max-pages', type=int, default=20, help='最大拉取页数 (每页 5000 条)')
    a = ap.parse_args()

    if not a.email or not a.password:
        print('[ERROR] 需要 --email 和 --password, 或设置 ACLED_EMAIL/ACLED_PASSWORD 环境变量')
        return

    print(f'[ACLED] 连接 ACLED API...')
    target_countries = [a['name'] for a in CA.CANONICAL_ACTORS.values()]  # 拉取 47 主体
    events = fetch_events(a.email, a.password, target_countries, a.max_pages)
    if not events:
        print('[ACLED] 未获取到事件 (检查账户是否通过审核)')
        return

    print(f'[ACLED] 获取事件: {len(events)} 条 (max_pages={a.max_pages})')
    insert_to_pg(events, a.pg, a.dry_run)


if __name__ == '__main__':
    main()
