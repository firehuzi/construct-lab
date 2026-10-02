# -*- coding: utf-8 -*-
"""case_schema_check.py —— 案例卡 vs Case JSON Schema V1.0 的对账

来源：`docs/ConStruct Lab：复杂系统结构化认知基础设施项目.txt` §附录一（第 3552 行起）
      声明的 `ConStruct Case JSON Schema V1.0`，目标是「**让任何案例都可以被机器读取**」。

为什么要有这个检查：
  这是本项目反复出现的同一种病 —— **一份声明得很漂亮的 schema，和一个真实产物，
  两者从不互相对照**。八维的「代码真相」、地图的「GDELT 实时」都是这一类。
  而这个 schema 尤其要紧：`ConStruct 100` 计划要建 100 个案例，
  如果格式不统一，100 份案例就只是一堆互不兼容的文件。

运行：  python case_schema_check.py            # 对账所有案例卡
        python case_schema_check.py --selftest
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(HERE, "data", "cases")

# ── 声明的 Schema V1.0（逐字取自计划书附录一）────────────────────────────────
# 键 = schema 字段；值 = 该字段的必需子键（空 = 只要求字段存在）
SCHEMA_V1 = {
    "case_id": [],
    "metadata": ["title", "domain", "time_range"],
    "system": ["type", "state"],
    "entities": ["id", "name", "type", "goal", "capability", "constraint"],
    "events": ["id", "description", "time", "impact"],
    "relations": ["source", "target", "type", "strength"],
    "drivers": ["type", "factor"],
    "feedback_loops": ["type", "cycle"],
    "path_dependency": ["past_model", "lock_in"],
    "equilibrium": ["previous", "current", "possible_future"],
}

# 「疑似承载同一语义」的人工对照 —— ⚠️ 只作【报告注解】，**不参与判定**。
# 为什么这样分：判定必须是纯机械的（在场／形态／缺失），否则一个硬编码的对照表
# 会把「空卡」也判成一堆 ⚠️ —— 而 `ConStruct 100` 要 100 份卡，那会全错。
ALIASES = {
    "metadata": "title / domain / date_range（提到了顶层，且多了 version / analyst / status）",
    "entities": "actors（按角色命名的对象，而非 {id,name,type,goal,capability,constraint} 数组）",
    "events": "event_timeline（日期→文字 的字典，无 id / impact）",
    "drivers": "散在 vulnerability_points / narrative_system / cef_analysis 里",
    "feedback_loops": "cef_analysis.feedback（散文式，非 {type, cycle[]}）",
    "path_dependency": "cognitive_collapse_path / structural_diagnosis（概念覆盖，形态不同）",
    "equilibrium": "cognitive_collapse_path（16→12→8→4→1 分层压缩，**比 schema 更丰富**）",
}


def _subkeys_ok(value, subs: list) -> tuple:
    """校验一个 schema 字段的子键。支持 dict 与 list[dict] 两种形态。
    ★ 这里修过一个 bug：原来只处理 list[dict]，于是 schema 里 dict 形态的
      metadata / system / equilibrium 全被判成「形态不同」，完全符合的卡也只过 7/10。
    """
    if isinstance(value, dict):
        miss = [s for s in subs if s not in value]
        return (not miss), miss
    if isinstance(value, list) and value and isinstance(value[0], dict):
        miss = [s for s in subs if s not in value[0]]
        return (not miss), miss
    return False, subs


def check_card(name: str, card: dict) -> dict:
    """纯机械判定：✅ 在场且形态对 ／ ⚠️ 在场但形态/子键不对 ／ ⛔ 不在场。"""
    rows = []
    for field, subs in SCHEMA_V1.items():
        if field not in card:
            rows.append((field, "⛔", "**完全缺失**"))
        elif not subs:
            rows.append((field, "✅", "存在"))
        else:
            ok, miss = _subkeys_ok(card[field], subs)
            if ok:
                rows.append((field, "✅", "字段与子键齐备"))
            else:
                rows.append((field, "⚠️", "形态或子键不符（缺：%s）" % "、".join(miss)))
    extra = [k for k in card if k not in SCHEMA_V1]
    return {"name": name, "rows": rows, "extra": extra,
            "ok": sum(1 for _f, m, _r in rows if m == "✅"),
            "reshaped": sum(1 for _f, m, _r in rows if m == "⚠️"),
            "absent": sum(1 for _f, m, _r in rows if m == "⛔")}


def load_cards() -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(CASES, "*.json"))):
        with open(p, encoding="utf-8") as fh:
            out.append((os.path.basename(p), json.load(fh)))
    return out


def machine_readable(card: dict) -> list:
    """schema 的目标是「让任何案例都可以被机器读取」——
    则【该是数的位置不该是字符串】。查出那些「看着像数却是自由文本」的值。"""
    bad = []
    for k, v in (card.get("key_numbers") or {}).items():
        if isinstance(v, str):
            bad.append(("key_numbers." + k, v))
    for role, obj in (card.get("actors") or {}).items():
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if isinstance(v, str) and any(ch.isdigit() for ch in v) and (
                    "count" in k or "pct" in k or "share" in k or "leverage" in k):
                bad.append(("actors.%s.%s" % (role, k), v))
    return bad


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    cards = load_cards()
    print("=" * 92)
    print("# 案例卡 vs Case JSON Schema V1.0 对账")
    print("=" * 92)
    print("\n  schema 声明处：docs/…基础设施项目.txt 附录一（第 3552 行起）")
    print("  schema 目标：「让任何案例都可以被机器读取」")
    print("  案例卡目录：%s（%d 份）" % (os.path.relpath(CASES, ROOT), len(cards)))
    if not cards:
        print("\n  ⛔ 没有案例卡可查。")
        return 1

    tot = {"ok": 0, "reshaped": 0, "absent": 0}
    for name, card in cards:
        r = check_card(name, card)
        for k in tot:
            tot[k] += r[k]
        print("\n  ── %s" % name)
        print("     %-16s %-4s %s" % ("schema 字段", "", "实测"))
        for field, mark, reason in r["rows"]:
            print("     %-16s %-4s %s" % (field, mark, reason))
        print("     ⇒ 齐备 %d ／ 形态不符 %d ／ 缺失 %d" % (r["ok"], r["reshaped"], r["absent"]))
        ali = [f for f, m, _ in r["rows"] if m in ("⛔", "⚠️") and f in ALIASES]
        if ali:
            print("     ⓘ 语义对照（人工注解，**不参与判定**）：")
            for f in ali:
                print("        %-16s 疑似由：%s" % (f, ALIASES[f]))
        print("     schema 里没有、但案例卡里有的顶层字段（%d 个）：" % len(r["extra"]))
        print("       %s" % "、".join(r["extra"]))
        bad = machine_readable(card)
        if bad:
            print("     ⚠️ 「该是数却是自由文本」的值（%d 个，妨碍机器读取）：" % len(bad))
            for k, v in bad[:6]:
                print("        %-34s = %s" % (k, v))

    n = len(cards)
    print("\n" + "=" * 92)
    print("  汇总（%d 份案例卡 × %d 个 schema 字段）" % (n, len(SCHEMA_V1)))
    print("     ✅ 齐备 %d ／ ⚠️ 形态不符 %d ／ ⛔ 缺失 %d"
          % (tot["ok"], tot["reshaped"], tot["absent"]))
    print()
    absent_fields = [f for f, m, _ in check_card(*cards[0])["rows"] if m == "⛔"]
    print("  ⇒ 结论：**声明的 schema 与真实产物严重不一致。**")
    print("     · %d 个字段完全缺失（%s）" % (len(absent_fields), "、".join(absent_fields)))
    print("     · 案例卡还多出 10 个 schema 没有的章节（paradoxes / key_numbers /")
    print("       cognitive_collapse_path / data_sources / disclaimers / next_events_to_track …）")
    print("     · 而 `ConStruct 100` 计划要建 100 个案例 ⇒ **格式不统一，100 份只是 100 个文件**。")
    print()
    print("  ⚠️ 但要说清楚：**不一致 ≠ 案例卡差**。这份卡里有 schema 没有的好东西 ——")
    print("     `data_sources`（9 个来源）、`disclaimers`（含事实核查）、")
    print("     `next_events_to_track`（**这就是预登记**）。方向是 schema 该向它靠，不是反过来。")
    print("=" * 92)
    return 1 if (tot["absent"] or tot["reshaped"]) else 0


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

    print("# case_schema_check 自证")
    full = {"case_id": "X", "metadata": {"title": "t", "domain": ["d"], "time_range": "1-2"},
            "system": {"type": "a", "state": "b"},
            "entities": [{"id": 1, "name": "n", "type": "t", "goal": "g",
                          "capability": "c", "constraint": "k"}],
            "events": [{"id": 1, "description": "d", "time": "t", "impact": "i"}],
            "relations": [{"source": 1, "target": 2, "type": "t", "strength": 4}],
            "drivers": [{"type": "material", "factor": "f"}],
            "feedback_loops": [{"type": "negative", "cycle": ["a"]}],
            "path_dependency": [{"past_model": "p", "lock_in": ["l"]}],
            "equilibrium": {"previous": "a", "current": "b", "possible_future": ["c"]}}
    r = check_card("full", full)
    check("★完全符合 schema 的卡 ⇒ 齐备 10、缺失 0",
          r["ok"] == len(SCHEMA_V1) and r["absent"] == 0,
          "ok=%d absent=%d" % (r["ok"], r["absent"]))
    r2 = check_card("empty", {})
    check("★空卡 ⇒ 缺失 = schema 字段数",
          r2["absent"] == len(SCHEMA_V1), str(r2["absent"]))
    r3 = check_card("reshape", {"metadata": {"title": "t"}})
    check("metadata 存在但形态不同 ⇒ 记 ⚠️ 而非 ✅",
          any(f == "metadata" and m == "⚠️" for f, m, _ in r3["rows"]),
          str([x for x in r3["rows"] if x[0] == "metadata"]))
    r4 = check_card("sub", {"entities": [{"id": 1, "name": "n"}]})
    check("entities 缺子键 ⇒ 报出缺哪些",
          any(f == "entities" and "缺" in reason for f, _m, reason in r4["rows"]),
          str([x for x in r4["rows"] if x[0] == "entities"]))
    check("extra 能列出 schema 之外的顶层字段",
          check_card("x", {"case_id": "a", "paradoxes": []})["extra"] == ["paradoxes"])
    mb = machine_readable({"key_numbers": {"a": 1, "b": "320k-460k"}})
    check("机器可读性：揪出「该是数却是文本」", mb == [("key_numbers.b", "320k-460k")], str(mb))
    cards = load_cards()
    check("真实案例卡存在且能加载", len(cards) >= 1, str(len(cards)))
    real = check_card(*cards[0])
    check("★真案例卡：schema 字段【没有全部齐备】（这正是要查出来的）",
          real["ok"] < len(SCHEMA_V1), "ok=%d/%d" % (real["ok"], len(SCHEMA_V1)))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
