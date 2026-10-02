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
    # ★★ 补这一批，是因为一个独立操作者实测撞上了（它按指南老老实实填，
    #   工具给了它一个【看起来完全正常】的错读数）：
    #     find_dyads(dyads,'CN','IN') → ['Government of India || NSCN-IM']
    #       'CN' 子串命中 **NS**CN**-IM**，'IN' 子串命中 **IN**dia
    #     deaths(CN, IN, 2020, 20) → 报「死亡合计 7」，真值是 2 起 / 25 死
    #     于是「中印 2020 全面战争」那条排除断言，依据的是**印度那加兰邦分离武装**的数字。
    #   同一根因：find_dyads(IN,'PK') 返回空 ⇒ IN-PK（1989–2025 完整记录）被判「数据不够」。
    #   ★ 而指南 §五 的示例全用 RU/UA/IQ/KW —— **恰好都在别名表里，把这个问题完全掩盖了。**
    #     教训：**示例恰好覆盖的实现，会掩盖不在示例里的缺陷。**
    "CN": "China", "IN": "India", "PK": "Pakistan", "KP": "North Korea",
    "KR": "South Korea", "JP": "Japan", "DE": "Germany", "FR": "France",
    "TR": "Turkey", "SA": "Saudi Arabia", "EG": "Egypt", "RS": "Serbia",
    "VN": "Vietnam", "PH": "Philippines", "SG": "Singapore", "MX": "Mexico",
    "ES": "Spain", "BR": "Brazil", "AF": "Afghanistan", "SY": "Syria",
    "YE": "Yemen", "PA": "Panama", "BA": "Bosnia-Herzegovina",
}
COALITION_HINT = "AUS/GB/US"


def load_dyads() -> dict:
    if not os.path.exists(DATA):
        return {}
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh).get("dyads") or {}


def load_geo() -> dict:
    """按 (主体对, 年, adm_1) 聚合的事件数 —— 地理判据的来源。"""
    if not os.path.exists(DATA):
        return {}
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh).get("geo") or {}


def resolve(spec: str) -> list:
    """把 `AUS/GB/US` 或 `IQ` 解析成 UCDP 原始名里该出现的词表。"""
    parts = [x.strip() for x in re.split(r"[/,]", spec) if x.strip()]
    return [DYAD_ALIASES.get(p, p) for p in parts]


def word_in(word: str, text: str) -> bool:
    """★ 词边界匹配，不是裸子串。

    ★★ 为什么必须改：裸子串让 'CN' 命中 **NS**CN**-IM'、'IN' 命中 '**IN**dia'。
      一个独立操作者按指南写 `CN, IN`，工具把中印案例映射到了
      「印度那加兰邦分离武装」，并据此报出一个【看起来完全正常】的死亡数。
      ⇒ 这是本类 bug 里最坏的一种：**错的读数与对的读数长得一样。**
    ★ 规则：短码（≤4 字符、全大写字母）必须【整词】匹配；
      长名（如 'United States of America'）允许作为子串出现。
    """
    w, t = word.lower().strip(), text.lower()
    if not w:
        return False
    if len(word) <= 4 and word.isalpha() and word.isupper():
        return re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) is not None
    return w in t


def dyad_side_has(raw: str, want: list, match_all: bool = False) -> bool:
    a, _, b = raw.partition(" || ")
    def side_ok(s):
        hits = [w for w in want if word_in(w, s)]
        return len(hits) == len(want) if match_all else bool(hits)
    return side_ok(a) or side_ok(b)


def find_dyads(dyads: dict, spec_a: str, spec_b: str) -> list:
    """找出「一边含 spec_a 的词、另一边含 spec_b 的词」的所有双边对。"""
    A, B = resolve(spec_a), resolve(spec_b)
    out = []
    for k in dyads:
        a, _, b = k.partition(" || ")
        if (dyad_side_has(k, A)) and any(word_in(w, a + b) for w in B):
            # 更严：A 的词与 B 的词必须落在【不同】的边上
            a_has = any(word_in(w, a) for w in A)
            b_has = any(word_in(w, b) for w in B)
            a_has2 = any(word_in(w, a) for w in B)
            b_has2 = any(word_in(w, b) for w in A)
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


def check_geo_present(dyads: dict, geo: dict, spec: str):
    """`geo_present(<码A>,<码B>,<州名关键词>,<年>,<阈值>)` —— 某州有没有足够多的事件。

    ★★ 为什么需要这一种锚：
      `dyad_present` 那种「有没有事件」的判据，在区分「有限冲突」与「全面入侵」时
      **根本不够** —— 因为顿巴斯从 2014 年就在打（只是被 UCDP 编成了 Ukraine||DPR/LPR）。
      实测 RU-UA：**2014 年 1 个州 2 起；2022 年 30 个州、基辅州 132 起、基辅市 42 起。**
      ⇒ **「基辅州出现战斗」才分得开。而 GED 有 adm_1，所以这做得到。**
    """
    m = re.match(r"geo_present\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*(\d{4})\s*,\s*(\d+)\s*\)",
                 normalize_src(spec))
    if not m:
        return None
    a, b, region, year, thr = (m.group(1).strip(), m.group(2).strip(),
                               m.group(3).strip(), m.group(4), int(m.group(5)))
    key = "%s-%s" % tuple(sorted([a, b]))
    if key not in geo:
        return {"observed": None,
                "why": "geo 里没有 %s ⇒ 数据不够，不判（**不许**判「没有事件」）" % key}
    regions = geo[key].get(year) or {}
    if not regions:
        return {"observed": None, "why": "%s 年 %s 无行政区记录 ⇒ 数据不够，不判" % (year, key)}
    hit = {k: v for k, v in regions.items() if region.lower() in k.lower()}
    n = sum(hit.values())
    return {"observed": n >= thr,
            "detail": "%s 年「%s」匹配到的行政区：%s ⇒ 合计 %d 起（阈值 %d）"
                      % (year, region,
                         ("；".join("%s:%d" % (k, v) for k, v in
                                    sorted(hit.items(), key=lambda kv: -kv[1])[:4]) or "无"),
                         n, thr)}


def check_geo_breadth(dyads: dict, geo: dict, spec: str):
    """`geo_breadth(<码A>,<码B>,<年>,<阈值>)` —— 事件铺开了多少个行政区。"""
    m = re.match(r"geo_breadth\(\s*([^,]+),\s*([^,]+),\s*(\d{4})\s*,\s*(\d+)\s*\)",
                 normalize_src(spec))
    if not m:
        return None
    a, b, year, thr = m.group(1).strip(), m.group(2).strip(), m.group(3), int(m.group(4))
    key = "%s-%s" % tuple(sorted([a, b]))
    if key not in geo or not geo[key].get(year):
        return {"observed": None, "why": "%s %s 无行政区记录 ⇒ 数据不够，不判" % (key, year)}
    n = len(geo[key][year])
    return {"observed": n >= thr,
            "detail": "%s 年该对事件铺开到 %d 个行政区（阈值 %d）" % (year, n, thr)}


def check_any(dyads: dict, geo: dict, spec: str):
    """总入口：支持 `not(...)` 包装。

    ★★ 为什么需要 `not()`：
      写 P02「有限入侵」时，observable 是「战斗**没有**铺开」，而
      `geo_breadth` 测的是「铺开了多少个州」—— **两者语义相反。**
      这与 present/absent 是同一个坑：**判据的形状与断言的形状不总是一致。**
      与其为每种判据都写一个反向版本（会组合爆炸），不如加一个通用取反。
    """
    s = normalize_src(spec)
    neg = False
    if s.startswith("not(") and s.endswith(")"):
        neg, s = True, s[4:-1].strip()
    r = (check_ucdp_present(dyads, s) or check_ucdp_deaths(dyads, s)
         or check_geo_present(dyads, geo, s) or check_geo_breadth(dyads, geo, s))
    if r is not None and neg:
        r = dict(r)
        if r.get("observed") is not None:
            r["observed"] = not r["observed"]
        # ★★ 修：原先只是前缀「取反（not）：」，而原句写的是取反【前】的语义，
        #   于是 observed=True 的那行 detail 读起来是「无事件记录」—— 数字对、打印行相反。
        #   独立操作者指出：只看 ↳ 那行会被误导。
        _raw = r.get("detail") or r.get("why") or ""
        r["detail"] = ("取反后：%s　｜　（取反前的原句：%s）"
                       % ("观察到了" if r["observed"] else "没观察到", _raw))
    return r


def apply_causal_prefix(path: dict, verdicts: list) -> dict:
    """★★ G6：因果链 —— 阶段 n 的确认，只在阶段 1..n−1 也确认时才算这条路径的。

    ★★ 这个缺口是怎么发现的
      海湾案例里 P03 的假设是「伊拉克撤军 ⇒ 联军收手」。
      检查器【逐阶段独立判】，于是报出：
        ① 宣布撤军 → 落空
        ② 联军收手 → 确认        ← 「联军收手」确实发生了
      ⇒ 看起来是「部分成立」。**而实际上 P03 整体是错的** ——
        联军收手的原因【不是伊拉克撤军，是伊拉克战败】。
      **而这一条比「判据核不了」更危险**：判据核不了你知道（它在待人工队列里），
      因果链缺环你不知道，而结论看起来是成立的。

    ⇒ 规则（能机器判的部分）：
      按顺序走 discriminating 阶段，**前缀连续命中才算链式确认**。
      前缀断掉之后仍然被确认的阶段，是【孤立确认】——
      它说明某个行为发生了，但**不是这条路径说的原因造成的**。

    ★ 四个已有案例全部通过：
      · 海湾 P03（0/3 ⇒ 落空，并报出孤立确认「联军收手」）√
      · 海湾 P01（1/1 ⇒ 确认）√
      · 俄乌 P01（2/2 ⇒ 确认）√
      · 俄乌 P02（0/2 ⇒ 落空）√

    ★★ 但它只修一半，限度必须写在记录里：
      它抓的是【前缀没中】，**抓不了【前缀中了但原因不同】**。
      若伊拉克真宣布撤军了、联军也收手了，而实际原因仍是战败 —— 前缀规则会判确认。
      ⇒ 所以它是**部分修**，不是完整修。**不许把它说成「因果链已验证」。**
    """
    # ★★ 修一个陷阱：`manual` 原先落进 `else: break` ⇒ 被当成「落空」。
    #   独立操作者实测：5 条路径全打印「✖️ 链断在开头」——而那 5 条其实【一条都没判】。
    #   **「没判」与「判了没中」在路径级读数上原本不可分。**
    chain = 0
    undecided = 0
    for _st, v in verdicts:
        if v == "confirmed":
            chain += 1
        elif v == "manual" or v == "insufficient_data":
            undecided += 1
            break                      # 链在这里【悬置】，不是断了
        else:
            break
    isolated = [st.get("stage") for (st, v) in verdicts[chain:] if v == "confirmed"]
    n = len(verdicts)
    if n == 0:
        pv = "open"
    elif chain == n:
        pv = "confirmed"
    elif undecided and chain == 0:
        pv = "undecided"               # ★ 与前缀断在开头【区分开】
    elif chain == 0:
        pv = "missed"
    else:
        pv = "partial"
    return {"path_verdict": pv, "chain_hits": chain, "chained_total": n,
            "undecided": undecided,
            "isolated_confirmations": isolated,
            "note": ("★ 孤立确认说明某个行为发生了，但不是这条路径说的原因造成的。"
                     if isolated else ""),
            "limit": "★ 前缀规则只抓「前缀没中」，抓不了「前缀中了但原因不同」—— 部分修，不是完整修。"}


def check_evidence_list(ev, sources: dict) -> tuple:
    """★★ S1.2 交叉印证（抄 2026-07-25 方案 §5.2）+ S1.1 分级 + §5.3 置信度。

    原方案写的是：
      · 同事实 ≥ 2 独立源 ⇒ confidence↑
      · 源间矛盾 ⇒ 标 contradiction
      · conf = f(source_reliability, corroboration, recency)

    ★ 为什么 evidence 要允许【一个列表】：现在一条判断只能挂一份依据，
      而「两个独立来源互证」显然比「一个来源说」强 —— 那正是原方案要的。
      ⇒ evidence 可以是对象，也可以是对象数组。

    ★ 独立性怎么判：**不同 outlet 就算独立源**（同 outlet 的多篇不算）。
      这条粗糙但可核，而且它把「两篇转载同一稿」与「两家各自报道」分开了。
    """
    items = ev if isinstance(ev, list) else [ev]
    items = [x for x in items if x]
    if not items:
        return None, "没有 evidence", {}

    obs_list, outs, details = [], [], []
    for it in items:
        ok, why = check_evidence(it, sources)
        if ok is None:
            return None, why, {}
        rec = sources.get(it.get("slug")) or {}
        obs_list.append(ok)
        outs.append((it.get("outlet") or rec.get("outlet")
                     or (rec.get("url") or "")[:60]))
        details.append({"slug": it.get("slug"), "observed": ok,
                        "tier": rec.get("tier"), "reliability": rec.get("reliability"),
                        "witness_type": rec.get("witness_type")})

    # ① 矛盾：两个来源对同一 observable 给出相反的 observed
    contradiction = len(set(obs_list)) > 1

    # ② 独立源数：按 outlet 去重
    n_indep = len(set(o for o in outs if o))

    # ③ 置信度：取各源 reliability 的均值 × 互证加成（上限 1.0）
    rels = [d["reliability"] for d in details if d.get("reliability") is not None]
    base = (sum(rels) / len(rels)) if rels else None
    if base is None:
        conf = None                       # ★ 给不出 reliability ⇒ 不给置信度（不猜）
    else:
        bonus = {0: 0.0, 1: 0.0, 2: 0.10}.get(n_indep, 0.15)
        conf = min(1.0, round(base + bonus, 3))
    return obs_list[0], "", {
        "observed_all": obs_list, "n_sources": len(items), "n_independent": n_indep,
        "contradiction": contradiction, "base_reliability": base, "confidence": conf,
        "sources": details,
    }


# ══ G4 · 概率空间的自洽性（抄 content/scenarios 那批场景的【区间】写法）════════
# ★ 旧写法粗区间的映射。刻意做得很宽 —— **因为它本来就很粗，收窄是假装精确。**
LEGACY_PROB = {
    "high": (0.40, 0.70),
    "medium": (0.15, 0.40),
    "low": (0.02, 0.15),
}


def prob_range(p):
    """把 probability 归一成 (low, high)。★ 返回 (低, 高, 是否粗) —— **粗的要标明**。

    ★ 为什么接受两种写法但不假装它们等价：
      区间（55-65%）携带「空间自洽性」这个信息；`high/medium/low` 不携带。
      把字符串映射成一个【很宽】的区间（如 high → 40-70%），是为了让老案例能跑，
      **而不是因为那个映射有依据** —— 所以第三个返回值标出它是粗的。
    """
    if isinstance(p, dict):
        lo, hi = p.get("low"), p.get("high")
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            if lo > 1:                      # 允许写 55 而不是 0.55
                lo, hi = lo / 100.0, hi / 100.0
            return float(lo), float(hi), False
        return None, None, False
    if isinstance(p, str) and p.strip().lower() in LEGACY_PROB:
        lo, hi = LEGACY_PROB[p.strip().lower()]
        return lo, hi, True                 # ★ 粗
    return None, None, False


def check_probability_space(case: dict) -> dict:
    """G4：路径概率之和应当【跨过 1.0】。

      · 上界 < 1.0（明显）  ⇒ **路径空间可能没穷尽**（还有路径没写）
      · 下界 > 1.0          ⇒ **概率互相矛盾**（加起来必然超过 100%）
      · 跨过 1.0            ⇒ 自洽

    ★ 这只对 direction=affirm 的路径算（排除断言不是路径，不占概率）。
    ★ 未填概率的路径【不算 0】—— 单独报出来，因为「没填」与「填了 0」不是一回事。
    """
    lo_sum = hi_sum = 0.0
    n, coarse, missing = 0, 0, []
    for p in case.get("paths") or []:
        if p.get("direction") not in (None, "affirm"):
            continue
        lo, hi, is_coarse = prob_range(p.get("probability"))
        if lo is None:
            missing.append(p.get("id") or p.get("label"))
            continue
        lo_sum += lo
        hi_sum += hi
        n += 1
        if is_coarse:
            coarse += 1
    if n == 0:
        return {"n": 0, "verdict": "no_data",
                "detail": "没有一条路径填了可解读的概率"}
    if hi_sum < 1.0 - 0.05:
        v, why = "gap", "上界 %.2f < 1.00 ⇒ **路径空间可能没穷尽**（还有路径没写）" % hi_sum
    elif lo_sum > 1.0 + 0.05:
        v, why = "conflict", "下界 %.2f > 1.00 ⇒ **概率互相矛盾**（加起来必然超过 100%%）" % lo_sum
    else:
        v, why = "consistent", "区间 %.2f ~ %.2f 跨过 1.00 ⇒ 自洽" % (lo_sum, hi_sum)
    return {"n": n, "lo_sum": round(lo_sum, 3), "hi_sum": round(hi_sum, 3),
            "coarse": coarse, "missing": missing, "verdict": v, "detail": why}


# ══ 主检查 ══════════════════════════════════════════════════════════════════════
def load_sources() -> dict:
    """读依据档案索引。

    ★★ 同时按【文件名】和【slug】建索引 —— 两种写法都能查到。

    修之前只按文件名（`archived_snapshot.split("/")[-1]`，**带 .html**）建 key，
    而 index.json 的 `slug` 字段**不带扩展名**。
    ⇒ 指南 §一 1.3 的示例教的是不带扩展名的那个 ⇒ **照指南写的人 8/8 全过不了第①道闸**，
      而报错说「不在索引里」—— **而索引里就有。**
    ★ 这是「错的读数与对的读数长得一样」的又一例；也是「示例恰好覆盖的实现会掩盖缺陷」
      的又一例（我自己那份写对了，因为我是读代码写的）。
    """
    p = os.path.join(HERE, "data", "sources", "index.json")
    if not os.path.exists(p):
        return {}
    out = {}
    for r in (fh_get(p) or {}).get("sources", []):
        fn = (r.get("archived_snapshot") or "").split("/")[-1]
        if fn:
            out[fn] = r
        if r.get("slug"):
            out[r["slug"]] = r
    return out


def fh_get(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def check_evidence(ev: dict, sources: dict) -> tuple:
    """★★ 依据的三道机器检查 —— 缺任何一道，该判断【退回待人工】。

    这是让「填了依据」不等于「过了」的机制。三道都是可机器判的：
      ① slug 在索引里          —— 不在 ⇒ 这个存档来源不明
      ② verified_open == True   —— 取不到 ⇒ 这条依据不存在
      ③ witness_type == contemporary —— 事后的不能用于时间锁定
    """
    if not ev:
        return None, "没有 evidence 块"
    slug = ev.get("slug")
    rec = sources.get(slug)
    if not rec:
        return None, ("① 依据「%s」查不到。"
                      "索引里两种写法都试过了：快照文件名（带扩展名，如 xxx.html）"
                      "与 slug 字段（不带扩展名）—— 都没命中 ⇒ 来源不明。" % (slug or "（未给）"))
    if not rec.get("verified_open"):
        return None, "② verified_open=false ⇒ 这条依据不存在"
    if rec.get("witness_type") != "contemporary":
        return None, ("③ witness_type=%s ⇒ 不能用于时间锁定"
                      % rec.get("witness_type"))
    if ev.get("observed") is None:
        return None, "依据合格，但没写 observed（是观察到了还是没观察到）"
    return bool(ev["observed"]), ""


def normalize_shape(case: dict) -> tuple:
    """★★ 产物接口：把 `path_space.paths` 归一到顶层 `paths`，并且【找不到就报错】。

    ★★ 为什么必须有这个 —— 一个独立操作者实测撞上的最致命缺陷：
      指南 §三 的示例、骨架的 `path_space`、骨架 `needs_human` 里写的 `path_space.paths`，
      **三处一致地把人导向 `path_space`**，而本函数原先只读顶层 `case["paths"]`。
      实测：同一份内容放 `path_space.paths` ⇒ `n_judgeable=0`；
            放顶层 ⇒ `n_judgeable=2`。
      **工具不报错、不警告，安静地输出一张空表加「可判判断总数 0」。**
      而 selftest 只对已有案例跑，**抓不到一个照骨架写的新案例读数为零。**

    ⇒ 两种形状都接受；但**若两个位置都找不到内容，报错退出，而不是安静地跑出零。**
      **错的读数与对的读数长得一样，是本项目最怕的输出。**
    """
    ps = case.get("path_space") or {}
    if not case.get("paths") and ps.get("paths"):
        case = dict(case)
        case["paths"] = ps["paths"]
        case["_shape_note"] = "paths 取自 path_space.paths（已自动归一）"
    if not case.get("exclusions") and ps.get("exclusions"):
        case = dict(case)
        case["exclusions"] = ps["exclusions"]
    return case, (case.get("paths") or [], case.get("exclusions") or [])


def check_case(case: dict, dyads: dict) -> dict:
    case, (top_paths, top_exc) = normalize_shape(case)
    if not top_paths and not top_exc:
        raise SystemExit(
            "⛔ 这个案例里【找不到任何路径或排除断言】。\\n"
            "   查过两处：顶层 paths/exclusions、path_space.paths/exclusions —— 都是空的。\\n"
            "   ⇒ 拒绝输出「可判判断总数 0」这种看起来正常的空报告。\\n"
            "   （这正是「错的读数与对的读数长得一样」那个病。）")
    rows, pending = [], []
    sources = load_sources()
    geo = load_geo()

    def judge(jid, kind, obs, window, evidence=None):
        src = (obs or {}).get("source")

        def to_manual(why):
            pending.append({"judgment_id": jid, "kind": kind,
                            "observable_object": (obs or {}).get("object"),
                            "observable_indicator": (obs or {}).get("indicator"),
                            "why_manual": why,
                            "window_to": (window or {}).get("to")})
            return {"verdict": "manual"}

        # ① 每条判断都可以带【人判＋依据可核】的 evidence —— 走三道机器闸
        if evidence:
            ok, why, corr = check_evidence_list(evidence, sources)
            if ok is None:
                return to_manual("evidence 不合格：%s" % why)
            # 三道过了 ⇒ 用人写的 observed 来映射，但标明依据来源是人＋存档
            v = ("falsified" if ok else "not_yet_falsified") if kind == "exclusion" \
                else ("confirmed" if ok else "missed")
            _d = "★ 人判＋依据可核（过了三道机器闸）"
            if corr.get("n_independent", 0) >= 2:
                _d += "；**%d 个独立源互证**（置信度 %s）" % (corr["n_independent"], corr["confidence"])
            if corr.get("contradiction"):
                _d += "；⛔ **源间矛盾**（同一 observable 两个来源给了相反的 observed）"
            return {"verdict": v, "basis": "human_with_evidence",
                    "evidence_slug": (evidence[0] if isinstance(evidence, list)
                                      else evidence).get("slug"),
                    "corroboration": corr,
                    "detail": _d}

        if not src:
            return to_manual("没有 source 也没有 evidence ⇒ 没有任何依据")
        r = check_any(dyads, geo, src)
        if r is None:
            return to_manual("source 的写法本工具不认识：%s" % src)
        r["source"] = src
        # ★★ 映射交给这里做，按【断言方向】——
        #   修之前我把 source 的真假直接当成断言的真假，结果排除断言 X01
        #   「盟军入侵伊拉克」在窗口内无事件时被判成「❌ 证伪」。**反了。**
        #   排除断言：观察到了 ⇒ 证伪；**没观察到 ⇒ 尚未被证伪（永远不是「证实」）**
        #   路径阶段：观察到了 ⇒ 确认；没观察到 ⇒ 落空
        #   数据不够   ⇒ 判「数据不够」，两样都不许说
        obs_r = r.get("observed")
        if obs_r is None:
            r["verdict"] = "insufficient_data"
        elif kind == "exclusion":
            r["verdict"] = "falsified" if obs_r else "not_yet_falsified"
        else:
            # ★★ 这里曾经写成 `if obs` —— 而 `obs` 是【函数参数】(observable 字典)，
            #   永远是真值 ⇒ **所有走数据层的路径阶段都被判成「确认」**，
            #   连「窗口内无事件记录」的 P02/占领巴格达 也是。
            #   根因：我为了加 evidence 把局部变量改名成 obs_r，漏改了这一行。
            #   **变量遮蔽，而且距离很近，读代码看不出来。**
            r["verdict"] = "confirmed" if obs_r else "missed"
        return r

    # ① 排除断言：发生了 ⇒ 证伪
    for x in case.get("exclusions", []):
        r = judge(x["id"], "exclusion", x.get("observable"), x.get("window"), x.get("evidence"))
        rows.append(("排除", x["id"], x.get("content"), r))

    # ② 路径推演：只数 discriminating 的
    path_results = []
    for p in case.get("paths", []):
        disc = [s for s in p.get("stages", []) if s.get("discriminating")]
        verdicts = []
        for i, st in enumerate(disc, 1):
            jid = "%s/%s#%d" % (p["id"], st["stage"], i)
            r = judge(jid, "path_stage", st.get("observable"), st.get("window"), st.get("evidence"))
            rows.append(("路径", jid, st["stage"], r))
            verdicts.append((st, r.get("verdict")))
        # ★★ G6：因果链前缀规则
        cr = apply_causal_prefix(p, verdicts)
        cr["path_id"] = p["id"]
        cr["path_label"] = p.get("label")
        path_results.append(cr)

    auto = [r for _k, _i, _c, r in rows
            if r.get("verdict") != "manual" and r.get("basis") != "human_with_evidence"]
    ev = [r for _k, _i, _c, r in rows if r.get("basis") == "human_with_evidence"]
    manual = [r for _k, _i, _c, r in rows if r.get("verdict") == "manual"]
    return {"rows": rows, "pending": pending, "n_judgeable": len(rows),
            "prob_space": check_probability_space(case),
            "n_auto": len(auto), "n_evidence": len(ev), "n_manual": len(manual),
            "paths": path_results}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    dyads = load_dyads()
    files = []
    if "--all" in sys.argv:
        _ids = {}
        for f2 in sorted(os.listdir(FILLED)):
            if not f2.endswith(".json"):
                continue
            try:
                _j = json.load(io.open(os.path.join(FILLED, f2), encoding="utf-8"))
                _ids.setdefault(_j.get("run_id"), []).append(f2)
            except Exception:                                  # noqa: BLE001
                pass
        _dup = {k: v for k, v in _ids.items() if len(v) > 1}
        if _dup:
            print("⛔ **同一个 run_id 有多个文件** —— 没人知道哪份是新的：")
            for k2, v2 in _dup.items():
                print("   %s ⇒ %s" % (k2, " ／ ".join(v2)))
            print("   ⇒ 这正是「两份同名的文件」那个病。**先解决它，再看读数。**")
            return 1
        files = sorted(os.path.join(FILLED, f) for f in os.listdir(FILLED) if f.endswith(".json"))
    else:
        files = [a for a in sys.argv[1:] if a.endswith(".json")]
    if not files:
        print("用法：python case_check.py <案例.json> | --all")
        return 1

    for fp in files:
        with io.open(fp, encoding="utf-8") as fh:
            case = json.load(fh)
        try:
            r = check_case(case, dyads)
        except SystemExit:
            # ★ 空壳不该让 --all 崩掉 —— 它是【正常状态】（刚由 s1.py 建出来、还没填）。
            #   但也不能安静跳过：要报出来，否则「跑了 6 个案例」会被读成「6 个都跑了」。
            print("=" * 96)
            print("# %s" % os.path.basename(fp))
            print("  ⏳ 空壳（还没有 paths/exclusions）—— 已跳过，未计入读数。")
            print("     ⇒ 它需要人填。**跳过 ≠ 通过。**")
            continue
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

        print()
        print("  ── ★★ G6 因果链（前缀规则）：阶段 n 的确认只在 1..n-1 也确认时才算这条路径的")
        for pr in r["paths"]:
            # ★ undecided 必须与 missed 分开印 ——
            #   独立操作者实测的坑：5 条路径全印「✖️ 链断在开头」，而那 5 条【一条都没判】。
            mark = {"confirmed": "✅ 链式确认", "partial": "◐ 部分",
                    "missed": "✖️ 链断在开头",
                    "undecided": "⏳ 前缀未判（不是判了没中）",
                    "open": "— 无可判阶段"}[pr["path_verdict"]]
            print("     %-34s %s（前缀连续命中 %d/%d）"
                  % (pr["path_label"][:34], mark, pr["chain_hits"], pr["chained_total"]))
            if pr["isolated_confirmations"]:
                print("        ⚠️ 孤立确认：%s" % "、".join(pr["isolated_confirmations"]))
                print("           ⇒ 这些阶段确认了，但【不是这条路径说的原因造成的】")
        if any(pr["isolated_confirmations"] for pr in r["paths"]):
            print("     %s" % r["paths"][0]["limit"])

        ps = r["prob_space"]
        print()
        print("  ── ★ G4 概率空间（路径概率之和应当跨过 1.00）")
        if ps["n"] == 0:
            print("     （没有一条路径填了可解读的概率）")
        else:
            mark = {"consistent": "✅ 自洽", "gap": "⚠️ 可能没穷尽",
                    "conflict": "⛔ 互相矛盾"}[ps["verdict"]]
            print("     %d 条路径：区间 %.2f ~ %.2f　%s" % (ps["n"], ps["lo_sum"], ps["hi_sum"], mark))
            print("     %s" % ps["detail"])
            if ps.get("coarse"):
                print("     ⚠️ 其中 %d 条写的是 high/medium/low（**粗**）—— 它不携带空间自洽性" % ps["coarse"])
            if ps.get("missing"):
                print("     ⚠️ %d 条【没填】概率：%s —— 没填 ≠ 填了 0"
                      % (len(ps["missing"]), "、".join(str(x) for x in ps["missing"][:3])))

        print()
        print("  ── ★ pending_manual 队列")
        if r["pending"]:
            for p in r["pending"]:
                print("     ⏳ %s" % p["observable_indicator"])
                print("        对象：%s ｜ 为什么只能人工：%s" % (p["observable_object"], p["why_manual"]))
        else:
            print("     （空）")
        tot = r["n_judgeable"]
        print("\n  ── 读数")
        print("     可判判断总数（排除 ＋ 区分性阶段）：%d" % tot)
        print("     ① 机器自动判（数据层直接判）：%d" % r["n_auto"])
        print("     ② 人判＋依据可核（过了三道机器闸）：%d" % r["n_evidence"])
        print("     ③ 待人工（连依据都没有）：%d" % r["n_manual"])
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
    # ★★ 词边界匹配 —— 裸子串让 'CN' 命中 N**SCN**、'IN' 命中 **IN**dia
    # ★ 注意：'CN' 在 'China' 里【本来就不存在】—— 让它成立的是【别名表】，
    #   不是词边界。词边界管的是「短码不许命中别的词内部的片段」。
    # ★★ 依据核验的第①道闸：索引里每一个 slug 都必须能被解析出来。
    #   修之前 8/8 都解析不出来，而【没有任何自证碰过这条路径】。
    _srcs = load_sources()
    if _srcs:
        _miss = [r["slug"] for r in _srcs.values()
                 if r.get("slug") and r["slug"] not in _srcs]
        ck("★★索引里每一个 slug 都能被 load_sources() 解析出来（第①道闸的前提）",
           not _miss, str(_miss[:3]))
        # ★ 去重后再数 —— _srcs 里每个来源占【两个】key（文件名与 slug），
        #   第一版我拿 16 跟 8 比，断言必挂。**这又是一次「两个数语义不同却并排比」。**
        _uniq = list({id(r): r for r in _srcs.values()}.values())
        _fn_ok = [r for r in _uniq
                  if (r.get("archived_snapshot") or "").split("/")[-1] in _srcs]
        ck("★★按【文件名】写也能查到（两种命名空间都支持）",
           len(_fn_ok) == len(_uniq), "%d / %d" % (len(_fn_ok), len(_uniq)))
        _one = list({id(r): r for r in _srcs.values()}.values())[0]
        _ok, _why = check_evidence(
            {"slug": _one["slug"], "observed": True}, _srcs)
        ck("★★用 slug（不带扩展名）写 evidence 必须能过闸①",
           "① 依据" not in _why, _why or "过了")
    # ★★ S1.2 交叉印证（抄 2026-07-25 方案 §5.2）
    _sw = load_sources()
    _a = next(r for r in {id(x): x for x in _sw.values()}.values()
              if r.get("witness_type") == "contemporary" and r.get("tier") == "P0")
    _b = next(r for r in {id(x): x for x in _sw.values()}.values()
              if r.get("witness_type") == "contemporary" and r.get("url", "").find("jta.org") > 0)
    ok1, w1, c1 = check_evidence_list([{"slug": _a["slug"], "observed": False,
                                        "outlet": "A"}, {"slug": _b["slug"],
                                        "observed": False, "outlet": "B"}], _sw)
    ck("★★两个独立源 ⇒ n_independent=2 且置信度高于单源",
       c1.get("n_independent") == 2 and c1.get("confidence") > (c1.get("base_reliability") or 0),
       str(c1.get("confidence")))
    ck("★★两个来源 observed 相反 ⇒ 标 contradiction",
       check_evidence_list([{"slug": _a["slug"], "observed": True, "outlet": "A"},
                            {"slug": _b["slug"], "observed": False, "outlet": "B"}],
                           _sw)[2].get("contradiction") is True)
    ck("★同一 outlet 的两篇【不算】独立源",
       check_evidence_list([{"slug": _a["slug"], "observed": False, "outlet": "A"},
                            {"slug": _a["slug"], "observed": False, "outlet": "A"}],
                           _sw)[2].get("n_independent") == 1)
    ck("★单源也能过（向后兼容）",
       check_evidence_list({"slug": _a["slug"], "observed": False}, _sw)[0] is False)
    ck("★★给不出 reliability ⇒ 不给置信度（不猜）",
       check_evidence_list([{"slug": next(r["slug"] for r in _sw.values()
                                          if r.get("reliability") is None),
                             "observed": False, "outlet": "W"}], _sw)[2].get("confidence") is None)
    ck("★★word_in：短码必须整词匹配（'CN' 不命中 ''NSCN''-IM 里的片段）",
       word_in("CN", "NSCN-IM") is False and word_in("CN", "NS CN IM") is True,
       "%s / %s" % (word_in("CN", "NSCN-IM"), word_in("CN", "NS CN IM")))
    ck("★★别名解析后 'China' 能命中（长名允许子串）",
       word_in(resolve("CN")[0], "Government of China") is True,
       str(resolve("CN")))
    ck("★★word_in：长名允许作子串（'United States of America'）",
       word_in("United States of America", "Government of United States of America") is True)
    # ★★ 别名表必须认得 CN/IN/PK —— 否则会静默判到错误的双边对
    ck("★★find_dyads(CN,IN) 必须返回中印对（不许是 India||NSCN-IM）",
       find_dyads(dyads, "CN", "IN") == ["Government of China || Government of India"],
       str(find_dyads(dyads, "CN", "IN")))
    ck("★★find_dyads(IN,PK) 必须非空（数据里有 1989–2025 完整记录）",
       find_dyads(dyads, "IN", "PK"), str(find_dyads(dyads, "IN", "PK")))
    _rd = check_ucdp_deaths(dyads, "UCDP:deaths(CN, IN, 2020, 20)")
    ck("★★deaths(CN,IN,2020) 的真值是 25（错报过 7 —— 那是印度 NSCN-IM 的数）",
       "25" in (_rd or {}).get("detail", ""), str(_rd))
    # ★★ 产物接口：path_space.paths 必须被读到
    _pp = {"path_space": {"paths": [{"id": "T", "label": "L", "stages": [
        {"stage": "s", "discriminating": True,
         "observable": {"object": "甲", "indicator": "乙"}}]}], "exclusions": []}}
    _cc, (_p, _e) = normalize_shape(_pp)
    ck("★★path_space.paths 会被归一读到（否则照骨架填的人会得到空报告）", len(_p) == 1, str(len(_p)))
    ck("★归一后带上说明", "_shape_note" in _cc, str(_cc.get("_shape_note")))
    try:
        check_case({"path_space": {"paths": [], "exclusions": []}}, dyads)
        ck("★★两处都空 ⇒ 必须报错退出，不许安静输出「可判判断总数 0」", False, "没有报错")
    except SystemExit:
        ck("★★两处都空 ⇒ 必须报错退出，不许安静输出「可判判断总数 0」", True)
    # ★★ G6：「没判」不许被当成「落空」
    #   ★ 就地定义 _st —— 这是【第三次】把自证插在变量定义之前了（前两次是 dyads、idx）。
    #     同一个毛病：插到文件里却没看上下文。所以这次不依赖别处的定义。
    _st = lambda n, v: ({"stage": n}, v)                      # noqa: E731
    _c = apply_causal_prefix({}, [_st("a", "manual"), _st("b", "confirmed")])
    ck("★★G6：前缀是 manual ⇒ 判 undecided，不是 missed（「没判」≠「判了没中」）",
       _c["path_verdict"] == "undecided", str(_c["path_verdict"]))
    _c2 = apply_causal_prefix({}, [_st("a", "missed"), _st("b", "confirmed")])
    ck("★★G6：前缀是 missed ⇒ 仍然是 missed（两者必须分得开）",
       _c2["path_verdict"] == "missed", str(_c2["path_verdict"]))
    # ★★ not() 的 detail 要写出取反后的语义
    _g2 = load_geo()          # 就地取，不依赖别处的 _g
    _nr = check_any(dyads, _g2, "UCDP:not(dyad_present(IQ, KW, 1992-1995))")
    ck("★★not() 的 detail 说明取反后的语义（原句是取反前的，只看 ↳ 会被误导）",
       "取反后：观察到了" in (_nr or {}).get("detail", ""), str(_nr)[:90])
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
    # ★★ 地理判据：区分「有限冲突」与「全面入侵」
    _g = load_geo()
    ck("★★geo 数据存在（RU-UA 有按州的记录）", bool(_g.get("RU-UA")), str(list(_g)[:3]))
    _r = check_geo_present(dyads, _g2, "UCDP:geo_present(RU, UA, Kyiv, 2022, 1)")
    ck("★★geo_present：2022 基辅出现在战斗记录里 ⇒ observed=True",
       _r and _r["observed"] is True, str(_r))
    _r = check_geo_present(dyads, _g, "UCDP:geo_present(RU, UA, Kyiv, 2014, 1)")
    ck("★★geo_present：2014 基辅【没有】⇒ observed=False（这就是它区分得开的原因）",
       _r and _r["observed"] is False, str(_r))
    _r = check_geo_breadth(dyads, _g, "UCDP:geo_breadth(RU, UA, 2022, 10)")
    ck("★★geo_breadth：2022 铺开 ≥10 个州 ⇒ observed=True",
       _r and _r["observed"] is True, str(_r))
    _r = check_geo_breadth(dyads, _g, "UCDP:geo_breadth(RU, UA, 2014, 10)")
    ck("★★geo_breadth：2014 只 1 个州 ⇒ observed=False", _r and _r["observed"] is False, str(_r))
    _r = check_geo_present(dyads, _g, "UCDP:geo_present(CN, IN, Kyiv, 2022, 1)")
    ck("★★geo 里没有的对 ⇒ 判「数据不够」，不许判「没有事件」",
       _r and _r["observed"] is None, str(_r))
    # ★★ not() 取反
    _r = check_any(dyads, _g, "UCDP:not(geo_breadth(RU, UA, 2022, 100))")
    ck("★★not()：2022 铺开 30 州、阈值 100 ⇒ 原判 False ⇒ 取反 True",
       _r and _r["observed"] is True, str(_r))
    _r = check_any(dyads, _g, "UCDP:not(geo_present(RU, UA, Kyiv, 2014, 1))")
    ck("★★not()：2014 基辅无战斗 ⇒ 原判 False ⇒ 取反 True", _r and _r["observed"] is True, str(_r))
    _r = check_any(dyads, _g, "UCDP:not(geo_present(CN, IN, Kyiv, 2022, 1))")
    ck("★★not() 遇上「数据不够」⇒ 仍然是「数据不够」，不许被取反成 True",
       _r and _r["observed"] is None, str(_r))
    ck("★not() 的 detail 里标出取反了", "取反" in (_r.get("detail") or ""), str(_r.get("detail")))
    # ★★ G6 前缀规则：四个已有案例
    def _st(n, v): return ({"stage": n}, v)
    _c = apply_causal_prefix({}, [_st("a","confirmed"), _st("b","confirmed")])
    ck("★★G6：前缀全中 ⇒ confirmed", _c["path_verdict"] == "confirmed", str(_c["path_verdict"]))
    _c = apply_causal_prefix({}, [_st("a","missed"), _st("b","confirmed")])
    ck("★★G6：前缀断在开头 ⇒ missed，并报出孤立确认",
       _c["path_verdict"] == "missed" and _c["isolated_confirmations"] == ["b"], str(_c))
    _c = apply_causal_prefix({}, [_st("a","confirmed"), _st("b","missed"), _st("c","confirmed")])
    ck("★★G6：中途断 ⇒ partial，孤立确认是 c",
       _c["path_verdict"] == "partial" and _c["isolated_confirmations"] == ["c"], str(_c))
    ck("★★G6：限度写在返回值里（抓不了「前缀中了但原因不同」）",
       "部分修" in _c["limit"], _c["limit"][:40])
    ck("★G6：无可判阶段 ⇒ open", apply_causal_prefix({}, [])["path_verdict"] == "open")
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

        # ★★ 路径阶段的判定必须与 observed 一致 —— 上面那个变量遮蔽 bug 就是这条该抓的
        _pv = {j: r.get("verdict") for k, j, _c, r in res["rows"] if k == "路径"}
        ck("★★路径阶段：窗口内【无】事件记录的，不许判成「确认」",
           not any(v == "confirmed" for j, v in _pv.items()
                   if j.startswith("IQ-KW@1991-P02") or "战争跨年" in j),
           str({j: v for j, v in _pv.items() if "P02" in j or "战争跨年" in j}))
        ck("★★路径阶段：确实无记录的 P01/停在边境 应判「确认」（它的 observable 就是「无」）",
           _pv.get("IQ-KW@1991-P01/停在边境#1") == "confirmed",
           str(_pv.get("IQ-KW@1991-P01/停在边境#1")))
        ck("★★总体：路径阶段里既有 confirmed 也有 missed（不是一边倒）",
           {"confirmed", "missed"} <= set(_pv.values()), str(sorted(set(_pv.values()))))

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
