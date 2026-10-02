# -*- coding: utf-8 -*-
"""给「全面战争」定阈值 —— 但【不发明】，而是锚在数据源自己的标准上。

UCDP 自身对「战争（war）」的定义是：**某一年战斗相关死亡 ≥ 1000**。
所以「印度无法对巴基斯坦发动全面战争」这条排除断言，可以用 UCDP 自己的门槛判：

    全面战争 ⟺ 该双边在某一年达到 UCDP 战争门槛（年度战斗死亡 ≥ 1000）

这比我自己拍一个数字好：口径来自数据源，不来自我。
"""
import csv
import io
import zipfile
from collections import defaultdict

ZIP = r"D:\Projects\地缘推演台\construct-stack\scripts\ged261-csv.zip"
NAMES = {"India": "IN", "Pakistan": "PK", "Ukraine": "UA",
         "Russia": "RU", "Soviet": "RU"}


def code_of(name: str):
    for k, v in NAMES.items():
        if k.lower() in (name or "").lower():
            return v
    return None


def run():
    # (pair, year) -> [events, deaths]
    agg = defaultdict(lambda: [0, 0])
    with zipfile.ZipFile(ZIP) as z, z.open("GEDEvent_v26_1.csv") as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
        for row in rdr:
            if row.get("type_of_violence") != "1":
                continue
            a, b = code_of(row.get("side_a")), code_of(row.get("side_b"))
            if not a or not b or a == b:
                continue
            pair = "-".join(sorted([a, b]))
            y = row.get("year") or "?"
            try:
                d = int(row.get("best") or 0)
            except ValueError:
                d = 0
            agg[(pair, y)][0] += 1
            agg[(pair, y)][1] += d
    return agg


if __name__ == "__main__":
    agg = run()
    for pair in ("IN-PK", "RU-UA"):
        print("=" * 78)
        print("  %s —— 按年（近 15 年 ＋ UCDP 战争门槛 1000 死/年）" % pair)
        print("  %-6s %8s %10s  %s" % ("年", "事件", "死亡(best)", "是否达 UCDP 战争门槛"))
        years = sorted({y for (p, y) in agg if p == pair and y.isdigit()})
        for y in years[-15:]:
            ev, d = agg[(pair, y)]
            mark = "★ 达门槛 ⇒ 构成「战争」" if d >= 1000 else ""
            print("  %-6s %8d %10d  %s" % (y, ev, d, mark))
        reached = [y for y in years if agg[(pair, y)][1] >= 1000]
        print("  ⇒ 达过 UCDP 战争门槛的年份：%s" % ("、".join(reached) if reached else "无"))
        print("  ⇒ 最近一次达门槛：%s" % (reached[-1] if reached else "从未"))
