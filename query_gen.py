# -*- coding: utf-8 -*-
"""query_gen.py —— 查询生成器：把「核不了的一条判断」变成【当时可问的问题】

★★ 为什么生成器比搜索引擎更该做
   用户问：在功能里加一个数据搜索引擎能不能满足需求？
   拆开看：搜索引擎能【找到线索】，不能【交付可存档的依据】、
   不能【判定】、不能【复现】（结果随人/随会话/随时间变）。
   而接进工具还要多付三样代价：网络依赖、后端、写盘存档 ——
   恰好都是现在【单文件 + file:// + 离线】这套架构刻意避免的。

   ⇒ 而真正难的一步根本不是搜索，是【写出时间锁定正确的查询词】。

★★ 要防的错：知道答案，就会搜到「像确认」的东西
   本项目实测过一次严重的选择偏倚（八维的 ρ 从 +0.507 掉到 +0.263）。
   检索上的同型错误是：
     ❌ 「以色列 1991 是否还击」     ← 这是【知道答案之后】的问题
     ✅ 「以色列 1991年1月 内阁 会议」← 这是【当时的人】会问的问题
   你知道结局，就会不自觉地搜那个结局的措辞 ⇒ 搜到一堆提到它的页面 ⇒ 误当成确认。

★★ 所以本生成器有三条硬规矩
   ① **不许含结果词** —— 还击/报复/成功/失败/拒绝/倒台/瓦解/退出/未/没有…
      生成的每条查询都会被机器扫一遍，含结果词就标出来。**这是可自证的。**
   ② **时间从 `window.from` 取，不从 `to` 取** —— 问的是「当时在发生什么」，
      不是「最后怎么样了」。而从 to 取会把结果期的时间词带进来。
   ③ **生成【多个入口】而不是一条「正确的」查询** —— 因为一条查询定死，
      等于替人做了判断。四个入口刻意互相拆台：
        时间锚 / 决策过程 / 外部约束 / 同期报道

★★ 它产出的是【线索入口】，不是【依据】
   ⇒ 输出里那三个字段必须留空由人填：
     archived_snapshot（存的是原文不是链接）、verified_open（打不开的不算依据）、
     witness_type（当时的／事后的 —— **事后的不能用于时间锁定**）。
     缺一个，这一步就退化成「形式上有核验、实际没人看」。

运行：  python query_gen.py <案例.json>          # 打印查询 + 出可填模板
        python query_gen.py <案例.json> --write  # 写出模板 JSON
        python query_gen.py --selftest
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ★ 结果词：查询里出现这些，就说明你在按【已知答案】搜
RESULT_WORDS = [
    # 行为类
    "还击", "报复", "反击", "入侵", "占领", "推翻", "撤军", "退出", "瓦解", "倒台",
    "参战", "介入", "干预", "制裁", "解除", "松动", "停火", "收手",
    # 判断类
    "成功", "失败", "胜利", "拒绝", "放弃", "克制", "避免", "未能", "没有", "未",
    # 英文
    "retaliat", "invad", "occup", "overthr", "withdraw", "collaps", "succeed",
    "fail", "reject", "abandon",
]

# 中性词：不预设结果，只指向【过程】
NEUTRAL = {
    "决策过程": ["会议", "声明", "决定", "讨论"],
    "外部约束": ["美国", "联合国"],
    "同期报道": ["报道"],
}


def time_words(window: dict, time_lock: str) -> list:
    """从窗口起点与时间锁定里取【当时】的时间词。

    ★ 从 `window.from` 取而不是 `to` —— 问的是当时在发生什么，不是最后怎么样了。
      从 to 取会把结果期的时间词带进来（例如问 1991 年的事却带上了 1993）。
    """
    out = []
    frm = (window or {}).get("from") or ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", frm) or re.match(r"(\d{4})-(\d{2})", frm)
    if m:
        y, mo = m.group(1), m.group(2)
        out.append("%s年%s月" % (y, int(mo)))
        out.append("%s年" % y)
    elif re.match(r"^\d{4}$", frm):
        out.append("%s年" % frm)
    if not out and time_lock:                      # 退回时间锁定里抠
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", time_lock)
        if m:
            out.append("%s年%s月" % (m.group(1), int(m.group(2))))
        else:
            m = re.search(r"(\d{4})\s*年", time_lock)
            if m:
                out.append("%s年" % m.group(1))
    return out


def find_result_words(text: str) -> list:
    """扫出文本里的结果词。★ 这是可机器查的，所以它是一条真规矩。"""
    low = (text or "").lower()
    return sorted({w for w in RESULT_WORDS if w.lower() in low})


def or_join(words: list) -> str:
    """中性词之间必须用 OR 连接。

    ★ 第一版写成空格分隔：`伊拉克政府 1991年1月 会议 声明 决定 讨论`。
      而搜索引擎里**空格 = AND** ⇒ 这条查询要求同时含四个词 ⇒ **什么都搜不到**。
      这个缺陷自证抓不到（生成器没错，是查询语法错），**只有看真输出才发现**。
      ⇒ 用 OR，并且加括号限定作用范围。
    """
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    return "(" + " OR ".join(words) + ")"


def gen_queries(judgment: dict, time_lock: str) -> dict:
    """为一条核不了的判断生成【多个入口】的查询。

    ★ 刻意不用 indicator 直译成查询词 —— indicator 就是结论
      （「对伊拉克本土实施军事报复」），拿它去搜等于按答案搜。
      查询面只用【主体】＋【当时的时间】，再加中性词。
    """
    obs = judgment.get("observable") or {}
    obj = (obs.get("object") or "").strip()
    ind = (obs.get("indicator") or "").strip()
    tws = time_words(judgment.get("window"), time_lock)
    primary = tws[0] if tws else ""
    year = tws[1] if len(tws) > 1 else ""

    queries = []
    if obj and primary:
        queries.append(("时间锚", "%s %s" % (obj, primary),
                        "只锚主体与时间，不带任何结果词 —— 让当时的材料自己浮出来"))
    if obj and primary:
        queries.append(("决策过程", "%s %s %s" % (obj, primary, or_join(NEUTRAL["决策过程"])),
                        "问「当时在决定什么」，不问「最后决定了什么」"))
    if obj and primary:
        queries.append(("外部约束", "%s %s %s" % (obj, primary, or_join(NEUTRAL["外部约束"])),
                        "故意引入第三方 —— 约束条件往往在别人的报道里"))
    if obj and (primary or year):
        queries.append(("同期报道", "%s %s %s" % (obj, primary or year, or_join(NEUTRAL["同期报道"])),
                        "按【报道日期】筛，不按相关性排 —— 事后的叙述不能用于时间锁定"))

    out = []
    for angle, q, why in queries:
        q = re.sub(r"\s+", " ", q).strip()
        hits = find_result_words(q)
        out.append({"angle": angle, "query": q, "why": why,
                    "result_words_found": hits,
                    "clean": not hits})
    return {"judgment_id": judgment.get("id") or judgment.get("judgment_id"),
            "claim": ind or judgment.get("content"),
            "object": obj,
            "time_anchor": primary,
            "queries": out,
            "indicator_note": "★ indicator「%s」【没有】被译成查询词 —— 它就是结论，拿它搜等于按答案搜。" % ind
                              if ind else "",
            "fill_in": {
                "archived_snapshot": None,
                "verified_open": None,
                "witness_type": None,
                "_options": {"witness_type": ["contemporary", "retrospective", "unknown"]},
                "_rules": [
                    "archived_snapshot 存的是【原文快照】不是链接 —— 链接会烂（本轮已实测：搜到的 Baltimore Sun 那条域名解析到非公网 IP，打开是空的）",
                    "verified_open=false ⇒ 这条依据【不存在】，不许拿它判定",
                    "witness_type=retrospective ⇒ **不能用于时间锁定**（它掺了后见之明）",
                ],
            }}


def collect(case: dict) -> list:
    """从案例里挑出【核不了的】判断（没有 source 的）。"""
    time_lock = (case.get("event") or {}).get("time_lock") or ""
    out = []
    for x in case.get("exclusions", []):
        if not ((x.get("observable") or {}).get("source")):
            out.append({"id": x.get("id"), "kind": "排除", "observable": x.get("observable"),
                        "window": x.get("window"), "content": x.get("content")})
    for p in case.get("paths", []):
        for i, st in enumerate([s for s in p.get("stages", []) if s.get("discriminating")], 1):
            if not ((st.get("observable") or {}).get("source")):
                out.append({"id": "%s/%s#%d" % (p.get("id"), st.get("stage"), i),
                            "kind": "路径", "observable": st.get("observable"),
                            "window": st.get("window"), "content": st.get("stage")})
    return [gen_queries(j, time_lock) for j in out]


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if a.endswith(".json")]
    if not args:
        print("用法：python query_gen.py <案例.json> [--write]")
        return 1
    with io.open(args[0], encoding="utf-8") as fh:
        case = json.load(fh)
    items = collect(case)

    print("=" * 100)
    print("# 查询生成器 · %s" % os.path.basename(args[0]))
    print("=" * 100)
    print("  核不了的判断：%d 条 ⇒ 每条生成多个【入口】，不是一条「正确的」查询" % len(items))
    print("  硬规矩：查询不许含结果词；时间只从 window.from 取（问当时，不问结果）\n")

    bad = 0
    for it in items:
        print("  ── %s" % it["judgment_id"])
        print("     判断：%s" % it["claim"])
        if it["indicator_note"]:
            print("     %s" % it["indicator_note"])
        for q in it["queries"]:
            flag = "⚠️ 含结果词 %s" % "、".join(q["result_words_found"]) if not q["clean"] else "✅"
            print("     [%s] %s" % (q["angle"], flag))
            print("         %s" % q["query"])
            bad += 0 if q["clean"] else 1
        print()
    print("  ── 读数")
    n_q = sum(len(it["queries"]) for it in items)
    print("     生成查询 %d 条，其中含结果词的 %d 条" % (n_q, bad))
    print("     （含结果词 ⇒ 你在按【已知答案】搜 ⇒ 会搜到「像确认」的东西）")
    print("\n  ── ★ 这一步产出的不是依据，是线索入口")
    print("     每条要人填三个字段，缺一个就退化成「形式上有核验、实际没人看」：")
    print("       archived_snapshot  存【原文快照】不是链接")
    print("       verified_open      打不开的 ⇒ 这条依据【不存在】")
    print("       witness_type       当时的／事后的 —— 事后的【不能】用于时间锁定")
    print("=" * 100)

    if "--write" in sys.argv:
        out = os.path.join(HERE, "data", "cases", "queries")
        os.makedirs(out, exist_ok=True)
        name = os.path.splitext(os.path.basename(args[0]))[0] + ".queries.json"
        with io.open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"schema": "construct-queries-v1", "case": os.path.basename(args[0]),
                       "items": items}, fh, ensure_ascii=False, indent=2)
        print("  已写出 %s" % os.path.relpath(os.path.join(out, name), HERE))
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

    print("# query_gen 自证")

    ck("★结果词识别：还击/报复/撤军",
       set(find_result_words("以色列还击并报复")) >= {"还击", "报复"}, str(find_result_words("以色列还击并报复")))
    ck("★结果词识别：英文",
       "retaliat" in find_result_words("Israel retaliates"), str(find_result_words("Israel retaliates")))
    ck("★中性词不被误判", find_result_words("以色列 1991年1月 内阁 会议") == [],
       str(find_result_words("以色列 1991年1月 内阁 会议")))

    # ★★ 时间从 from 取，不从 to 取
    tws = time_words({"from": "1991-01-17", "to": "1991-03-31"}, "")
    ck("★★时间词取自 window.from（1991年1月），**不带** to 的 3 月",
       tws[0] == "1991年1月", str(tws))
    ck("★窗口缺失时退回时间锁定里抠",
       time_words({}, "1991年1月15日——决议最后期限已过")[0] == "1991年1月",
       str(time_words({}, "1991年1月15日——决议最后期限已过")))
    ck("★抠不到就返回空（不编时间）", time_words({}, "很久以前") == [],
       str(time_words({}, "很久以前")))

    # ★★ indicator 不许被译成查询词
    j = {"id": "T1", "observable": {"object": "以色列", "indicator": "对伊拉克本土实施军事报复"},
         "window": {"from": "1991-01-17", "to": "1991-03-31"}}
    r = gen_queries(j, "1991年1月15日——决议最后期限已过。")
    ck("★★indicator 没被译成查询词",
       all("报复" not in q["query"] for q in r["queries"]),
       str([q["query"] for q in r["queries"]]))
    ck("★★indicator 没译进查询，但被明确说明（防止人以为是漏了）",
       "没有】被译成查询词" in r["indicator_note"], r["indicator_note"][:60])
    ck("★生成了多个入口（≥4）", len(r["queries"]) >= 4, str(len(r["queries"])))
    # ★★ 中性词必须 OR 连接 —— 空格是 AND，四个词全要 ⇒ 搜不到任何东西
    ck("★★中性词用 OR 连接（空格=AND ⇒ 会搜不到）",
       any(" OR " in q["query"] for q in r["queries"]),
       str([q["query"] for q in r["queries"]]))
    ck("★★一条查询里【不出现】两个相邻的裸中性词（那等于 AND 它们）",
       all(not re.search(r"会议 声明|声明 决定|决定 讨论", q["query"]) for q in r["queries"]),
       str([q["query"] for q in r["queries"]]))
    ck("★or_join 单词不加括号", or_join(["报道"]) == "报道")
    ck("★or_join 多词加括号", or_join(["会议", "声明"]) == "(会议 OR 声明)", or_join(["会议", "声明"]))
    ck("★or_join 空表返回空", or_join([]) == "")
    ck("★★所有生成的查询都【干净】（不含结果词）",
       all(q["clean"] for q in r["queries"]),
       str([(q["query"], q["result_words_found"]) for q in r["queries"]]))
    ck("★四个入口的角度齐全",
       {q["angle"] for q in r["queries"]} == {"时间锚", "决策过程", "外部约束", "同期报道"},
       str([q["angle"] for q in r["queries"]]))
    ck("★查询里含主体与时间锚",
       all("以色列" in q["query"] and "1991年1月" in q["query"] for q in r["queries"]),
       str([q["query"] for q in r["queries"]]))

    # ★ 反向：含结果词的查询必须被标出来
    j2 = {"id": "T2", "observable": {"object": "以色列撤军", "indicator": "撤军"},
          "window": {"from": "1991-01-17"}}
    r2 = gen_queries(j2, "")
    ck("★★object 自己含结果词时，查询被标出来（不静默放过）",
       any(not q["clean"] for q in r2["queries"]),
       str([(q["query"], q["result_words_found"]) for q in r2["queries"]]))

    # ★ 三个必填字段必须留空
    ck("★★三个字段留空由人填（archived_snapshot / verified_open / witness_type）",
       all(r["fill_in"].get(k) is None
           for k in ("archived_snapshot", "verified_open", "witness_type")))
    ck("★写明「事后的不能用于时间锁定」",
       any("不能用于时间锁定" in x for x in r["fill_in"]["_rules"]),
       str(r["fill_in"]["_rules"]))
    ck("★witness_type 有可选项", r["fill_in"]["_options"]["witness_type"] ==
       ["contemporary", "retrospective", "unknown"])

    # 真案例
    fp = os.path.join(HERE, "data", "cases", "filled", "IQ-KW-1991.json")
    if os.path.exists(fp):
        with io.open(fp, encoding="utf-8") as fh:
            case = json.load(fh)
        items = collect(case)
        ck("★★真案例：7 条核不了的都生成了查询", len(items) == 7, str(len(items)))
        ck("★★真案例：没有任何一条查询含结果词",
           all(q["clean"] for it in items for q in it["queries"]),
           str([(q["query"], q["result_words_found"]) for it in items for q in it["queries"]
                if not q["clean"]]))
        ck("★真案例：每条都有时间锚",
           all(it["time_anchor"] for it in items),
           str([(it["judgment_id"], it["time_anchor"]) for it in items]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
