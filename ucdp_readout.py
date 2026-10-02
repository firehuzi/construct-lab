# -*- coding: utf-8 -*-
"""ucdp_readout.py —— 用 UCDP GED v26.1 造一个【覆盖到 2025】的外部量

═══ 为什么换数据源 ═══════════════════════════════════════════════════════════
第 5 步查出：原来的外部量（COW 骨架）最新只到 2014–2020，而档案的方向基线是
2026 年的判断 ⇒ 口径错位 11–12 年 ⇒ 那条检验【这一版测不了】。

而磁盘上一直躺着一份没被接进去的数据：
  `construct-stack/scripts/ged261-csv.zip` → `GEDEvent_v26_1.csv`
  **UCDP GED v26.1，417,968 条事件，年份 1992 → 2025**
  （`actor_timelines` 的骨架里【没有 UCDP 来源】——它最大年只到 2014）

⇒ 口径错位从 12 年降到 **1 年**（2025 vs 2026）。

═══ 读出口的构造 ═══════════════════════════════════════════════════════════
「方向扩张性」= 战略方向 ↑扩张／→维持／↓收缩。扩张的直接外部表现是
【把武力投到本国之外】。UCDP GED 恰好能逐条算出来：

  abroad(y) = 该主体作为 side_a、type_of_violence==1（国家间/国家对组织的有组织暴力）、
              且【事件发生国 ≠ 主体本国】（country_id ≠ gwnoa）的事件数

对照它的反面：
  home(y)   = 同口径，但事件发生在本国境内

  R5 对外投射强度 = 最近三年 abroad 之和
  R6 对外投射趋势 = abroad(近三年) − abroad(前三年)   ← 「方向」是变化量，故也报趋势

运行：  python ucdp_readout.py --build     # 流式扫 274 MB CSV（约 1 分钟），落 data/ucdp_actors.json
        python ucdp_readout.py             # 用缓存出结论
        python ucdp_readout.py --selftest
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIP = os.path.join(ROOT, "construct-stack", "scripts", "ged261-csv.zip")
MEMBER = "GEDEvent_v26_1.csv"
OUT = os.path.join(HERE, "data", "ucdp_actors.json")

# 主体名关键词 → 八维主体码。⚠️ 顺序有讲究（North Korea 必须在 Korea 之前）。
NAME_HINTS = [
    ("United States", "US"), ("Russia", "RU"), ("Soviet", "RU"), ("China", "CN"),
    ("Japan", "JP"), ("Germany", "DE"), ("France", "FR"),
    ("United Kingdom", "GB"), ("India", "IN"), ("Iran", "IR"), ("Israel", "IL"),
    ("Egypt", "EG"), ("Pakistan", "PK"), ("North Korea", "KP"), ("Korea", "KR"),
    ("Singapore", "SG"), ("Serbia", "RS"), ("Yugoslav", "RS"), ("Ukraine", "UA"),
    ("Australia", "AUS"), ("Italy", "IT"), ("Spain", "ES"), ("Iraq", "IQ"),
    ("Turkey", "TR"), ("Saudi", "SA"), ("Taiwan", "TW"), ("Vietnam", "VN"),
    ("Philippines", "PH"), ("Mexico", "MX"), ("Brazil", "BR"), ("Canada", "CA"),
]


def hint(name: str):
    for k, code in NAME_HINTS:
        if k.lower() in (name or "").lower():
            return code
    return None


def hints_all(name: str) -> set:
    """★ 取出名称里命中的【全部】主体码 —— 两侧都要算，且要处理联盟列表。
    为什么：俄乌成对时俄是 side_a、乌是 side_b ⇒ 只数 side_a 会【系统性漏掉防御方】。
    而 side_b 可能是联盟串（"Government of United Kingdom, Government of United
    States of America, …"）⇒ 必须全部取出，不能只取第一个。
    """
    return {code for k, code in NAME_HINTS if k.lower() in (name or "").lower()}


def build() -> int:
    """流式扫 GED 两遍：
    ① 导表：side_a 名 → 主体码（NAME_HINTS）；主体码 → 本国 GW 码（从 gwnoa 众数）
    ② 统计：按 (主体码, 年) 分 home / abroad

    ⚠️ 第一版我要求 `gwnoa` 非空 —— 结果 US 全为 0。原因：全表 25% 的行 gwnoa 为空，
       而「Government of United States of America - al-Qaida」这类【对外投射】行
       恰恰就在那 25% 里。改为【只看 side_a 能否映射到主体】，
       本国码从【有 gwnoa 的行】里自导，而不是硬记 GW 码表。
    """
    gw_name = defaultdict(Counter)
    code_gw = defaultdict(Counter)
    n = 0
    with zipfile.ZipFile(ZIP) as z, z.open(MEMBER) as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
        for row in rdr:
            n += 1
            if row.get("type_of_violence") != "1":
                continue
            name = row.get("side_a") or ""
            code = hint(name)
            if not code:
                continue
            gw = (row.get("gwnoa") or "").strip()
            if gw:
                gw_name[gw][name] += 1
                code_gw[code][gw] += 1

    own = {c: (cnt.most_common(1)[0][0] if cnt else None) for c, cnt in code_gw.items()}

    per = defaultdict(lambda: defaultdict(lambda: {"abroad": 0, "home": 0, "unknown": 0,
                                                   "deaths_abroad": 0}))
    # ★ 双边对计数：type-1 事件里，两个主体同时出现的年份分布。
    #   为什么要它：排除性断言常是【双边】的（「印度无法对巴基斯坦发动全面战争」），
    #   而 per-actor 计数判不了这种断言。UCDP 覆盖到 2025，能判 2020+ 的窗口。
    pairs = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(ZIP) as z, z.open(MEMBER) as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
        for row in rdr:
            if row.get("type_of_violence") != "1":
                continue
            codes = set()
            for col in ("side_a", "side_b"):
                codes |= hints_all(row.get(col))
            if not codes:
                continue
            y = row.get("year") or "?"
            cid = (row.get("country_id") or "").strip()
            best = 0
            try:
                best = int(row.get("best") or 0)
            except ValueError:
                best = 0
            for code in codes:
                b = per[code][y]
                if not cid or own.get(code) is None:
                    b["unknown"] += 1
                elif cid == own[code]:
                    b["home"] += 1
                else:
                    b["abroad"] += 1
                    b["deaths_abroad"] += best
            if len(codes) >= 2:
                for x, yy in combinations(sorted(codes), 2):
                    pairs["%s-%s" % (x, yy)][y] += 1

    data = {"source": "UCDP GED v26.1", "rows_scanned": n,
            "own_gw": own,
            "gw_names": {k: v.most_common(1)[0][0] for k, v in gw_name.items()},
            "pairs": {k: dict(sorted(v.items())) for k, v in sorted(pairs.items())},
            "actors": {c: dict(sorted(ys.items())) for c, ys in sorted(per.items())}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("扫描 %d 行 → %s（%d 个主体）" % (n, os.path.relpath(OUT, ROOT), len(data["actors"])))
    print("自导本国 GW 码：%s" % json.dumps(own, ensure_ascii=False))
    return 0


def load() -> dict:
    with open(OUT, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    if "--build" in sys.argv:
        return build()
    if "--selftest" in sys.argv:
        return selftest()
    d = load()
    print("=" * 92)
    print("# UCDP GED v26.1 外部量（%s）" % d["source"])
    print("=" * 92)
    print("  扫描行数 = %d　主体数 = %d" % (d["rows_scanned"], len(d["actors"])))
    print("\n  %-6s %-38s %6s %6s %7s %7s" % ("码", "UCDP 里的主体名", "2023", "2024", "2025", "本国2025"))
    for code, ys in sorted(d["actors"].items()):
        r = lambda y: ys.get(str(y), {}).get("abroad", 0)
        h = ys.get("2025", {}).get("home", 0)
        name = ""
        for gw, nm in d["gw_names"].items():
            if hint(nm) == code:
                name = nm
                break
        print("  %-6s %-38s %6d %6d %7d %7d"
              % (code, name[:38], r(2023), r(2024), r(2025), h))
    return 0


def selftest() -> int:
    n_pass = n_fail = 0

    def check(name, cond, detail=""):
        nonlocal n_pass, n_fail
        if cond:
            n_pass += 1
            print("  ✅ %s" % name)
        else:
            n_fail += 1
            print("  ❌ %s   %s" % (name, detail))

    print("# ucdp_readout 自证")
    check("hint：俄罗斯 ⇒ RU", hint("Government of Russia (Soviet Union)") == "RU")
    check("hint：苏联 ⇒ RU", hint("Government of Soviet Union") == "RU")
    check("hint：朝鲜优先于韩国（North Korea ⇒ KP）",
          hint("Government of North Korea") == "KP", str(hint("Government of North Korea")))
    check("hint：韩国 ⇒ KR", hint("Government of South Korea") == "KR")
    check("hint：美国 ⇒ US", hint("Government of United States of America") == "US")
    check("hint：不认识的名字 ⇒ None", hint("Jalisco Cartel New Generation") is None)
    if os.path.exists(OUT):
        d = load()
        check("缓存存在且非空", len(d["actors"]) > 10, str(len(d["actors"])))
        check("★年份覆盖到 2023 以后（这是换数据源的全部理由）",
              any(str(y) >= "2023" for ys in d["actors"].values() for y in ys))
    else:
        print("  ⚠️ 未找到缓存，跳过缓存检查（先跑 --build）")
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
