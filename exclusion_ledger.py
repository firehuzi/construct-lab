# -*- coding: utf-8 -*-
"""exclusion_ledger.py —— 「不可能路径」账（排除性断言）

★★ 由来
  用户 2026-09-28 的文章把框架的判据定义清楚了：

    「ConStruct Lab 不发布选举预测……我们做的事更基础，也更困难：
      **揭示哪些路径在逻辑上不可能**。」
    「预测需要知道未来。诊断只需要理解当下。」

  ⇒ 「解释」= **标记逻辑上不可能的路径**。这比预测好测得多：
     不需要未来数据，只需要【排除】。

★★ 一条硬规矩（否则它不可证伪）
  「X 不可能」是【单向可证伪】的：
    X 发生了      ⇒ 断言被证伪 ✅ 有信息
    X 没发生      ⇒ 只能说「**尚未被证伪**」，【不能】说断言被证实
  所以每条断言必须有【声明日期】（"至今"才有意义）与【窗口】。
  没窗口的标「不可判」，不冒充判过。

★★ 用户的关键判断（已记入）
  「之前所有案例是在数据层基础设施不完善的情况下的推演 —— 但现在做也有好处：
    在数据不充分的情况下推演可能更有意义，**可以证明结构分析方法的可行性**。」
  ⇒ 本账的判定分档刻意区分「数据不够判」与「断言本身不可判」——
    前者是数据问题，后者是方法问题。混为一谈就看不出方法可行不可行。

运行：  python exclusion_ledger.py            # 算账
        python exclusion_ledger.py --selftest
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TIMELINES = os.path.join(HERE, "actor_timelines")

# ══ 断言登记表（从 scan_exclusions.py 的 142 条候选里逐条挑出的真断言）══════════
# window：判定窗口（起于声明日期）
# check：机器可判时用哪种核对；否则 None ⇒ 标「待判（缺证据层）」
E = [
    dict(id="X-01", actor="欧盟", claim="欧洲不可能实现无人机生产自主化",
         why="其对华关键材料依赖难以克服",
         src="ConStruct_Archive/Scenarios/Scenario_004_Russia_Ukraine.md",
         window="5年", check=None),
    dict(id="X-02", actor="俄/乌", claim="俄乌双方无人机生产都无法脱离中国供应链",
         why="中国掌控全球无人机生产",
         src="ConStruct_Archive/Scenarios/Scenario_004_Russia_Ukraine.md",
         window="3年", check=None),
    dict(id="X-03", actor="伊朗", claim="伊朗不可能承认以色列",
         why="「消灭犹太复国主义政权」是革命身份的核心条款",
         src="content/articles/IRN_structure_article_2026-07-28.md",
         window="至今", check="fact:record"),
    dict(id="X-04", actor="伊朗", claim="伊朗不可能主动解散真主党或停止支持胡塞武装",
         why="这是革命输出的核心机制",
         src="content/articles/IRN_structure_article_2026-07-28.md",
         window="至今", check=None),
    dict(id="X-05", actor="欧盟", claim="欧盟不可能同时维持对北约依赖与建设独立军事能力",
         why="两者在资源分配上直接冲突",
         src="content/articles/EU_structure_article_2026-07-28.md",
         window="5年", check=None),
    dict(id="X-06", actor="日本", claim="日本无法在台湾问题上采取独立行动",
         why="美日同盟把台湾问题嵌入美国安全承诺",
         src="content/articles/JPN_structure_article_2026-07-28.md",
         window="5年", check=None),
    dict(id="X-07", actor="印度/巴基斯坦", claim="巴基斯坦的核武器使印度无法发动全面战争",
         why="核威慑冻结",
         src="ConStruct_Archive/Scenarios/Scenario_005_India_Pakistan.md",
         window="至今", check="ucdp:IN-PK:2020"),
    dict(id="X-08", actor="中国", claim="中国无法在北极理事会中拥有正式决策权",
         why="中国不是北极国家",
         src="ConStruct_Archive/Scenarios/Scenario_006_Arctic.md",
         window="至今", check="fact:record"),
    dict(id="X-09", actor="美国/中国", claim="美国无法将中国排除在拉美之外",
         why="结构性优势不可撼动",
         src="ConStruct_Archive/Scenarios/Scenario_007_Latin_America.md",
         window="5年", check=None),
    dict(id="X-10", actor="中国", claim="中国的 scope 递增 ⇒ 不可能回退到更小的 scope",
         why="每个 scope 比上一个大",
         src="ConStruct_Archive/Tier1/China.md",
         window="至今", check=None),
    dict(id="X-11", actor="塞尔维亚", claim="摆荡式建构使其无法选边（在欧盟与中国之间）",
         why="任何选边都是身份自杀",
         src="WB/20260327221200/out/wechat/2026-09-28-为什么地缘政治分析总是失败.md",
         window="至今", check="fact:record"),
    dict(id="X-12", actor="新加坡", claim="冻结局无法处理外部输入的正向情感",
         why="冻结局最怕的不是敌人，是温暖",
         src="WB/20260327221200/out/wechat/2026-09-28-为什么地缘政治分析总是失败.md",
         window="至今", check=None),
    dict(id="X-13", actor="法国", claim="法国无法承受殖民式战争的国内政治成本",
         why="阿尔及利亚的教训",
         src="content/articles/FRA_structure_article_2026-07-28.md",
         window="至今", check=None),
    dict(id="X-14", actor="韩国", claim="韩国被锁在两个方向，无法放弃任何一个",
         why="双锚夹层",
         src="ConStruct_Archive/Tier2/South_Korea.md",
         window="5年", check=None),
    dict(id="X-15", actor="土耳其", claim="土耳其无法决定自己是欧洲国家还是中东国家",
         why="身份撕扯",
         src="ConStruct_Archive/Tier2/Turkey.md",
         window="5年", check=None),
    dict(id="X-16", actor="乌克兰", claim="乌克兰在地面无法取得决定性突破",
         why="双方消耗战结构",
         src="ConStruct_Archive/Scenarios/Scenario_004_Russia_Ukraine.md",
         window="2年", check="ucdp:UA-RU:2023"),
    dict(id="X-17", actor="欧盟", claim="任何打破锁死的尝试都=修改 Identity 核心=EU 死亡 ⇒ 锁死无法从内部打破",
         why="共识即身份",
         src="WB/2026-06-09-17-25-25/ConStruct_MultiPath_001_EU_Future.md",
         window="5年", check=None),
    dict(id="X-18", actor="美国/伊朗", claim="美伊协议（60天窗口期）无法触及教派裂痕／抵抗之弧／大以色列三层",
         why="只能管理国家间博弈那一层",
         src="ConStruct_Archive/Scenarios/Scenario_003_Middle_East_Supplement.md",
         window="60天", check=None),
]


# ══ 核对引擎 ════════════════════════════════════════════════════════════════════
STATE_FALSIFIED = "⛔ 已被证伪"
STATE_UNFALSIFIED = "⏳ 尚未被证伪"
STATE_NEED_EVIDENCE = "❓ 待判（缺证据层）"
STATE_UNDECIDABLE = "⚠️ 不可判（断言缺窗口／路径不清）"
# ★ 下面两档是【用户让我做的这件事的核心区分】——
#   「数据不够」是数据层缺口；「断言需先定阈值」是方法本身的问题。
#   混在一起就看不出方法可行不可行。
STATE_NO_DATA = "📉 数据不够（断言可判，卡在数据层）"
STATE_NEED_THRESHOLD = "🔧 断言需先定阈值（卡在方法，不是数据）"

UCDP = os.path.join(HERE, "data", "ucdp_actors.json")


def _pairs() -> dict:
    if not os.path.exists(UCDP):
        return {}
    with open(UCDP, encoding="utf-8") as fh:
        return (json.load(fh) or {}).get("pairs", {}) or {}


def check_ucdp_bilateral(a: str, b: str, since: int, threshold=None) -> dict:
    """用 UCDP GED（覆盖到 2025）核对【双边】排除断言。
    ★ 与 COW 骨架的关键差别：UCDP 覆盖 2020+，窗口能落进数据里。

    三种结果必须分清：
      · 窗口内有事件且【已达阈值】  ⇒ 证伪
      · 窗口内无事件                ⇒ 尚未被证伪
      · 有事件但【没定阈值】        ⇒ 判不了，且这是【方法问题】不是数据问题
    """
    ys = _pairs().get("-".join(sorted([a, b])))
    if ys is None:
        return {"ok": None, "kind": "nodata",
                "ev": "UCDP 里没有 %s-%s 这个双边对 ⇒ 不可判" % (a, b)}
    n = sum(v for y, v in ys.items() if y >= str(since))
    last = max(ys)
    if n == 0:
        return {"ok": False, "kind": "none",
                "ev": "UCDP 覆盖到 %s，%d 年起窗口内 0 条 ⇒ 尚未被证伪" % (last, since)}
    if threshold is None:
        return {"ok": None, "kind": "threshold",
                "ev": "UCDP 覆盖到 %s，窗口内有 %d 条事件 —— 但【「全面战争」没有阈值定义】"
                      "⇒ 判不了：有持续武装冲突 ≠ 全面战争" % (last, n)}
    if n >= threshold:
        return {"ok": True, "kind": "hit",
                "ev": "窗口内 %d 条 ≥ 阈值 %d ⇒ 【该路径发生了】" % (n, threshold)}
    return {"ok": False, "kind": "below",
            "ev": "窗口内 %d 条 < 阈值 %d ⇒ 尚未被证伪" % (n, threshold)}


def _timeline(code: str):
    p = os.path.join(TIMELINES, code + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def check_bilateral(a: str, b: str, kind: str, since: int) -> dict:
    """机器核对：两个主体之间在 since 年后有没有发生 kind 类事件。
    数据：actor_timelines 的 COW 骨架（每条带 involved 列表）。

    ★ 这里修过两个 bug，都是同一类「把查不到当成没有」：
      ① 缺时间线（主体名写错/不存在）⇒ 原版会继续跑，然后因为 b 从没出现
         而报「尚未被证伪」。改：缺数据 ⇒ 不可判。
      ② ★更要命的：COW 骨架最新只到 2014，而核对窗口是 2020 起 ——
         那么「自 2020 年起未见」是【空的】。改：数据覆盖不到窗口 ⇒ 不可判。
         这正是 §10 那条口径对账的同型错误：**数据是真的，但不对题。**
    """
    da, db = _timeline(a), _timeline(b)
    missing = [x for x, d in ((a, da), (b, db)) if not d]
    if missing:
        return {"ok": None, "ev": "缺时间线：%s ⇒ 不可判（不把缺数据当没有）" % "、".join(missing)}
    sk = da.get("skeleton_cow") or []
    maxyear = max((s.get("year_end") or 0) for s in sk) if sk else 0
    if maxyear < since:
        return {"ok": None,
                "ev": "数据只覆盖到 %d，核对窗口自 %d 起 ⇒ 【窗口不在数据里，判不了】"
                      % (maxyear, since)}
    hits = [s for s in sk
            if b in set(s.get("involved") or []) and s.get("type") == kind
            and (s.get("year_end") or 0) >= since]
    if hits:
        return {"ok": True, "ev": "找到 %d 条 %s（最近 %s）⇒ 【该路径发生了】"
                % (len(hits), kind, max(h.get("year_end") for h in hits))}
    return {"ok": False, "ev": "数据覆盖 %d–%d，窗口内未见 %s 类事件 ⇒ 尚未被证伪"
            % (min((s.get("year_end") or 0) for s in sk), maxyear, kind)}


def check_fact(kind: str) -> dict:
    """公开记录类断言：本账【不伪造判定】——没有证据库就如实说没有。"""
    return {"ok": None, "ev": "需外部记录（本仓无证据层）—— 请人工核并写入依据"}


def evaluate(e: dict) -> dict:
    name = e.get("check")
    if not name:
        return {"state": STATE_NEED_EVIDENCE, "evidence": "该断言需政治/外交/贸易记录；本仓没有那一层"}
    if name.startswith("ucdp:"):
        # UCDP 覆盖到 2025 ⇒ 窗口能落在数据里。格式 ucdp:IND-PAK:2020[:阈值]
        parts = name.split(":")
        pair, since = parts[1], int(parts[2])
        th = int(parts[3]) if len(parts) > 3 else None
        a, b = pair.split("-")
        r = check_ucdp_bilateral(a, b, since, th)
        if r["ok"] is None:
            st = STATE_NEED_THRESHOLD if r["kind"] == "threshold" else STATE_NO_DATA
            return {"state": st, "evidence": r["ev"]}
        return {"state": STATE_FALSIFIED if r["ok"] else STATE_UNFALSIFIED,
                "evidence": r["ev"]}
    if name.startswith("bilateral:"):
        _, pair, kind = name.split(":")
        a, b = pair.split("-")
        r = check_bilateral(a, b, kind, since=2020)
        if r["ok"] is None:
            return {"state": STATE_NO_DATA, "evidence": r["ev"]}
        return {"state": STATE_FALSIFIED if r["ok"] else STATE_UNFALSIFIED,
                "evidence": r["ev"]}
    if name.startswith("fact:"):
        return {"state": STATE_NEED_EVIDENCE, "evidence": check_fact(name)["ev"]}
    return {"state": STATE_UNDECIDABLE, "evidence": "未实现的核对类型"}


def compute() -> dict:
    rows = []
    for e in E:
        r = evaluate(e)
        rows.append(dict(e, state=r["state"], evidence=r["evidence"]))
    tally = {}
    for r in rows:
        tally[r["state"]] = tally.get(r["state"], 0) + 1
    return {"rows": rows, "tally": tally}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    cur = compute()
    print("=" * 96)
    print("# 「不可能路径」账 —— 排除性断言（单向可证伪）")
    print("=" * 96)
    print("\n  来源：47 份主体档案 ＋ 10 个场景 ＋ 结构诊断文章 ＋ 2026-09-28 框架操作手册")
    print("  抽取：从 367 个 .md 的 %d 条候选里逐条挑出真断言" % 142)
    print("  规矩：「X 不可能」单向可证伪 —— X 发生⇒证伪；X 未发生⇒【只说明尚未被证伪】\n")
    print("  %-6s %-10s %-14s %s" % ("id", "主体", "状态", "断言"))
    print("  " + "-" * 92)
    for r in cur["rows"]:
        print("  %-6s %-10s %-14s %s" % (r["id"], r["actor"], r["state"], r["claim"][:52]))
        print("  %-6s %-10s %-14s ⓘ %s" % ("", "", "", r["evidence"]))
    print("  " + "-" * 92)
    print("  " + "　".join("%s ×%d" % (k, v) for k, v in sorted(cur["tally"].items())))

    print("\n" + "=" * 96)
    print("  读这张账要注意的三件事")
    print("=" * 96)
    print("  ① **机器能判的只有很少几条。** 本账 %d 条里，只有涉及【双边冲突事件】的能用"
          % len(cur["rows"]))
    print("     磁盘上的 UCDP/COW 数据判；其余 %d 条需要政治/外交/贸易记录 ——"
          % sum(1 for r in cur["rows"] if r["state"] == STATE_NEED_EVIDENCE))
    print("     而本仓【没有那一层】。这不是断言的错，是证据层的缺口。")
    print("  ② 用户 2026-09-28 的框架手册里，两条断言（塞尔维亚无法选边、冻结局怕温暖）")
    print("     是【回溯性】的 —— 它们用已经发生的事来立论。这不是缺点：")
    print("     排除性断言的价值恰恰在于【可以对过去查】，不必等未来。")
    print("  ③ ⚠️ 「尚未被证伪」**不是**「被证实」。一条断言至今没被证伪，")
    print("     只说明它还没撞上反例；要让它真成为知识，需要【主动去找反例】。")
    print("     而本仓的 `CWKB_Vault/Special/Prediction_Graveyard/` 只为这件事")
    print("     留了一个位置（1 条记录）—— 它需要的是持续往里写。")
    print("=" * 96)
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

    print("# exclusion_ledger 自证")
    check("无 check 的断言 ⇒ 待判（不冒充判过）",
          evaluate({"check": None})["state"] == STATE_NEED_EVIDENCE)
    check("fact: 类 ⇒ 待判（本仓无证据层，不伪造判定）",
          evaluate({"check": "fact:record"})["state"] == STATE_NEED_EVIDENCE)
    r = evaluate({"check": "bilateral:IND-PAK:WAR"})
    check("★COW 口径核不动 2020+ 窗口 ⇒ 判『数据不够』（不是『尚未被证伪』）",
          r["state"] == STATE_NO_DATA, r["state"] + " / " + r["evidence"])
    r2 = evaluate({"check": "bilateral:IND-XXX:WAR"})
    check("★缺时间线 ⇒ 判『数据不够』（不把『查不到』当『没有』）",
          r2["state"] == STATE_NO_DATA, r2["evidence"])
    # UCDP 口径：覆盖到 2025 ⇒ 窗口落进数据里。四个方向都要钉住：
    r5 = evaluate({"check": "ucdp:IN-PK:2020"})
    check("★UCDP：有事件但没定阈值 ⇒ 判『方法问题』，不是『数据问题』",
          r5["state"] == STATE_NEED_THRESHOLD, r5["state"] + " / " + r5["evidence"])
    r6 = evaluate({"check": "ucdp:IN-PK:2020:999999"})
    check("★UCDP：给了阈值且未达 ⇒ 尚未被证伪",
          r6["state"] == STATE_UNFALSIFIED, r6["state"] + " / " + r6["evidence"])
    r7 = evaluate({"check": "ucdp:IN-PK:2020:1"})
    check("★UCDP：给了阈值且已达 ⇒ 被证伪", r7["state"] == STATE_FALSIFIED, r7["state"])
    r8 = evaluate({"check": "ucdp:CN-XX:2020:1"})
    check("★UCDP：没有这个双边对 ⇒ 数据不够（不猜）",
          r8["state"] == STATE_NO_DATA, r8["state"] + " / " + r8["evidence"])
    # ★ 窗口覆盖：COW 骨架止于 2014，而核对窗口自 2020 起 ⇒ 必须判「不可判」
    r3 = check_bilateral("IND", "PAK", "WAR", since=2020)
    check("★数据覆盖不到核对窗口 ⇒ 不可判（数据是真的，但不对题）",
          r3["ok"] is None and "窗口" in r3["ev"], str(r3))
    r4 = check_bilateral("IND", "PAK", "WAR", since=1900)
    check("★窗口在数据覆盖内 ⇒ 才给二值判定", r4["ok"] is not None, str(r4))
    # 单向可证伪的语义：状态集合必须把「证伪」与「尚未证伪」分开，且没有「已证实」
    states = {evaluate(e)["state"] for e in E}
    check("★状态里【没有】「已证实」这一档（单向可证伪，不许把未证伪读成证实）",
          not any("证实" in s for s in states), str(states))
    check("账里断言数 ≥ 15", len(E) >= 15, str(len(E)))
    check("每条断言都有 来源 ＋ 窗口 ＋ 理由",
          all(e.get("src") and e.get("window") and e.get("why") for e in E),
          str([e["id"] for e in E if not (e.get("src") and e.get("window") and e.get("why"))]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
