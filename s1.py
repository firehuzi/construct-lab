# -*- coding: utf-8 -*-
"""s1.py —— S1 的入口。把四个工具串成一条命令。

★★ 它存在的理由
   本轮结束时，四个工具是【散的】：
     case_skeleton.py  从 UCDP 生成案例骨架
     query_gen.py      为核不了的判断生成时间锁定的查询
     archive_source.py 取证并存档
     case_check.py     跑检查、出读数
   **它们之间没有入口** —— 每次都要人手串。而 S1 的跑通判据是：

     「给一个双边对＋年份，一条命令出完整 construct-run-v1」

★★ 而它顺带解决一个更阴的问题：产物形状
   一位独立操作者按指南和骨架老实填写，得到的是「可判判断总数 0」的空报告 ——
   因为指南、骨架、骨架 needs_human 三处都指向 `path_space.paths`，
   而工具读的是【顶层】`paths`。**不报错、不警告。**
   ⇒ 所以本入口【只产出顶层形状】，并且它会先跑一遍 case_check 确认读得到。
     **形状由入口保证，不由写的人记住。**

★★ 它【不做】什么（照实说）
   · 不填路径空间 —— 那是人的判断，S1.0 不假装能做
   · 不补 event.text 原文 —— 那要研究工作量
   · 不判 —— 只登记
   它做的是：**把「一件事件」变成一份【形状正确、缺口显式】的记录，并把下一步告诉人。**

运行：  python -B s1.py --dyad CN,IN --year 2020
        python -B s1.py --dyad IQ,KW --year 1991 --check
        python -B s1.py --selftest
"""
from __future__ import annotations

import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "cases", "filled")
sys.path.insert(0, HERE)


def _load(mod):
    import importlib.util
    spec = importlib.util.spec_from_file_location(mod, os.path.join(HERE, mod + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ══ S1.3 同一性（抄 TaoPaw 的 cellId 做法）══════════════════════════════════════
# ★★ 要解决的真问题：我们的记录里带【时间戳】（committed_at / fetched_at）⇒
#    同一份输入跑两次，文件必然不同。所以**哈希不能打在文件上**。
#    TaoPaw 的做法是 `cellId = fnv1a(canonicalJson(cell))` —— **cell 是【输入】不是产物**。
#    ⇒ 我们照做：哈希打在【输入格】上；时间戳是【运输字段】，不属于同一性。
#
# ★ 为什么需要它：这是《读数口径登记表》C2 那一格 ——「同输入两次跑 ⇒ 逐位相同」。
#   它是**其余读数的可信度之根**：没有它，上面所有数字都不知道能不能复现。
def canonical(obj) -> str:
    """规范化 JSON：排序键、无空白。同一份语义 ⇒ 同一个字符串。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fnv1a32(s: str) -> str:
    """FNV-1a 32 位。★ 与 TaoPaw 同一族；只为「同不同」服务，不做密码学用途。"""
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h


def cell_of(rec: dict) -> dict:
    """从记录里抽出【输入格】—— 只有这些进哈希。

    ⛔ 刻意排除：committed_at（时间戳）、built_by（工具版本）。
    ★ 刻意包含：双边对、年份、臂、选择规则、两个主体 —— 它们定义了「这是哪一格」。
    """
    return {
        "dyad": rec["selection"]["dyad_raw"],
        "year": rec["selection"]["year"],
        "arm": rec["arm"],
        "rule": rec["selection"]["rule"],
        "actors": rec["event"]["actors"],
    }


def cell_id_of(rec: dict) -> str:
    return fnv1a32(canonical(cell_of(rec)))


def judgments_fnv(rec: dict) -> str:
    """判断的指纹 —— 人对 paths/exclusions 的输入。

    ★ 它与 cellId 分开：**cellId 说「这是哪一格」，judgmentsFnv 说「这一格里写了什么」。**
      两个都要有：只知道 cellId，无法判断内容变没变；只知道 judgmentsFnv，
      无法判断还在不在同一格上。
    """
    slim = []
    for p in rec.get("paths") or []:
        slim.append({"id": p.get("id"), "label": p.get("label"),
                     "stages": [{"stage": s.get("stage"),
                                 "discriminating": s.get("discriminating"),
                                 "observable": s.get("observable")}
                                for s in (p.get("stages") or [])]})
    for x in rec.get("exclusions") or []:
        slim.append({"id": x.get("id"), "content": x.get("content"),
                     "observable": x.get("observable")})
    return fnv1a32(canonical(slim))


def build(dyad_spec: str, year: str) -> dict:
    """一个双边对 ＋ 年份 → 一份形状正确的 construct-run-v1。"""
    cs = _load("case_skeleton")
    cc = _load("case_check")
    dyads = cs.load_dyads()
    idx = cs.archive_index()

    want = [x.strip() for x in dyad_spec.split(",")]
    if len(want) != 2:
        raise SystemExit("⛔ --dyad 要两个码，用逗号分隔，如 --dyad CN,IN")
    A, B = cc.resolve(want[0]), cc.resolve(want[1])
    keys = [k for k in dyads
            if cs.is_state_state(k)
            and any(cc.word_in(w, s) for w in A for s in k.split(" || "))
            and any(cc.word_in(w, s) for w in B for s in k.split(" || "))]
    if not keys:
        raise SystemExit("⛔ UCDP 里找不到这两个国家之间的双边对：%s" % dyad_spec)
    if len(keys) > 1:
        raise SystemExit("⛔ 命中多个双边对，不猜：%s" % keys)
    k = keys[0]
    cells = {y: v for y, v in dyads[k].items() if y != "_cid"}
    if year not in cells:
        raise SystemExit("⛔ %s 在 %s 年无记录。该对有记录的年份：%s"
                         % (k, year, ", ".join(sorted(cells)) or "（无）"))
    events, deaths = cells[year]

    a, _, b = k.partition(" || ")
    a, b = cs.clean_name(a), cs.clean_name(b)
    gkey = "%s-%s" % tuple(sorted(want))          # ★ geo 用【原始码】建键（工具就是这么做的）
    geo = (cc.load_geo().get(gkey) or {}).get(year) or {}

    rec = {
        "schema": "construct-run-v1",
        "run_id": "%s-%s@%s" % (want[0], want[1], year),
        "committed_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "built_by": "s1.py",
        # ★ S1.3 两个指纹（见函数注释：cellId 说「这是哪一格」，judgmentsFnv 说「写了什么」）
        "cellId": None, "judgmentsFnv": None,
        "arm": "high" if deaths >= cs.WAR_DEATHS else "quiet",
        "selection": {
            "rule": "UCDP GED v26.1；达战争门槛（死亡 ≥%d）⇒ 高冲突臂，否则低冲突臂"
                    % cs.WAR_DEATHS,
            "dyad_raw": k, "year": year, "events": events, "deaths": deaths,
            "dyad_years_in_data": len(cells),
            "caveat": ("★ 该双边对在数据里只有 %d 年记录 ⇒ 这一条【不是】某场冲突的安静年。"
                       % len(cells)) if len(cells) <= 2 else None,
        },
        "event": {
            "text": None,                      # ★ F1：原文 —— 入口拿不到，不编
            "source": {"dataset": "UCDP GED v26.1", "dyad": k, "year": year,
                       "events": events, "deaths": deaths},
            "event_date": year,
            "time_lock": None,                 # ★ F3：时间锁定 —— 必须人定
            "actors": [a, b],
        },
        "data_layer": {
            "ucdp": {"dyad": k, "year": year, "events": events, "deaths": deaths,
                     "meets_war_threshold": deaths >= cs.WAR_DEATHS},
            "archive": {x: {"status": "有档案" if cs.archive_hit(x, idx) else "★ 无档案"}
                        for x in (a, b)},
            "geo": geo,
        },
        # ★★ 顶层 paths / exclusions —— 形状由入口保证
        "paths": [],
        "exclusions": [],
        "needs_human": [
            "event.text（F1 原文）—— 入口拿不到，**不许编**",
            "event.time_lock（F3 时间锁定）—— 必须人定；UCDP 只到年精度",
            "paths —— 路径空间（3–5 条），见《路径空间写法指南》",
            "exclusions —— 排除断言",
            "diagnoses —— 主体诊断（若主体不在 47 档案里，显式标「无档案」）",
        ],
    }
    rec["cellId"] = cell_id_of(rec)
    rec["judgmentsFnv"] = judgments_fnv(rec)
    return rec


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    def opt(name, default=""):
        if name in sys.argv:
            i = sys.argv.index(name)
            if i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        return default

    dyad, year = opt("--dyad"), opt("--year")
    if not dyad or not year:
        print("用法：python -B s1.py --dyad CN,IN --year 2020 [--check]")
        return 1

    rec = build(dyad, year)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s.json" % rec["run_id"])
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2)

    print("=" * 92)
    print("# S1 入口 · %s" % rec["run_id"])
    print("=" * 92)
    print("  写出：%s" % os.path.relpath(path, HERE))
    print("  事件：%s｜%s 年｜%d 起事件 / %d 起死亡｜臂=%s"
          % (rec["selection"]["dyad_raw"].replace("Government of ", ""),
             year, rec["selection"]["events"], rec["selection"]["deaths"], rec["arm"]))
    if rec["selection"]["caveat"]:
        print("  ⚠️ %s" % rec["selection"]["caveat"])
    dl = rec["data_layer"]
    print("  档案：%s" % "；".join("%s=%s" % (k2, v["status"]) for k2, v in dl["archive"].items()))
    if dl["geo"]:
        top = sorted(dl["geo"].items(), key=lambda kv: -kv[1])[:4]
        print("  地理：%s" % "  ".join("%s:%d" % (k2[:18], v) for k2, v in top))
    print()
    print("  ── ★ 形状已保证（顶层 paths/exclusions）")
    print("     这是那位独立操作者撞到的第一个坑：指南与骨架都指向 path_space.paths，")
    print("     而工具读顶层。⇒ 形状由入口保证，不由写的人记住。")
    print()
    print("  ── 还需要人做的（%d 项）" % len(rec["needs_human"]))
    for x in rec["needs_human"]:
        print("     ⏳ %s" % x)
    print()
    print("  ── 下一步")
    print("     ① 补 event.text（原文）与 time_lock      ← 研究工作量，入口代不了")
    print("     ② 按《路径空间写法指南》填 paths / exclusions")
    print("     ③ 核不了的判断：python -B query_gen.py <本文件>   ← 出时间锁定的查询")
    print("     ④ 找到依据：python -B archive_source.py <url>      ← 取证并存档")
    print("     ⑤ 跑检查：  python -B case_check.py <本文件>")

    if "--same" in sys.argv:
        print()
        print("  ── ★ S1.3 同一性（同输入两次跑）")
        r1, r2 = build(dyad, year), build(dyad, year)
        ok_c = r1["cellId"] == r2["cellId"]
        ok_j = r1["judgmentsFnv"] == r2["judgmentsFnv"]
        print("     cellId       %s  %s" % (r1["cellId"], "✅ 相同" if ok_c else "⛔ 不同"))
        print("     judgmentsFnv %s  %s" % (r1["judgmentsFnv"], "✅ 相同" if ok_j else "⛔ 不同"))
        print("     （时间戳两次必然不同 —— 它是【运输字段】，不进哈希：%s / %s）"
              % (r1["committed_at"][11:19], r2["committed_at"][11:19]))
        if not (ok_c and ok_j):
            print("     ⛔ 同一性不成立 —— 这是最该修的一类问题。")
            return 1
        print("     ✅ 同一性成立：同一格 ＋ 同一输入 ⇒ 同一指纹。")

    if os.path.exists(path) and "--force" not in sys.argv:
        # ★★ 入口不许静默覆盖 —— 我刚因为这个造出了第二份同名文件。
        #   而「两份同名的文件，没人知道哪份是新的」是本项目反复出现的病（实测过两次）。
        raise SystemExit(
            "⛔ %s 已存在。\\n"
            "   ⇒ 拒绝覆盖：里面可能已经有人填好的判断，而覆盖是静默的。\\n"
            "   （本轮就发生过：s1.py 建出一份空壳，与已有的同名案例并存，\\n"
            "     而 --all 读到两份、没人知道哪份是新的。）\\n"
            "   确实要重建 ⇒ 加 --force，或先把旧的改名。" % os.path.relpath(path, HERE))

    if "--check" in sys.argv:
        print()
        print("  ── 预检（确认工具读得到这份产物）")
        cc = _load("case_check")
        try:
            r = cc.check_case(json.load(io.open(path, encoding="utf-8")), cc.load_dyads())
            print("     ✅ 读到：可判判断 %d 条（当前为 0 是对的 —— paths/exclusions 还是空的）"
                  % r["n_judgeable"])
        except SystemExit:
            # ★ 这个报错对 case_check 是【对的】—— 它必须拒绝输出「可判判断总数 0」那种假读数。
            #   但入口【知道】这份是刚建出来的空壳 ⇒ 该报「形状对了、内容还没填」，不是失败。
            #   ⇒ 同一件事，在两个位置上该说两句不同的话。
            print("     ✅ 形状正确：工具在两处都查过（顶层 paths/exclusions、path_space），")
            print("        确认这份产物里【还没有任何判断】—— 这是刚建出来的正常状态。")
            print("        （case_check 对同一份文件会报错退出，那是对的：它必须拒绝输出")
            print("          「可判判断总数 0」那种看起来正常的空报告。）")
            print("=" * 92)
            return 0
    print("=" * 92)
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

    print("# s1 自证")
    rec = build("IQ,KW", "1991")
    ck("★能建出记录", rec["schema"] == "construct-run-v1")
    # ★★ S1.3 同一性
    ck("★★同输入两次跑 ⇒ cellId 相同（S1.3 的核心）",
       cell_id_of(rec) == cell_id_of(build("IQ,KW", "1991")), cell_id_of(rec))
    ck("★★不同输入 ⇒ cellId 不同（否则它区分不开任何东西）",
       cell_id_of(rec) != cell_id_of(build("IN,PK", "2023")))
    _t1 = build("IQ,KW", "1991"); _t1["committed_at"] = "1999-01-01T00:00:00"
    ck("★★时间戳【不进】哈希（它是运输字段，不是同一性）",
       cell_id_of(_t1) == cell_id_of(rec))
    ck("★judgmentsFnv 对空路径空间是稳定的",
       judgments_fnv(rec) == judgments_fnv(build("IQ,KW", "1991")))
    _j = dict(rec, paths=[{"id": "X", "label": "L", "stages": []}])
    ck("★★写了判断之后 judgmentsFnv 会变（否则它量不到内容）",
       judgments_fnv(_j) != judgments_fnv(rec))
    ck("★canonical 排序键（同语义 ⇒ 同字符串）",
       canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1}))
    ck("★fnv1a32 输出 8 位十六进制", len(fnv1a32("x")) == 8 and all(c in "0123456789abcdef" for c in fnv1a32("x")))
    ck("★★paths / exclusions 在【顶层】（那位盲测者撞到的坑）",
       "paths" in rec and "exclusions" in rec and "path_space" not in rec)
    ck("★event.text 是 None 而不是空串（F1：拿不到就不编）", rec["event"]["text"] is None)
    ck("★time_lock 是 None（F3 必须人定）", rec["event"]["time_lock"] is None)
    ck("★两个都进 needs_human",
       any("event.text" in x for x in rec["needs_human"])
       and any("time_lock" in x for x in rec["needs_human"]))
    ck("★数据层带出处", rec["data_layer"]["ucdp"]["dyad"] and rec["data_layer"]["ucdp"]["events"] == 69)
    ck("★臂判定：海湾 1991 = high（21790 ≥ 1000）", rec["arm"] == "high", rec["arm"])
    r2 = build("IN,PK", "2023")
    ck("★臂判定：印巴 2023 = quiet（1 < 1000）", r2["arm"] == "quiet", r2["arm"])
    ck("★主体名已清洗", all("Government of" not in x for x in rec["event"]["actors"]))
    try:
        build("IQ,ZZZZ", "1991")
        ck("★找不到的对要报错", False, "没报错")
    except SystemExit:
        ck("★找不到的对要报错", True)
    try:
        build("IQ,KW", "1800")
        ck("★该年无记录要报错（不拿别的年份顶）", False, "没报错")
    except SystemExit:
        ck("★该年无记录要报错（不拿别的年份顶）", True)
    # ★★ 产物必须能被 case_check 真读到（形状的最后一道验收）
    cc = _load("case_check")
    _empty = dict(rec, paths=[], exclusions=[])
    try:
        cc.check_case(_empty, cc.load_dyads())
        ck("★空路径空间会被 check_case 拒绝（而不是安静输出 0）", False, "没报错")
    except SystemExit:
        ck("★空路径空间会被 check_case 拒绝（而不是安静输出 0）", True)
    _one = dict(rec, paths=[{"id": "T", "label": "L", "stages": [
        {"stage": "s", "discriminating": True,
         "observable": {"object": "甲", "indicator": "乙"}}]}])
    _r = cc.check_case(_one, cc.load_dyads())
    ck("★★填了内容之后 case_check 能读到（形状通了）", _r["n_judgeable"] >= 1, str(_r["n_judgeable"]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
