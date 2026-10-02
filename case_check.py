# -*- coding: utf-8 -*-
"""case_check.py —— B4.3：对一个填好的案例跑三条检查，并量出 pending_manual 队列

★★ 这个工具的产出里，**最重要的一行是 pending_manual 的长度。**

   B4 的检查 3 有三条：① 排除方向被证伪 ② 判据质量 ③ 路径空间。
   而 ①③ 都需要「判据能不能落到可观察的事实上」。
   `observable` 里 `threshold` + `source` 都有 ⇒ 机器能判；缺任一 ⇒ **必须人判**。

   ★ 关键的设计选择：**不能自动判的，进队列，不假装判了。**
     因为「假装判了」会让一条没核过的断言看起来像核过的 —— 那正是本项目一贯的病。

   而 **pending_manual 占多大比例，本身是一个读数**：
     · 若几乎全满 ⇒ 说明问题不在数据量，在于「路径推演的判据天生是政治性的」
     · 若有相当一部分可核 ⇒ 说明数据缺口是具体的、可补的

★★ 核对类型（前三个真跑通，第四个占位）
   ucdp_dyad_present(<a>,<b>,<y1>-<y2>)  该两边在窗口内【有】事件记录
   ucdp_dyad_absent (<a>,<b>,<y1>-<y2>)  该两边在窗口内【无】事件记录
   ucdp_deaths      (<a>,<b>,<y>)        年度死亡 ≥ 阈值
   （其余一律进队列）

★ 覆盖不到窗口时的规矩（本轮栽过一次，写死在这）
   **数据覆盖不到 ⇒ 判「数据不够」，不许判「尚未被证伪」也不许判「已确认」。**

运行：  python case_check.py <案例.json>
        python case_check.py --all
        python case_check.py --selftest
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "ucdp_actors.json")
FILLED = os.path.join(HERE, "data", "cases", "filled")
DYAD_ALIASES = {                      # observable 里写的简写 → UCDP 原始名里该出现的词
    "IQ": "Iraq", "KW": "Kuwait", "US": "United States of America",
    "GB": "United Kingdom", "AUS": "Australia", "RU": "Russia", "UA": "Ukraine",
    "IR": "Iran", "IL": "Israel",
}
COALITION_HINT = "AUS/GB/US"


def load_dyads() -> dict:
    if not os.path.exists(DATA):
        return {}
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh).get("dyads") or {}


def resolve(spec: str) -> list:
    """把 `AUS/GB/US` 或 `IQ` 解析成 UCDP 原始名里该出现的词表。"""
    parts = [x.strip() for x in re.split(r"[/,]", spec) if x.strip()]
    return [DYAD_ALIASES.get(p, p) for p in parts]


def dyad_side_has(raw: str, want: list, match_all: bool = False) -> bool:
    a, _, b = raw.partition(" || ")
    def side_ok(s):
        hits = [w for w in want if w.lower() in s.lower()]
        return len(hits) == len(want) if match_all else bool(hits)
    return side_ok(a) or side_ok(b)


def find_dyads(dyads: dict, spec_a: str, spec_b: str) -> list:
    """找出「一边含 spec_a 的词、另一边含 spec_b 的词」的所有双边对。"""
    A, B = resolve(spec_a), resolve(spec_b)
    out = []
    for k in dyads:
        a, _, b = k.partition(" || ")
        if (dyad_side_has(k, A)) and any(w.lower() in (a + b).lower() for w in B):
            # 更严：A 的词与 B 的词必须落在【不同】的边上
            a_has = any(w.lower() in a.lower() for w in A)
            b_has = any(w.lower() in b.lower() for w in B)
            a_has2 = any(w.lower() in a.lower() for w in B)
            b_has2 = any(w.lower() in b.lower() for w in A)
            if (a_has and b_has) or (a_has2 and b_has2):
                out.append(k)
    return out


# ══ 三种核对 ════════════════════════════════════════════════════════════════════
def normalize_src(src: str) -> str:
    """把 source 写法归一。

    ★ 第一次跑出「auto=0 manual=11」—— 连 4 条带 source 的也全进了队列。
      查下去：我在案例 JSON 里写的是 `UCDP:dyad_absent(...)`，而正则期望
      `ucdp_dyad_present(...)`。**前缀与函数名两种写法都没匹配上，静默落到
      「不认识的写法」分支** ⇒ 读数变成 100% 待人工。
      ★★ 这正是那条自证「读数不能太干净」存在的理由 ——
         没有它，我会把「100% 待人工」当成结论报出去。
    """
    s = (src or "").strip()
    s = re.sub(r"^[A-Za-z_]+:", "", s)          # UCDP: / COW: 之类的前缀
    s = re.sub(r"^ucdp_", "", s)                # ucdp_dyad_present → dyad_present
    # ★ 第一版这里写的是 `^(dyad_|ucdp_)` —— 把 `dyad_` 也剥掉了 ⇒
    #   正则 `dyad_(present|absent)\(` 再也匹配不到，三个 present/absent 自证全变 None。
    #   **归一器与正则不一致，而且不一致得很静默。** 所以下面给归一器本身也加了自证。
    return s


def check_ucdp_present(dyads: dict, spec: str):
    """`(ucdp_)dyad_present|absent(a,b,y1-y2)`。

    ★ 第一版我让调用方传 expect，结果 `absent` 的语义被写反：
      函数从正则里解析出 present|absent，却忽略它、用调用方给的 expect。
      ⇒ 改为【期望由 source 自己声明】，调用方不再传。
    """
    m = re.match(r"dyad_(present|absent)\(\s*([^,]+),\s*([^,]+),\s*(\d{4})\s*-\s*(\d{4})\s*\)",
                 normalize_src(spec))
    if not m:
        return None
    kind, a, b, y1, y2 = m.groups()
    y1, y2 = int(y1), int(y2)
    keys = find_dyads(dyads, a, b)
    if not keys:
        # ★ 该双边对在数据里【根本不存在】—— 不能判「无事件」（那可能是数据里没这一对）
        return {"observed": None, "why": "UCDP 里找不到这两个 side 的双边对 ⇒ 数据不够，不判"}
    hits, years = [], []
    for k in keys:
        for y, cell in dyads[k].items():
            if y == "_cid" or not isinstance(cell, list):
                continue
            if y1 <= int(y) <= y2 and cell[0] > 0:
                hits.append((k, y, cell[0], cell[1]))
                years.append(int(y))
    ok = bool(hits)
    # ★★ 这里修过一个语义错误，值得写下来：
    #   第一版直接把 source 的真假当成了【断言的真假】⇒ 排除断言 X01「盟军入侵伊拉克」
    #   在窗口内【无事件】时被判成「❌ 证伪」。**反了。**
    #   根因是两件事被混成一件：
    #     ① observable 说的是【观察到一个事件】还是【观察到一个缺失】（present/absent）
    #     ② 观察到之后，对断言意味着什么 —— 这取决于断言是排除还是推演
    #   ⇒ 拆开：本函数只回答【观察到了没有】(observed)，映射交给调用方按 direction 做。
    observed = ok if kind == "present" else (not ok)
    return {"observed": observed, "kind": kind,
            "detail": "窗口 %d-%d 内%s事件记录；命中 %s" %
                      (y1, y2, "有" if ok else "无",
                       ("；".join("%s %s (%d 起/%d 死)" % (k.replace('Government of ', '')[:34], y, e, d)
                                  for k, y, e, d in hits[:3]) if hits else "无")),
            "dyads_checked": keys}


def check_ucdp_deaths(dyads: dict, spec: str):
    m = re.match(r"deaths\(\s*([^,]+),\s*([^,]+),\s*(\d{4})\s*,\s*(\d+)\s*\)", normalize_src(spec))
    if not m:
        return None
    a, b, y, thr = m.group(1), m.group(2), m.group(3), int(m.group(4))
    keys = find_dyads(dyads, a, b)
    if not keys:
        return {"observed": None, "why": "找不到双边对 ⇒ 数据不够"}
    tot = sum(dyads[k].get(y, [0, 0])[1] for k in keys if isinstance(dyads[k].get(y), list))
    return {"observed": tot >= thr,
            "detail": "%s 年该对死亡合计 %d（阈值 %d）" % (y, tot, thr)}


def bigrams(s: str) -> set:
    """中文字符二元组（与 judgment_ledger 同一套口径）。"""
    s = re.sub(r"[\s\W_]+", "", s or "", flags=re.UNICODE)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else ({s} if s else set())


def overlap(a: str, b: str) -> float:
    x, y = bigrams(a), bigrams(b)
    if not x or not y:
        return 0.0
    return len(x & y) / float(min(len(x), len(y)))


def looks_opposite(a: str, b: str) -> bool:
    """一侧有否定词、另一侧没有 ⇒ 很可能是【相反】而不是【相同】。"""
    neg = ("不", "未", "无", "停止", "停", "拒绝", "没有")
    return any(w in a for w in neg) != any(w in b for w in neg)


def check_discriminating(case: dict, thresh: float = 0.5) -> dict:
    """★★ 区分点【提示】—— 不是校验，而且它两个方向都会错。

    ★★ 这个结论是第一版写错之后才想明白的，值得完整写下来：
      海湾真跑（docs/ConStruct_路径空间试写_海湾.md）里我写过：
        「停火是所有路径共通的终点 —— P01／P02／P03／P05 都以某种停火结束。
          ⇒ 所以「停火」不是区分点」
      然后在 IQ-KW-1991.json 里，我把 P03②「联军收手」标成了 `discriminating: true`。
      **结论写了、实现时反着做、无人发现。** 于是我想做机器检查来抓这种自相矛盾。
      **结果两个方向都错了：**

        报了不该报的：P01③「停在边境，不向巴格达推进」对 P02③「越过边境向巴格达推进」
                      —— 它们是【相反】的，却因为用词相同（联军地面部队／巴格达／推进）
                         被判成高度重叠。
        漏了该报的  ：P03②「联军收手」没被报 —— 它的 indicator 短而独特，
                      而它的问题**不是词面像，是概念上【所有路径最后都会停火】**。

      ⇒ **字符重叠度分不出「相同」与「相反」，而区分点恰恰最常表现成一对相反的阶段。**
        这个口径在这一件事上两个方向都不对 —— 与本项目早先那次
        （「命中率 = 58%」对「命中率 > 65%」被判成同类）是同型错误。

    ⇒ 定位：**列出词面高度相似的对，让人自己判是「相同」还是「相反」。**
      它不判对错，也不该被当成通过／不通过。
      「是不是共通前提／共通终点」是语义判断，机器现在判不了 —— **这条限度照实说。**
    """
    hits = []
    stages = [(p, st) for p in case.get("paths", []) for st in p.get("stages", [])
              if st.get("discriminating")]
    for p, st in stages:
        obs = st.get("observable") or {}
        mine = "%s %s" % (obs.get("object") or "", obs.get("indicator") or "")
        for p2 in case.get("paths", []):
            if p2 is p:
                continue
            for st2 in p2.get("stages", []):
                obs2 = st2.get("observable") or {}
                other = "%s %s" % (obs2.get("object") or "", obs2.get("indicator") or "")
                ov = overlap(mine, other)
                if ov >= thresh:
                    opp = looks_opposite(mine, other)
                    hits.append({
                        "stage": "%s/%s" % (p.get("id"), st.get("stage")),
                        "conflicts_with": "%s/%s" % (p2.get("id"), st2.get("stage")),
                        "overlap": round(ov, 2),
                        "likely_opposite": opp,
                        "why": ("词面重叠 %.0f%%，但只有一侧含否定词 ⇒ 更可能是【相反】而非相同"
                                "—— 若确实相反，它是有效区分点，不必改。" % (ov * 100)) if opp else
                               ("词面重叠 %.0f%%，两侧都无否定词 ⇒ 更可能是【同义】"
                                "—— 请确认它到底区分开了什么。" % (ov * 100)),
                    })
    return {"hits": hits, "checked": len(stages),
            "limit": "★ 本项是【提示】不是校验：分不出「相同」与「相反」，"
                     "也判不了「是不是所有路径共通的终点」—— 后者是语义判断。"}


# ══ 主检查 ══════════════════════════════════════════════════════════════════════
def check_case(case: dict, dyads: dict) -> dict:
    rows, pending = [], []

    def judge(jid, kind, obs, window):
        src = (obs or {}).get("source")
        if not src:
            pending.append({"judgment_id": jid, "kind": kind,
                            "observable_object": (obs or {}).get("object"),
                            "observable_indicator": (obs or {}).get("indicator"),
                            "why_manual": "没有 source ⇒ 没有数据源可核",
                            "window_to": (window or {}).get("to")})
            return {"verdict": "manual"}
        r = check_ucdp_present(dyads, src) or check_ucdp_deaths(dyads, src)
        if r is None:
            pending.append({"judgment_id": jid, "kind": kind,
                            "observable_object": (obs or {}).get("object"),
                            "observable_indicator": (obs or {}).get("indicator"),
                            "why_manual": "source 的写法本工具不认识：%s" % src,
                            "window_to": (window or {}).get("to")})
            return {"verdict": "manual"}
        r["source"] = src
        # ★★ 映射交给这里做，按【断言方向】——
        #   修之前我把 source 的真假直接当成断言的真假，结果排除断言 X01
        #   「盟军入侵伊拉克」在窗口内无事件时被判成「❌ 证伪」。**反了。**
        #   排除断言：观察到了 ⇒ 证伪；**没观察到 ⇒ 尚未被证伪（永远不是「证实」）**
        #   路径阶段：观察到了 ⇒ 确认；没观察到 ⇒ 落空
        #   数据不够   ⇒ 判「数据不够」，两样都不许说
        obs = r.get("observed")
        if obs is None:
            r["verdict"] = "insufficient_data"
        elif kind == "exclusion":
            r["verdict"] = "falsified" if obs else "not_yet_falsified"
        else:
            r["verdict"] = "confirmed" if obs else "missed"
        return r

    # ① 排除断言：发生了 ⇒ 证伪
    for x in case.get("exclusions", []):
        r = judge(x["id"], "exclusion", x.get("observable"), x.get("window"))
        rows.append(("排除", x["id"], x.get("content"), r))

    # ② 路径推演：只数 discriminating 的
    for p in case.get("paths", []):
        disc = [s for s in p.get("stages", []) if s.get("discriminating")]
        for i, st in enumerate(disc, 1):
            jid = "%s/%s#%d" % (p["id"], st["stage"], i)
            r = judge(jid, "path_stage", st.get("observable"), st.get("window"))
            rows.append(("路径", jid, st["stage"], r))

    auto = [r for _k, _i, _c, r in rows if r.get("verdict") != "manual"]
    manual = [r for _k, _i, _c, r in rows if r.get("verdict") == "manual"]
    return {"rows": rows, "pending": pending,
            "n_judgeable": len(rows), "n_auto": len(auto), "n_manual": len(manual)}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    dyads = load_dyads()
    files = []
    if "--all" in sys.argv:
        files = sorted(os.path.join(FILLED, f) for f in os.listdir(FILLED) if f.endswith(".json"))
    else:
        files = [a for a in sys.argv[1:] if a.endswith(".json")]
    if not files:
        print("用法：python case_check.py <案例.json> | --all")
        return 1

    for fp in files:
        with io.open(fp, encoding="utf-8") as fh:
            case = json.load(fh)
        r = check_case(case, dyads)
        print("=" * 96)
        print("# %s" % os.path.basename(fp))
        print("=" * 96)
        print("  %-5s %-34s %-26s %s" % ("类", "判断", "内容/阶段", "判定"))
        print("  " + "-" * 92)
        for kind, jid, label, res in r["rows"]:
            v = res.get("verdict", "?")
            # ★ 排除断言与路径阶段的措辞【不能混用】：
            #   排除断言：只有「证伪」与「尚未被证伪」两态 —— **永远没有「证实」**
            #   路径阶段：有「确认」与「落空」两态
            mark = {"manual": "⏳ 待人工",
                    "falsified": "⛔ 被证伪（它发生了，我错了）",
                    "not_yet_falsified": "⏸️ 尚未被证伪",
                    "confirmed": "✅ 该阶段确认",
                    "missed": "✖️ 该阶段落空",
                    "insufficient_data": "⚠️ 数据不够，不判"}.get(v, v)
            print("  %-5s %-34s %-26s %s" % (kind, jid[:34], (label or "")[:26], mark))
            if res.get("detail"):
                print("  %-5s   ↳ %s" % ("", res["detail"]))
            if res.get("why"):
                print("  %-5s   ↳ %s" % ("", res["why"]))

        dg = check_discriminating(case)
        print("\n  ── ★ 区分点校验（标了 discriminating=true 的阶段，是不是真的区分得开）")
        if dg["hits"]:
            for d in dg["hits"]:
                tag = "↔️ 可能相反" if d["likely_opposite"] else "≈ 可能同义"
                print("     %s %s" % (tag, d["stage"]))
                print("        与 %s　%s" % (d["conflicts_with"], d["why"]))
        else:
            print("     （没有词面高度相似的阶段对）")
        print("     %s" % dg["limit"])
        print("     检查了 %d 个标 true 的阶段。" % dg["checked"])

        print("\n  ── ★ pending_manual 队列")
        if r["pending"]:
            for p in r["pending"]:
                print("     ⏳ %s" % p["observable_indicator"])
                print("        对象：%s ｜ 为什么只能人工：%s" % (p["observable_object"], p["why_manual"]))
        else:
            print("     （空）")
        tot = r["n_judgeable"]
        print("\n  ── 读数")
        print("     可判判断总数（排除 ＋ 区分性阶段）：%d" % tot)
        print("     机器可判：%d　待人工：%d" % (r["n_auto"], r["n_manual"]))
        if tot:
            print("     **待人工占比：%.0f%%**" % (100.0 * r["n_manual"] / tot))
            print("     （这个数字就是这一跑要量出来的东西：")
            print("       接近 100% ⇒ 问题不在数据量，在于路径推演的判据天生是政治性的；")
            print("       明显低于 100% ⇒ 数据缺口是具体的、可补的。）")
        print()
    return 0


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

    print("# case_check 自证")
    dyads = load_dyads()
    ck("★能读到双边对", len(dyads) > 50, str(len(dyads)))

    # ★★ 归一器与正则必须一致 —— 它们不一致过一次，而且不一致得很静默
    ck("★★normalize_src 去掉前缀但【保留 dyad_】",
       normalize_src("UCDP:dyad_present(a,b,1991-1992)") == "dyad_present(a,b,1991-1992)",
       normalize_src("UCDP:dyad_present(a,b,1991-1992)"))
    ck("★★归一后的形态仍能被正则匹配（这条就是防不一致的）",
       re.match(r"dyad_(present|absent)\(", normalize_src("UCDP:dyad_absent(a,b,1991-1992)")) is not None,
       normalize_src("UCDP:dyad_absent(a,b,1991-1992)"))
    ck("★ucdp_ 前缀也被归一", normalize_src("ucdp_dyad_present(a,b,1-2)") == "dyad_present(a,b,1-2)",
       normalize_src("ucdp_dyad_present(a,b,1-2)"))
    ck("★无前缀不动", normalize_src("deaths(a,b,1991,1000)") == "deaths(a,b,1991,1000)")
    ck("★resolve 把简写展开", resolve("AUS/GB/US") == ["Australia", "United Kingdom",
                                                      "United States of America"],
       str(resolve("AUS/GB/US")))
    ks = find_dyads(dyads, "AUS/GB/US", "IQ")
    ck("★能找到 联军||伊拉克 这个对", any("Iraq" in k for k in ks), str(ks))
    ck("★找不到的对返回空", find_dyads(dyads, "IQ", "ZZZZ") == [], str(find_dyads(dyads, "IQ", "ZZZZ")))

    # ★ 核心：Iraq||Kuwait 只在 1990/1991 有记录 ⇒ absent 检查必须能判
    r = check_ucdp_present(dyads, "UCDP:dyad_present(IQ, KW, 1992-1995)")
    ck("★★present 检查：IQ-KW 在 1992-1995 无记录 ⇒ observed=False",
       r and r["observed"] is False, str(r))
    r = check_ucdp_present(dyads, "UCDP:dyad_present(IQ, KW, 1990-1991)")
    ck("★★present 检查：IQ-KW 在 1990-1991 有记录 ⇒ observed=True",
       r and r["observed"] is True, str(r))
    r = check_ucdp_present(dyads, "UCDP:dyad_absent(IQ, KW, 1992-1995)")
    ck("★★absent 检查：窗口内无事件 ⇒ observed=True（**观察到了一个【缺失】**）",
       r and r["observed"] is True, str(r))

    # ★★ 覆盖不到 ⇒ 判数据不够，不许判证伪/确认
    r = check_ucdp_present(dyads, "UCDP:dyad_present(IQ, ZZZZ, 1991-1992)")
    ck("★★找不到双边对 ⇒ insufficient_data（**不许**判「无事件」）",
       r and r["observed"] is None, str(r))

    ck("★deaths 检查：IQ-KW 1991 死亡 21790 ≥ 1000 ⇒ observed=True",
       (check_ucdp_deaths(dyads, "UCDP:deaths(IQ, KW, 1991, 1000)") or {}).get("observed") is True)
    ck("★deaths 检查：阈值 999999 ⇒ observed=False",
       (check_ucdp_deaths(dyads, "UCDP:deaths(IQ, KW, 1991, 999999)") or {}).get("observed") is False)
    ck("★不认识的 source 写法 ⇒ 返回 None（会进队列）",
       check_ucdp_present(dyads, "fact:某个历史事实") is None)

    # 真案例
    fp = os.path.join(FILLED, "IQ-KW-1991.json")
    if os.path.exists(fp):
        with io.open(fp, encoding="utf-8") as fh:
            case = json.load(fh)
        res = check_case(case, dyads)
        ck("★真案例能跑", res["n_judgeable"] > 0, str(res["n_judgeable"]))
        ck("★★有 source 的进了自动判定、没 source 的进了队列",
           res["n_auto"] > 0 and res["n_manual"] > 0,
           "auto=%d manual=%d" % (res["n_auto"], res["n_manual"]))
        # ★★ 这条自证就是抓到 normalize 那个 bug 的那条：读数不能太干净
        ck("★★带 source 的判断【必须真的被判了】—— 不许全落进队列",
           res["n_auto"] >= 3, "auto=%d manual=%d（若 auto=0 说明 source 写法没被识别）"
           % (res["n_auto"], res["n_manual"]))
        ck("★★待人工队列里的每一条都写明了【为什么只能人工】",
           all(p.get("why_manual") for p in res["pending"]))
        # ★★ 区分点校验：必须能在真案例上报出 P03② （我自己标错的那条）
        dg = check_discriminating(case)
        ck("★区分点提示：真案例上有词面相似的对", len(dg["hits"]) > 0, str(len(dg["hits"])))
        ck("★★它把【相反】的那对识别出来了（P01③停在边境 vs P02③占领巴格达）",
           any(d["likely_opposite"] for d in dg["hits"]),
           str([(d["stage"], d["likely_opposite"]) for d in dg["hits"]]))
        ck("★★而它【漏了】P03②「联军收手」—— 照实记：这条检查判不了语义上的共通终点",
           not any("P03" in d["stage"] and "收手" in d["stage"] for d in dg["hits"]),
           str([d["stage"] for d in dg["hits"]]))
        ck("★★返回值里带 limit（写明它两个方向都会错）", "limit" in dg and "提示" in dg["limit"])
        ck("★looks_opposite：一侧有否定词才算相反",
           looks_opposite("停在边境，不向巴格达推进", "越过边境向巴格达推进") is True
           and looks_opposite("甲进攻乙", "甲攻击乙") is False)
        # 反向：两条 observable 明显不同的阶段，不该被报
        _fake = {"paths": [
            {"id": "A", "stages": [{"stage": "s", "discriminating": True,
              "observable": {"object": "伊拉克政府", "indicator": "宣布从科威特撤军"}}]},
            {"id": "B", "stages": [{"stage": "s", "discriminating": True,
              "observable": {"object": "以色列", "indicator": "对伊拉克本土实施军事报复"}}]}]}
        ck("★★反向：observable 明显不同的两条不该被提示",
           check_discriminating(_fake)["hits"] == [], str(check_discriminating(_fake)["hits"]))

        ck("★★★排除断言的判定词里【永远不出现「确认」】—— 单向可证伪",
           all(r.get("verdict") in ("falsified", "not_yet_falsified", "manual", "insufficient_data")
               for k, _i, _c, r in res["rows"] if k == "排除"),
           str([(j, r.get("verdict")) for k, j, _c, r in res["rows"] if k == "排除"]))
        ck("★★排除断言被真的判了（不是全进队列）",
           any(k == "排除" and r.get("verdict") != "manual" for k, _i, _c, r in res["rows"]),
           str([(j, r.get("verdict")) for k, j, _c, r in res["rows"] if k == "排除"]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
