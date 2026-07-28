#!/usr/bin/env python3
"""
ConStruct — 三层认知锚定可视化 (真实数据驱动)
=================================================
从 PG 读取 GDELT/UCDP 真实数据 + actor_timelines COW 骨架，
生成三层叠加时间轴 PNG。

三层:
  上层 — GDELT 近 30 天情绪脉冲 (bar, real-time)
  中层 — UCDP 1989–2025 冲突事件/死亡年序列 (bar+line)
  底层 — COW 1816–2014 冲突+同盟+领土骨架 (scatter timeline)

附"照妖镜"标注: GDELT 情绪骤降 + 主体间历史 TER_LOSS/MID 标记。

依赖: pip install matplotlib psycopg2-binary
用法: python visualize_three_layers.py CHN
"""
import os, sys, json, argparse
from datetime import datetime, timedelta
from collections import defaultdict

import psycopg2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'construct-stack', 'scripts'))
import canonical_actors as CA

DEFAULT_PG = 'postgresql://construct:construct_dev_2026@localhost:5432/construct'
OUTPUT_DIR = os.path.join(BASE, 'visuals')
TIMELINE_DIR = os.path.join(BASE, 'actor_timelines')

# 配色
C_GDELT_POS = '#2E7D32'
C_GDELT_NEG = '#C62828'
C_UCDP_EVENTS = '#1565C0'
C_UCDP_DEATHS = '#D32F2F'
C_COW_MID = '#42A5F5'
C_COW_WAR = '#E53935'
C_COW_ALLY = '#43A047'
C_COW_TERR_GAIN = '#8E24AA'
C_COW_TERR_LOSS = '#EF6C00'

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_gdelt(conn, code, days=30):
    """GDELT 近 30 天每日情绪脉冲"""
    cur = conn.cursor()
    cur.execute("""
        SELECT time::date, count(*), COALESCE(AVG(avg_tone),0)
        FROM events WHERE source='GDELT'
        AND (actor1_code=%s OR actor2_code=%s)
        AND time >= NOW() - interval '%s days'
        GROUP BY time::date ORDER BY time::date
    """, (code, code, days))
    rows = cur.fetchall()
    cur.close()
    return rows  # [(date, count, tone), ...]


def load_ucdp(conn, code, cname):
    """UCDP 1989–2025 年度事件数和死亡数"""
    cur = conn.cursor()
    cur.execute("""
        SELECT EXTRACT(YEAR FROM time)::int, count(*),
               COALESCE(SUM((metadata->>'deaths_best')::int), 0)
        FROM events WHERE source='UCDP' AND location ILIKE %s
        GROUP BY 1 ORDER BY 1
    """, (cname + '%',))
    rows = cur.fetchall()
    cur.close()
    return rows


def load_cow(code):
    """actor_timelines/{code}.json skeleton_cow"""
    path = os.path.join(TIMELINE_DIR, f'{code}.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('skeleton_cow', [])


def build_mirror_annotations(cow_events, gdelt_data):
    """照妖镜: GDELT 近 3 天情绪骤降 + 主体历史 TER_LOSS/MID 标记"""
    annotations = []
    # 近期情绪骤降
    if gdelt_data and len(gdelt_data) >= 3:
        recent = [t for _, _, t in gdelt_data[-3:]]
        if sum(recent) / 3 < -3.0:
            annotations.append(
                f'[照妖镜] 近 3 天 GDELT 情绪均值 {sum(recent)/3:.1f} (冲突警戒线 -2)')
    # 历史 TER_LOSS 数
    losses = [e for e in cow_events if e['type'] == 'TERR_LOSS']
    if losses:
        top = sorted(losses, key=lambda e: e['year_start'])
        annotations.append(
            f'[历史基线] 自 {top[0]["year_start"]} 年起共 {len(losses)} 次领土变更记录')
        recent_loss = [e for e in top if e['year_start'] >= 1900]
        if recent_loss:
            annotations.append(
                f'  最近: {recent_loss[-1]["year_start"]}年 {recent_loss[-1].get("entity","?")} → {recent_loss[-1].get("to","?")}')
    # 战争数
    wars = [e for e in cow_events if e['type'] == 'WAR']
    if wars:
        annotations.append(
            f'[冲突史] 1816–2014 参与 {len(wars)} 次国家间战争')
    return annotations


def draw(code, cname, gdelt_data, ucdp_data, cow_events, mirror_msgs, output_path):
    """生成三层叠加时间轴 PNG"""
    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(4, 1, height_ratios=[1.2, 1.2, 1.2, 0.6],
                          hspace=0.35, top=0.94, bottom=0.06)

    ax1 = fig.add_subplot(gs[0])  # GDELT
    ax2 = fig.add_subplot(gs[1])  # UCDP
    ax3 = fig.add_subplot(gs[2])  # COW
    ax_mirror = fig.add_subplot(gs[3])  # 照妖镜

    fig.suptitle(f'ConStruct 认知锚定 — {cname} ({code})',
                 fontsize=18, fontweight='bold', color='#0C447C')

    # ---- 上层: GDELT 30天 ----
    if gdelt_data:
        dates = [d[0] for d in gdelt_data]
        tones = [d[2] for d in gdelt_data]
        colors = [C_GDELT_POS if t >= 0 else C_GDELT_NEG for t in tones]
        ax1.bar(dates, tones, color=colors, alpha=0.75, width=0.8)
        ax1.axhline(y=0, color='#333', linewidth=0.8)
        ax1.axhline(y=-2, color='red', linestyle='--', linewidth=1, alpha=0.4, label='冲突警戒线')
        ax1.axhline(y=2, color='green', linestyle='--', linewidth=1, alpha=0.4, label='合作线')
        ax1.set_ylabel('Goldstein情绪', fontsize=11)
        ax1.set_title(f'上层: GDELT 近 30 天情绪脉冲 (事件数: {sum(d[1] for d in gdelt_data)})', fontsize=13)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(axis='y', alpha=0.2)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))

    # ---- 中层: UCDP ----
    if ucdp_data:
        years = [r[0] for r in ucdp_data]
        events = [r[1] for r in ucdp_data]
        deaths = [r[2] / 1000.0 for r in ucdp_data]  # k
        ax2b = ax2.twinx()
        ax2.bar(years, events, color=C_UCDP_EVENTS, alpha=0.5, label='事件数')
        ax2b.plot(years, deaths, color=C_UCDP_DEATHS, linewidth=1.8, marker='.', markersize=3, label='死亡(k)')
        ax2.set_ylabel('事件数', fontsize=11)
        ax2b.set_ylabel('死亡 (千人)', fontsize=11, color=C_UCDP_DEATHS)
        ax2.set_title(f'中层: UCDP 冲突事件/死亡 1989–2025 (总事件: {sum(events):,})', fontsize=13)
        ax2.legend(loc='upper left', fontsize=9)
        ax2b.legend(loc='upper right', fontsize=9)
        ax2.grid(axis='y', alpha=0.2)

    # ---- 底层: COW 骨架 ----
    if cow_events:
        type_pos = {'MID': 1, 'WAR': 2, 'ALLIANCE': 3, 'TERR_GAIN': 4, 'TERR_LOSS': 5}
        type_col = {'MID': C_COW_MID, 'WAR': C_COW_WAR, 'ALLIANCE': C_COW_ALLY,
                    'TERR_GAIN': C_COW_TERR_GAIN, 'TERR_LOSS': C_COW_TERR_LOSS}
        x_vals = []
        y_vals = []
        colors = []
        for e in cow_events:
            yr = (e['year_start'] + e.get('year_end', e['year_start'])) / 2
            x_vals.append(yr)
            y_vals.append(type_pos.get(e['type'], 0))
            colors.append(type_col.get(e['type'], '#999'))
        ax3.scatter(x_vals, y_vals, c=colors, alpha=0.5, s=12, edgecolors='none')
        ax3.set_yticks([1, 2, 3, 4, 5])
        ax3.set_yticklabels(['MID (争端)', 'WAR (战争)', 'ALLIANCE (同盟)', 'TERR+ (获得)', 'TERR− (丧失)'], fontsize=9)
        ax3.set_xlabel('年份', fontsize=11)
        ax3.set_title(f'底层: COW 200年骨架 — 冲突+同盟+领土 ({len(cow_events)} 事件)', fontsize=13)
        ax3.grid(axis='x', alpha=0.15)
        ax3.set_xlim(1800, 2030)

    # ---- 照妖镜 ----
    if mirror_msgs:
        ax_mirror.text(0.02, 0.5, '\n'.join(mirror_msgs), fontsize=10,
                       verticalalignment='center',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF8E1', alpha=0.9))
    ax_mirror.axis('off')
    ax_mirror.set_title('照妖镜: 历史基线 vs. 当下脉冲', fontsize=13, color='#C62828')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'[viz] -> {output_path}')


def main():
    ap = argparse.ArgumentParser(description='ConStruct three-layer visualizer')
    ap.add_argument('code', nargs='?', default='CHN', help='actor code')
    ap.add_argument('--pg', default=DEFAULT_PG)
    a = ap.parse_args()

    code = a.code
    cname = CA.CANONICAL_ACTORS.get(code, {}).get('name', code)

    conn = psycopg2.connect(a.pg)
    gdelt_data = load_gdelt(conn, code)
    ucdp_data = load_ucdp(conn, code, cname)
    conn.close()

    cow_events = load_cow(code)
    mirror_msgs = build_mirror_annotations(cow_events, gdelt_data)

    print(f'[{code}] GDELT 30d: {len(gdelt_data)} days | UCDP: {len(ucdp_data)} years | COW: {len(cow_events)} events')
    for msg in mirror_msgs:
        print(f'  {msg}')

    output_path = os.path.join(OUTPUT_DIR, f'{code}_timeline.png')
    draw(code, cname, gdelt_data, ucdp_data, cow_events, mirror_msgs, output_path)


if __name__ == '__main__':
    main()
