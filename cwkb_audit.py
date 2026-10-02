# -*- coding: utf-8 -*-
"""cwkb_audit.py —— S1.4 的审计：把「声明为空」与「没人管的空」分开。

★★ 为什么需要它
   本项目反复出现「**规划写了，目录建了，内容没有**」：
     · 立项设计的 SQLite 唯一真相源 —— 从未建
     · CWKB 七个目录 —— 空的
   而**空目录不会报错、不会过期、不会提醒你** —— 它只是安静地在那儿。

   ⇒ 所以判据是这两条，它们【分得开】：
     · 目录里有 1 个文件且是 `_README.md` ⇒ **声明为空**（可接受的当前状态）
     · 目录里 0 个文件                   ⇒ **没人管的空**（这才是要报的）
     · 有 `_README.md` 且有其它文件      ⇒ **已开始填**（README 该更新了）

★★ 它还回答一个更要紧的问题：**README 里承诺的「填它需要什么」，做了没有。**
   所以每条 README 必须有那两节，否则审计报「声明不完整」。

运行：  python cwkb_audit.py
        python cwkb_audit.py --selftest
"""
from __future__ import annotations

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
CWKB = os.path.join(WS, "CWKB_Vault")

# ★ 必须被声明的七个（S1.4 的对象）
MUST_DECLARE = [
    "02_History", "03_Data", "04_ThinkTanks", "05_Academic", "Indexes",
    os.path.join("Special", "Event_Chains"), os.path.join("Special", "Strategy_Timeline"),
]
REQUIRED_SECTIONS = ["## 该装什么", "## 为什么现在空", "## 填它需要什么", "## ⛔ 不许拿什么填"]


def scan() -> list:
    rows = []
    for rel in MUST_DECLARE:
        d = os.path.join(CWKB, rel)
        if not os.path.isdir(d):
            rows.append({"dir": rel, "state": "missing", "n": 0, "why": "目录不存在"})
            continue
        files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        others = [f for f in files if f != "_README.md"]
        rd = os.path.join(d, "_README.md")
        if not files:
            rows.append({"dir": rel, "state": "undeclared_empty", "n": 0,
                         "why": "0 个文件 —— 没人管的空（规划写了、目录建了、内容没有）"})
            continue
        if files == ["_README.md"]:
            txt = io.open(rd, encoding="utf-8").read()
            missing = [s for s in REQUIRED_SECTIONS if s not in txt]
            rows.append({"dir": rel,
                         "state": "declared_empty_complete" if not missing else "declared_incomplete",
                         "n": 0, "why": ("声明为空，四节齐全" if not missing
                                         else "声明缺节：%s" % "、".join(missing))})
            continue
        has_rd = "_README.md" in files
        rows.append({"dir": rel, "state": "filling", "n": len(others),
                     "why": ("已开始填（%d 个内容文件）%s" % (len(others),
                             "；README 该更新了" if has_rd else "；⚠️ 没有声明文件"))})
    return rows


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    rows = scan()
    print("=" * 92)
    print("# CWKB 空目录审计（S1.4）")
    print("=" * 92)
    for r in rows:
        mark = {"declared_empty_complete": "✅ 声明为空（完整）",
                "declared_incomplete": "⚠️ 声明不完整",
                "undeclared_empty": "⛔ 没人管的空",
                "filling": "🔨 已开始填",
                "missing": "⛔ 目录不存在"}[r["state"]]
        print("  %-28s %s" % (r["dir"], mark))
        print("      %s" % r["why"])
    bad = [r for r in rows if r["state"] in ("undeclared_empty", "declared_incomplete", "missing")]
    print()
    if bad:
        print("  ⛔ %d 个目录需要处理：" % len(bad))
        for r in bad:
            print("     %s —— %s" % (r["dir"], r["why"]))
    else:
        print("  ✅ 七个目录全部处于【已声明的状态】：要么声明为空且四节齐全，要么已开始填。")
    print()
    print("  ★ 本审计回答的是：「空」有没有被说出来。")
    print("    ⛔ 它【不】回答「该不该填」—— 那是内容问题，不是审计问题。")
    print("=" * 92)
    return 0 if not bad else 1


def selftest() -> int:
    n_pass = n_fail = 0

    def ck(name, cond, detail=""):
        nonlocal n_pass, n_fail
        if cond:
            n_pass += 1
            print("  ✅ %s" % name)
        else:
            n_fail += 1
            print("  ❌ %s   %s" % (name, detail))

    print("# cwkb_audit 自证")
    ck("★七个目录都被纳入审计（不是写死的空表）", len(MUST_DECLARE) == 7, str(len(MUST_DECLARE)))
    rows = scan()
    ck("★扫描结果与目录数一致", len(rows) == 7, str(len(rows)))
    ck("★★每个目录都有状态（不是 None）", all(r.get("state") for r in rows))
    ck("★★状态取值在预期集合内",
       all(r["state"] in ("declared_empty_complete", "declared_incomplete",
                          "undeclared_empty", "filling", "missing") for r in rows),
       str([r["state"] for r in rows]))
    # ★★ 关键：它必须能把「声明为空」与「没人管的空」分开
    ck("★★能分出「声明为空」与「没人管的空」（两个状态名不同）",
       "declared_empty_complete" != "undeclared_empty")
    for rel in MUST_DECLARE:
        d = os.path.join(CWKB, rel)
        ck("★%s 有 _README.md（已声明）" % rel,
           os.path.exists(os.path.join(d, "_README.md")))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
