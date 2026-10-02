# -*- coding: utf-8 -*-
"""case_skeleton.py —— 案例骨架生成器（用户选的 a 段：纯机器的那一半）

★★ 做什么
   从数据层（UCDP GED v26.1 的全部双边对）里选出一批「对-年」单元，
   自动生成**案例骨架**：
     ✅ 能机器给的，给全，并且每条都带出处
     ❌ 不能机器给的（事件原文、时间锁定、路径空间、排除断言），置 None 并标 needs_human
   **不猜。** 这是 B4.1 迁移器已验证的同一套规矩。

★★ 为什么这不只是「批量生产案例」
   「量化研究一批历史案例」里，**能量化的是【事实层】，不是【判断层】**。
   路径空间与排除断言是判断 —— 它们只能由人填，而它们才是这个项目真正值钱的东西。
   ⇒ 骨架生成器把批量的部分做掉，把人留在判断上。

★★ 零效应臂（内建，不是可选）
   每个高冲突案例，配一个**同一个双边对**的安静年作对照。
   理由：本项目栽过一次严重的选择偏倚 —— 八维的 ρ 从 +0.507 被打到 +0.263，
   因为样本里只有「有冲突活动」的主体。
   ⇒ 只收「爆发了的案例」，量出来的分辨率必然虚高。
   所以对照臂不是补充，是**必需**。

运行：  python case_skeleton.py --report       # 只读：候选池与选择偏倚读数
        python case_skeleton.py --build N     # 生成 N 个案例（两臂各半）
        python case_skeleton.py --selftest
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "ucdp_actors.json")
OUT_DIR = os.path.join(HERE, "data", "cases", "skeletons")
WS = os.path.dirname(HERE)

# 对齐 UCDP 自身的战争定义（与本项目 WAR_DEATH_THRESHOLD 同源、已冻结）
WAR_DEATHS = 1000
# 对照臂上限：年度死亡低于此数视为「安静年」
QUIET_DEATHS = 25          # UCDP GED 对组织化暴力的收录下限量级

ARCHIVE_DIRS = [os.path.join(WS, "ConStruct_Archive"), os.path.join(WS, "actors")]


# ══ 数据层 ══════════════════════════════════════════════════════════════════════
def load_dyads() -> dict:
    if not os.path.exists(DATA):
        return {}
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh).get("dyads") or {}


def clean_name(n: str) -> str:
    """把 UCDP 的行为体名修成人能读的样子。★ 只做确定性替换，不做猜测性归并。"""
    n = re.sub(r"^Government of\s+", "", n.strip())
    n = re.sub(r"\s*\(.*?\)\s*", " ", n)
    return re.sub(r"\s+", " ", n).strip(" ,")


def archive_index() -> dict:
    """档案里有哪些主体名（用于 S2a 的「在不在档案里」判定）。"""
    idx = {}
    for root in ARCHIVE_DIRS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if not f.endswith(".md"):
                    continue
                stem = os.path.splitext(f)[0]
                if 1 <= len(stem) <= 30:
                    idx.setdefault(stem, os.path.relpath(os.path.join(dirpath, f), WS))
    return idx


def archive_hit(name: str, idx: dict):
    """在不在档案里。★ 找不到就返回 None —— 不猜、不做模糊归并。"""
    if not name:
        return None
    if name in idx:
        return idx[name]
    for k, v in idx.items():
        if len(k) >= 2 and (k in name or name in k):
            return v
    return None


# ══ 选例 ════════════════════════════════════════════════════════════════════════
def units(dyads: dict) -> list:
    """把 dyads 摊平成「对-年」单元。返回 [(dyad, year, events, deaths)]。"""
    out = []
    for k, v in dyads.items():
        for y, cell in v.items():
            if y == "_cid" or not isinstance(cell, list) or len(cell) != 2:
                continue
            out.append((k, y, int(cell[0]), int(cell[1])))
    return out


def select(dyads: dict, n_high: int, n_quiet: int, states_only: bool = False) -> tuple:
    """选两臂。

    ★ 第一版我犯了个错：对照臂从【所有】双边对里挑安静年，于是高冲突臂讲 Israel-Hamas、
      对照臂讲 Israel-PFLP-GC —— **两个不同的对，差的不只是「那一年」**。
      那样的对照是松的。改为**优先从【同一批对】里取对照年** ⇒ 真正的配对设计。

    ★ 第二个发现（写进了报告）：UCDP 是【冲突数据集】，它给不出「真正的零」。
      最低也是一年 1-3 起事件。所以这里的「对照臂」严格说是【低冲突臂】，
      不是零效应臂。要做真零，需要另一个数据源（COW MID 的和平年／GDELT 全部事件）。
    """
    if states_only:                                  # ★ 用户定的范围：先只做国家主体
        dyads = {k: v for k, v in dyads.items() if is_state_state(k)}
    us = units(dyads)
    by_dyad = {}
    for d, y, e, dd in us:
        by_dyad.setdefault(d, []).append((y, e, dd))

    # 高冲突臂：达 UCDP 战争门槛的年。按死亡降序取，但【每个对最多取 1 年】——否则
    # 同一个对（如 RU-UA 的 2022-2025）会占满整批，那又是一次选择偏倚。
    high = [u for u in us if u[3] >= WAR_DEATHS]
    high.sort(key=lambda u: -u[3])
    seen, hsel = set(), []
    for u in high:
        if u[0] in seen:
            continue
        seen.add(u[0])
        hsel.append(u)
        if len(hsel) >= n_high:
            break

    # 对照臂：★ 先从上面对【已入选的那批对】里取，取不满再向外扩。
    def quietest(d):
        ys = [(y, e, dd) for (y, e, dd) in by_dyad.get(d, []) if dd <= QUIET_DEATHS]
        return min(ys, key=lambda t: (t[2], t[0])) if ys else None

    qsel, used = [], set()
    for u in hsel:                                   # ① 优先：与高冲突臂【同一个对】
        qt = quietest(u[0])
        if qt:
            qsel.append((u[0], qt[0], qt[1], qt[2]))
            used.add(u[0])
    for d in sorted(by_dyad):                        # ② 扩：其余对里最安静的
        if len(qsel) >= n_quiet:
            break
        if d in used:
            continue
        qt = quietest(d)
        if qt:
            qsel.append((d, qt[0], qt[1], qt[2]))
            used.add(d)
    qsel = qsel[:n_quiet]
    return hsel, qsel


# ══ 骨架 ════════════════════════════════════════════════════════════════════════
def is_state_state(dyad: str) -> bool:
    """国家对国家（用户 2026-10-02 定的范围：**先只做国家主体**）。

    UCDP 的 side_a 若为国家，写的是 `Government of <国名>`；非国家行为体则不是
    （`Hamas` / `IS` / `TTP` / `ETIM` / `Kachin Independence Organization`…）。
    ⇒ 两边都以 `Government of` 开头的，才算是国家对国家。

    ★ 这个判定是【保守】的：`Government of X` 里 X 也可能是非国家实体
      （如历史上的傀儡政权），但那种情况极少，宁可少收不可误收。
    """
    a, _, b = dyad.partition(" || ")
    return a.startswith("Government of") and b.startswith("Government of")


def case_id_for(dyad: str, year: str) -> str:
    """案例 id。★ 必须唯一 —— 第一版是 `re.sub(...)[:40] + '@' + year`，
    结果 `Bosnia-Herzegovina || Serbian Republic of Bosnia-Herzegovina`(high)
    与 `Bosnia-Herzegovina || Serbian irregulars`(quiet) 都截断到
    `Government_of_Bosnia_Herzegovina_Serbian@1992` ⇒ **后写的静默盖掉先写的**，
    12 个骨架只落了 11 个文件。
    ⇒ 加一个内容散列后缀；并且 build() 里撞名【报错】而不是覆盖。
    """
    h = hashlib.sha1(dyad.encode("utf-8")).hexdigest()[:6]
    return "%s_%s@%s" % (re.sub(r"[^\w]+", "_", dyad)[:36], h, year)


def skeleton(dyad: str, year: str, events: int, deaths: int, arm: str, idx: dict) -> dict:
    a_raw, _, b_raw = dyad.partition(" || ")
    a, b = clean_name(a_raw), clean_name(b_raw)
    ah, bh = archive_hit(a, idx), archive_hit(b, idx)
    # ★ UCDP 的 side_a/side_b 可以是【联盟】（逗号分隔的多方）。第一版把它们当成一个主体名了。
    #   这是事实，不是缺陷 —— 但要显式标出来，否则「主体」这个词会被误用。
    coalition = [x for x in (a, b) if "," in x]

    s = {
        "schema": "construct-case-skeleton-v1",
        "case_id": case_id_for(dyad, year),
        "arm": arm,                               # high = 高冲突臂 / quiet = 对照臂（零效应臂）
        "selection": {                            # ★ 透明：这个案例为什么被选中
            "rule": "年度战斗死亡 ≥ %d ⇒ 高冲突臂；同一双边对里死亡最少的年 ⇒ 对照臂" % WAR_DEATHS,
            "dyad_raw": dyad, "year": year,
            "events": events, "deaths": deaths,
        },
        # ── F1/F3：机器【没有】的，置 None 并标出 ──
        "event": {
            "text": None,                         # F1：原文。数据层只有计数，没有报道文本
            "source": {"dataset": "UCDP GED v26.1", "dyad": dyad, "year": year,
                       "events": events, "deaths": deaths},
            "event_date": year,
            "time_lock": None,                    # F3：只看该年当时已知的 —— 必须人定
            "actors": [a, b],
        },
        # ── 机器能给的，给全，带出处 ──
        "data_layer": {
            "ucdp": {"dyad": dyad, "year": year, "events": events, "deaths": deaths,
                     "war_threshold": WAR_DEATHS, "meets_war_threshold": deaths >= WAR_DEATHS},
            "archive": {
                a: {"ref": ah, "status": "有档案" if ah else "★ 无档案"},
                b: {"ref": bh, "status": "有档案" if bh else "★ 无档案"},
            },
            # ★ 联盟 side 要显式标出 —— 否则「主体」这个词会被误用
            "coalition_sides": coalition,
            "side_is_coalition": bool(coalition),
        },
        # ── 判断层：空的模板。这是人要做的事 ──
        "path_space": {
            "paths": [],
            "exclusions": [],
            "_fill": {
                "每条路径": {
                    "label": "一句话（如「联军解放科威特、不推翻萨达姆」）",
                    "stages": [{"stage": "阶段名", "discriminating": "布尔 —— 只数 true 的",
                                "observable": {"object": "谁/什么被观察", "indicator": "看到什么算发生",
                                               "threshold": None, "source": None},
                                "window": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}}],
                    "rules_out": ["这条路径排除了什么 —— 必填，信息量在排除上"],
                    "probability": "high / medium / low",
                },
                "每条排除断言": {
                    "content": "被排除的路径", "direction": "exclude",
                    "observable": {"object": None, "indicator": None},
                    "window": {"from": None, "to": None},
                },
                "两条硬规矩": [
                    "区分点写在【行为】上，不是【遭遇】上（海湾那次的教训）",
                    "区分点必须让不同路径在该阶段的 observable 不同（否则它不是区分点）",
                ],
            },
        },
        "needs_human": (["event.text", "event.time_lock",
                         "path_space.paths", "path_space.exclusions"]
                        + (["data_layer.actors —— 这一边的 side 是【联盟】，要先拆成单个主体"]
                           if coalition else [])),
    }
    return s


def build(n: int, states_only: bool = True) -> tuple:
    dyads = load_dyads()
    idx = archive_index()
    h, q = select(dyads, (n + 1) // 2, n // 2, states_only=states_only)
    os.makedirs(OUT_DIR, exist_ok=True)
    made, seen = [], {}
    for arm, sel in (("high", h), ("quiet", q)):
        for dyad, year, ev, dd in sel:
            s = skeleton(dyad, year, ev, dd, arm, idx)
            cid = s["case_id"]
            # ★ 撞名【报错】而不是静默覆盖 ——
            #   第一版就是 12 个骨架只落了 11 个文件，少的那一个被盖掉且没人知道。
            if cid in seen:
                raise RuntimeError("case_id 撞名：%s\n  已用于 %s\n  现在用于 %s"
                                   % (cid, seen[cid], dyad))
            seen[cid] = dyad
            with io.open(os.path.join(OUT_DIR, cid + ".json"), "w",
                         encoding="utf-8", newline="\n") as fh:
                json.dump(s, fh, ensure_ascii=False, indent=2)
            made.append(s)
    return made, h, q


# ══ 报告 ════════════════════════════════════════════════════════════════════════
def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    dyads = load_dyads()
    if not dyads:
        print("没有 data/ucdp_actors.json 的 dyads —— 先跑 ucdp_readout.py --build")
        return 1
    us = units(dyads)
    idx = archive_index()

    if "--build" in sys.argv:
        n = 12
        for i, a in enumerate(sys.argv):
            if a == "--build" and i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
                n = int(sys.argv[i + 1])
        made, h, q = build(n)
        print("生成 %d 个骨架（高冲突 %d ＋ 对照 %d）到 %s"
              % (len(made), len(h), len(q), os.path.relpath(OUT_DIR, WS)))

    high = [u for u in us if u[3] >= WAR_DEATHS]
    quiet = [u for u in us if u[3] <= QUIET_DEATHS]
    print("=" * 96)
    print("# 案例骨架 · 候选池与选择偏倚读数")
    print("=" * 96)
    print("  数据源：UCDP GED v26.1（%d 个双边对，%d 个「对-年」单元）" % (len(dyads), len(us)))
    print("  年份范围：%s → %s" % (min(u[1] for u in us), max(u[1] for u in us)))
    print()
    print("  ── 两臂")
    print("     高冲突臂（死亡 ≥ %d）      %5d 个单元，涉及 %d 个双边对"
          % (WAR_DEATHS, len(high), len(set(u[0] for u in high))))
    print("     对照臂  （死亡 ≤ %d）      %5d 个单元，涉及 %d 个双边对"
          % (QUIET_DEATHS, len(quiet), len(set(u[0] for u in quiet))))
    withq = len(set(u[0] for u in quiet) & set(u[0] for u in high))
    print("     **两臂都有数据的双边对：%d 个** ← 只有这些对能做【配对对照】" % withq)
    print()
    print("  ── ★ 选择偏倚读数（这是本工具存在的理由之一）")
    print("     高冲突臂占全部单元的 %.1f%%" % (100.0 * len(high) / max(1, len(us))))
    print("     ⇒ 若只收这一臂，样本 100% 是「爆发了的对-年」")
    print("     ⇒ 量出来的分辨率必然虚高（本项目实测过一次：ρ 从 +0.507 掉到 +0.263）")
    print("     ⇒ **所以对照臂不是补充，是必需。**")
    print()
    print("  ── ★ 对照臂的诚实限度（UCDP 是【冲突数据集】，给不出「真正的零」）")
    lo = min(u[3] for u in quiet) if quiet else None
    print("     对照臂最低年度死亡 = %s，但**事件数仍 >0** ⇒ 它是【低冲突臂】，不是零效应臂" % lo)
    print("     ⇒ 要真正的零效应臂，需要另一个源（COW MID 的无争端年 ／ GDELT 的全部事件）")
    print()
    print("  ── 档案覆盖（S2a：不在档案里就要显式标「无档案」）")
    names = set()
    for k in dyads:
        a, _, b = k.partition(" || ")
        names.add(clean_name(a))
        names.add(clean_name(b))
    hit = [n for n in names if archive_hit(n, idx)]
    print("     候选主体 %d 个，其中 %d 个有档案，**%d 个无档案**"
          % (len(names), len(hit), len(names) - len(hit)))
    print("     （无档案不是缺陷 —— 是 S2a 要显式标出来的事实）")
    print("=" * 96)
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

    print("# case_skeleton 自证")
    # ★ 用户定的范围：先只做国家主体
    ck("★国家对国家判定：Government of X || Government of Y ⇒ True",
       is_state_state("Government of Iraq || Government of Kuwait") is True)
    ck("★国家对国家判定：含非国家行为体 ⇒ False",
       is_state_state("Government of Israel || Hamas") is False
       and is_state_state("Government of China || ETIM") is False)
    ck("★clean_name 去掉 Government of",
       clean_name("Government of Iraq") == "Iraq", clean_name("Government of Iraq"))
    ck("★clean_name 去掉括号里的别名",
       clean_name("Government of Russia (Soviet Union)") == "Russia",
       clean_name("Government of Russia (Soviet Union)"))
    ck("★clean_name 对已干净的名字不动", clean_name("Hamas") == "Hamas")

    dyads = load_dyads()
    ck("★能读到双边对（>50 个）", len(dyads) > 50, str(len(dyads)))
    # ★ 这个数字是要紧的：只做国家主体后，池子从 126 对缩到 12 对
    _ss = {k: v for k, v in dyads.items() if is_state_state(k)}
    ck("★★states_only 过滤后池子里【没有任何非国家对】",
       all(is_state_state(k) for k in _ss))
    ck("★★国家对国家的对数【远小于】全部对数 —— 这是取样能力的天花板",
       len(_ss) < len(dyads) / 5, "国家 %d / 全部 %d" % (len(_ss), len(dyads)))
    _us = units(_ss)
    _h = [u for u in _us if u[3] >= WAR_DEATHS]
    ck("★★国家对国家里【达战争门槛的单元数是个位数】—— 撑不起「一批」",
       len(_h) < 10, str(len(_h)))
    us = units(dyads)
    ck("★能摊平成对-年单元（>500）", len(us) > 500, str(len(us)))
    ck("★单元结构正确（4 元组，年-计数-死亡）",
       all(len(u) == 4 and isinstance(u[3], int) for u in us[:50]))

    h, q = select(dyads, 6, 6)
    ck("★高冲突臂非空", len(h) > 0, str(len(h)))
    ck("★对照臂非空", len(q) > 0, str(len(q)))
    ck("★★高冲突臂【每个对最多一个年】（否则同一个对占满整批 = 又一次选择偏倚）",
       len(set(u[0] for u in h)) == len(h), "%d 对 / %d 条" % (len(set(u[0] for u in h)), len(h)))
    ck("★★对照臂也每个对最多一个年",
       len(set(u[0] for u in q)) == len(q), "%d 对 / %d 条" % (len(set(u[0] for u in q)), len(q)))
    ck("★高冲突臂全部达门槛", all(u[3] >= WAR_DEATHS for u in h), str([u[3] for u in h]))
    ck("★对照臂全部低于安静线", all(u[3] <= QUIET_DEATHS for u in q), str([u[3] for u in q]))
    # ★ 对照臂必须取【死亡最小】的年，不是随便一个安静年
    ck("★★对照臂取的是该对【最安静】的年（死亡不高于该对任何一年）",
       True if not q else all(
           u[3] == min(x[2] for x in [(yy, e2, d2) for (dd, yy, e2, d2) in us if dd == u[0]])
           for u in q),
       "抽查：" + str([(u[0][:20], u[3]) for u in q[:3]]))

    idx = archive_index()
    # ★★ 配对优先：对照臂应优先取自高冲突臂用过的那些对
    h2, q2 = select(dyads, 6, 6)
    hd = set(u[0] for u in h2); qd = set(u[0] for u in q2)
    ck("★★对照臂优先与高冲突臂【配对】（交集应 >0）", len(hd & qd) > 0,
       "高 %d 对 / 对照 %d 对 / 交集 %d" % (len(hd), len(qd), len(hd & qd)))
    ck("★★UCDP 给不出「真正的零」—— 对照臂的最低死亡应仍可能 >0 或 =0，但事件数 >0",
       all(u[2] > 0 for u in q2), str([u[2] for u in q2]))
    ck("★档案索引非空（>50 个主体名）", len(idx) > 50, str(len(idx)))
    ck("★档案命中：伊拉克不在档案里（实测结论）", archive_hit("Iraq", idx) is None)
    ck("★档案命中：俄罗斯在档案里", archive_hit("Russia", idx) is not None,
       str(archive_hit("Russia", idx)))
    ck("★档案命中：找不到返回 None（不猜）", archive_hit("某个不存在的主体xyz", idx) is None)

    s = skeleton("Government of Iraq || Government of Kuwait", "1991", 100, 21790, "high", idx)
    # ★★ case_id 必须唯一 —— 第一版 [:40] 截断让两条 Bosnia 记录撞名并被静默覆盖（12→11 个文件）
    ck("★★case_id 带散列后缀，Bosnia 那两条不再撞名",
       case_id_for("Government of Bosnia-Herzegovina || Serbian Republic of Bosnia-Herzegovina", "1992")
       != case_id_for("Government of Bosnia-Herzegovina || Serbian irregulars", "1992"),
       case_id_for("Government of Bosnia-Herzegovina || Serbian irregulars", "1992"))
    ck("★case_id 对同输入稳定（可复跑）",
       case_id_for("A || B", "1991") == case_id_for("A || B", "1991"))
    ck("★骨架 schema 正确", s["schema"] == "construct-case-skeleton-v1")
    ck("★★event.text 是 None 而【不是空串】（数据层没有报道原文 —— F1 必须人补）",
       s["event"]["text"] is None, repr(s["event"]["text"]))
    ck("★★event.time_lock 是 None（F3 必须人定）", s["event"]["time_lock"] is None)
    ck("★event.text / time_lock 都进 needs_human",
       "event.text" in s["needs_human"] and "event.time_lock" in s["needs_human"])
    ck("★路径空间是空模板（判断留给人）",
       s["path_space"]["paths"] == [] and s["path_space"]["exclusions"] == [])
    ck("★模板里写了「区分点写在行为上」这条教训",
       "行为" in json.dumps(s["path_space"]["_fill"], ensure_ascii=False))
    ck("★数据层给了出处", s["data_layer"]["ucdp"]["dyad"] and s["data_layer"]["ucdp"]["year"])
    ck("★达门槛的标 True", s["data_layer"]["ucdp"]["meets_war_threshold"] is True)
    ck("★主体名已清洗（无 Government of）",
       all("Government of" not in x for x in s["event"]["actors"]), str(s["event"]["actors"]))
    ck("★无档案的要显式标出", "无档案" in json.dumps(s["data_layer"]["archive"], ensure_ascii=False))
    # ★ 联盟 side 要标出
    sc = skeleton("Government of Australia, Government of United Kingdom || Government of Iraq",
                  "2003", 95, 7927, "high", idx)
    ck("★★联盟 side 被标出（不是当成一个主体）", sc["data_layer"]["side_is_coalition"] is True,
       str(sc["data_layer"]["coalition_sides"]))
    ck("★★联盟 side 进 needs_human", any("联盟" in x for x in sc["needs_human"]),
       str(sc["needs_human"]))
    ck("★单主体 side 不误标为联盟",
       skeleton("Hamas || Government of Israel", "2023", 1, 1, "high", idx)["data_layer"]["side_is_coalition"] is False)
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
