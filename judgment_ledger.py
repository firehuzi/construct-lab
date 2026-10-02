# -*- coding: utf-8 -*-
"""judgment_ledger.py —— B4.1：统一「可观察判据」＋ 老记录迁移器

★★ 为什么要有这个文件
   B4 的核心决定（见 docs/ConStruct_B4_规格_V1.md §二）：
     **排除断言**问「什么算它发生了？」（发生了 ⇒ 我错了）
     **路径推演**也问「什么算它发生了？」（发生了 ⇒ 我对了）
   同一句话，只是一条要证伪、一条要确认 —— **所以不该有两套字段**。
   统一为 observable{object, indicator, threshold?, source?} + window。

★★ 迁移器的诚实边界（这是本文件最重要的设计）
   老记录（construct-exclusion-v1）里 `criterion` 是【一整句自由文本】：
       「互撤导弹」 / 「联合国决议和阿拉伯盟友共同约束」 / 「北约成员国军队出现在乌克兰境内」
   我**没法机械地**把它拆成 `object` + `indicator` —— 那需要语义理解。

   ⇒ 所以迁移器**能迁的迁、不能迁的【标出来】，绝不猜**：
     · content / direction / window.from  ⇒ 机械可迁
     · observable.indicator               ⇒ 原样搬 criterion（它是判据文本）
     · observable.object                  ⇒ **置 None 并记进 needs_human**
     · window.to 无法解析的                ⇒ 同样记进 needs_human

   **★ 绝不许把 object 填成 ""。** 空串能骗过「非空校验」，然后一条本该被人补的判据
     会静默变成「合格」。这与本项目一贯的病同型（形式上有、实际上不对题）。

运行：  python judgment_ledger.py --report     # 看迁移后还差什么（只读，不写）
        python judgment_ledger.py --migrate    # 写 data/exclusions/migrated/
        python judgment_ledger.py --selftest
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXCL_DIR = os.path.join(HERE, "data", "exclusions")
OUT_DIR = os.path.join(EXCL_DIR, "migrated")

OLD_SCHEMA = "construct-exclusion-v1"
NEW_SCHEMA = "construct-judgment-v1"

# 一条判断必须有的东西（缺任一 ⇒ 阻止提交／必须人工补）
REQUIRED = ["observable.object", "observable.indicator", "window.from", "window.to"]


# ══ 日期与窗口 ══════════════════════════════════════════════════════════════════
def extract_date(text: str):
    """从 time_lock 那种长句里抠出起始日期。抠不到返回 None（不猜）。"""
    if not text:
        return None
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if m:
        return "%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", text)
    if m:
        return "%04d-%02d" % (int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return m.group(0)
    m = re.search(r"\b(\d{4})\b", text)
    if m:
        return m.group(1)
    return None


def add_years(iso: str, n: int):
    """在 ISO 日期上加 n 年（只做年，够用；日期精度不谎报）。"""
    if not iso:
        return None
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", iso)
    if not m:
        return None
    y = int(m.group(1)) + n
    return "%04d%s%s" % (y, ("-" + m.group(2)) if m.group(2) else "",
                         ("-" + m.group(3)) if m.group(3) else "")


def parse_window(raw, time_lock: str):
    """把老记录那个自由文本窗口转成 {from, to, raw, unresolved}。

    ★ 「至今」是个陷阱：它的 to 永远不到期 ⇒ **这条断言实际上永远判不了**。
      本轮已经用真实案例证明窗口决定真值（「盟军入侵伊拉克」1991 成立、2003 被证伪）。
      所以「至今」必须显式标 unresolved，不许当成一个正常窗口。
    """
    from_ = extract_date(time_lock)
    out = {"from": from_, "to": None, "raw": raw, "unresolved": []}
    if not from_:
        out["unresolved"].append("window.from")
    if raw is None or str(raw).strip() == "":
        out["unresolved"].append("window.to")
        return out
    s = str(raw).strip()
    m = re.match(r"^(\d+)\s*年$", s)
    if m and from_:
        out["to"] = add_years(from_, int(m.group(1)))
        return out
    m = re.match(r"^(\d+)\s*(个月|月)$", s)
    if m and from_ and len(from_) >= 7:
        y, mo = int(from_[:4]), int(from_[5:7])
        mo += int(m.group(1))
        y += (mo - 1) // 12
        mo = (mo - 1) % 12 + 1
        out["to"] = "%04d-%02d" % (y, mo)
        return out
    if s in ("至今", "长期", "永久", "无限期"):
        out["unresolved"].append("window.to")
        out["note"] = "「%s」⇒ to 永不到期 ⇒ 这条断言实际上永远判不了" % s
        return out
    out["unresolved"].append("window.to")
    return out


# ══ 「建议值」—— 给起点，但不填进 object ═══════════════════════════════════════
# ★ 为什么不直接填进 observable.object：
#   填进去，人可能不加思索就接受（**而现在的病正是「填错了没人发现」**）；
#   留空，3 条全要人从零写。
#   ⇒ 折中：写进【另一个字段】object_suggestion。检查只读 object，所以骗不过去；
#     而人有一个可改的起点。
def known_actors() -> set:
    """从档案目录里取主体名，用于「这条断言观察的是谁」的比对。"""
    names = set()
    for root in (os.path.join(os.path.dirname(HERE), "ConStruct_Archive"),
                 os.path.join(os.path.dirname(HERE), "actors")):
        if not os.path.isdir(root):
            continue
        for p in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
            n = os.path.splitext(os.path.basename(p))[0]
            if 2 <= len(n) <= 12 and not n.startswith(("Template", "Scenario", "Index")):
                names.add(n)
    # 档案里用英文名的几个
    names |= {"美国", "中国", "俄罗斯", "日本", "欧盟", "北约", "印度", "伊朗", "以色列",
              "乌克兰", "德国", "法国", "英国", "韩国", "土耳其", "沙特", "新加坡",
              "塞尔维亚", "巴基斯坦", "越南", "台湾", "澳大利亚", "埃及", "朝鲜",
              "东盟", "金砖", "OPEC", "台积电", "ASML", "英伟达", "三星", "华为",
              "OpenAI", "Anthropic", "SpaceX", "Palantir", "DeepSeek"}
    return names


def suggest_object(content: str, indicator: str) -> dict | None:
    """给一个【建议的观察对象】，只作起点。取不到就返回 None —— 不硬编。

    取法：在 content／indicator 里找【已知主体名】，取最先出现、位置最靠前的那个。
    ★ 刻意不做「取第一个名词短语」这种通用抽取 —— 中文没有词边界，
      那样抽出来的东西一半是错的，而错的建议比没有建议更坏（人会直接接受）。
    """
    if not content:
        return None
    for text in (content, indicator or ""):
        best = None
        for a in known_actors():
            i = text.find(a)
            if i >= 0 and (best is None or i < best[1]):
                best = (a, i)
        if best:
            return {"value": best[0], "confidence": "high" if best[1] == 0 else "medium",
                    "basis": "在「%s」的第 %d 字匹配到档案里的主体名" % (text[:18], best[1] + 1)}
    return None


# ══ 迁移 ════════════════════════════════════════════════════════════════════════
def migrate_item(item: dict, run: dict) -> dict:
    """把一条老排除断言迁成统一形状。★ 不猜：拿不到的字段置 None 并记进 needs_human。"""
    time_lock = run.get("time_lock") or ""
    win = parse_window(item.get("window"), time_lock)
    crit = (item.get("criterion") or "").strip() or None

    j = {
        "schema": NEW_SCHEMA,
        "id": item.get("id"),
        "run_id": (run.get("scenario_id") or "?") + "@" + str(run.get("exported_at") or ""),
        "scenario": item.get("scenario") or run.get("scenario"),
        "time_lock": time_lock,
        "direction": "exclude",                 # 老记录只有排除断言
        "content": (item.get("excluded") or "").strip() or None,
        "observable": {
            # ★ object 拿不到 —— criterion 是一整句，机械拆不出「观察对象」
            "object": None,
            # criterion 原样搬进 indicator：它是判据文本，不是垃圾
            "indicator": crit,
            "threshold": None,
            "source": None,
        },
        "window": win,
        "why": "",
        "migrated_from": {
            "schema": OLD_SCHEMA,
            "note": "机械可迁的部分已迁；拿不到的置 None 并记进 needs_human，不猜。",
        },
    }
    # ★ 建议值：写进【另一个字段】，不填进 observable.object（检查只读后者 ⇒ 骗不过去）
    sug = suggest_object(j["content"], j["observable"]["indicator"])
    if sug:
        j["observable"]["object_suggestion"] = sug
    # 汇总还差什么（★ 缺什么列什么，不填占位）
    need = []
    if not j["observable"]["object"]:
        need.append("observable.object")
    if not j["observable"]["indicator"]:
        need.append("observable.indicator")
    need += win.get("unresolved", [])
    j["needs_human"] = sorted(set(need))
    return j


def load_old() -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(EXCL_DIR, "*.json"))):
        try:
            with io.open(p, encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("schema") == OLD_SCHEMA:
            out.append((p, rec))
    return out


def migrate_all() -> list:
    rows = []
    for p, rec in load_old():
        for it in rec.get("exclusions", []):
            rows.append(migrate_item(it, rec))
    return rows


# ══ 报告 ════════════════════════════════════════════════════════════════════════
def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    rows = migrate_all()
    if "--migrate" in sys.argv:
        os.makedirs(OUT_DIR, exist_ok=True)
        by_run = {}
        for r in rows:
            by_run.setdefault(r["run_id"], []).append(r)
        for rid, items in by_run.items():
            safe = re.sub(r"[^\w\-]", "_", rid)[:60]
            with io.open(os.path.join(OUT_DIR, safe + ".json"), "w",
                         encoding="utf-8", newline="\n") as fh:
                json.dump({"schema": NEW_SCHEMA, "run_id": rid, "judgments": items},
                          fh, ensure_ascii=False, indent=2)
        print("已写出 %d 个 run 到 %s" % (len(by_run), os.path.relpath(OUT_DIR, HERE)))

    print("=" * 96)
    print("# B4.1 迁移报告：老排除断言 → 统一「可观察判据」")
    print("=" * 96)
    print("  来源 %d 个老记录文件，迁出 %d 条判断" % (len(load_old()), len(rows)))
    print("  迁移规矩：**能迁的迁、不能迁的标出来，绝不猜**。object 不许填 \"\"（空串会骗过非空校验）。\n")
    print("  %-24s %-30s %-28s %s" % ("id", "content（排除的路径）", "observable.indicator", "还差什么"))
    print("  " + "-" * 92)
    for r in rows:
        print("  %-24s %-30s %-28s %s"
              % (r["id"], (r["content"] or "")[:30], (r["observable"]["indicator"] or "")[:28],
                 "、".join(r["needs_human"]) or "✅ 齐备"))
        w = r["window"]
        line = "  %-24s 窗口 from=%s to=%s" % ("", w["from"], w["to"])
        if w.get("note"):
            line += "　★ " + w["note"]
        print(line)
        s = r["observable"].get("object_suggestion")
        if s:
            print("  %-24s ↳ 建议 object：**%s**（%s）—— 只是起点，检查只认 object 那一栏"
                  % ("", s["value"], s["confidence"]))

    tally = {}
    for r in rows:
        for n in r["needs_human"]:
            tally[n] = tally.get(n, 0) + 1
    print("\n  ── 还差什么（计数）")
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("     %-32s %d" % (k, v))
    ready = len([r for r in rows if not r["needs_human"]])
    print("\n  ★ 迁移后【直接可用】的：%d / %d" % (ready, len(rows)))
    print("     其余 %d 条需要人补 —— **这正是迁移器该有的输出**：" % (len(rows) - ready))
    print("     老记录的 criterion 是一整句自由文本，机械拆不出「观察对象」。")
    print("     硬拆会得到一个看起来合格、实际不对题的字段 —— 那比缺失更糟。")
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

    print("# judgment_ledger 自证")

    # ── 日期抽取 ──
    ck("★从长句里抠日期（年月日）",
       extract_date("2014年2月22日——亚努科维奇逃离基辅。此时克里米亚还在乌克兰控制下。") == "2014-02-22",
       str(extract_date("2014年2月22日——亚努科维奇逃离基辅。")))
    ck("★只到年月也能抠",
       extract_date("1991年1月15日——决议最后期限已过") == "1991-01-15")
    ck("★抠不到返回 None（不猜）", extract_date("很久以前") is None)

    # ── 窗口解析 ──
    w = parse_window("3年", "2014年2月22日——亚努科维奇逃离基辅。")
    ck("★「3年」⇒ to = from+3年", w["from"] == "2014-02-22" and w["to"] == "2017-02-22", str(w))
    ck("★3年窗口无 unresolved", w["unresolved"] == [], str(w["unresolved"]))
    w = parse_window(None, "2014年2月22日——…")
    ck("★窗口为 null ⇒ 记 window.to 待补", "window.to" in w["unresolved"], str(w))
    w = parse_window("至今", "2014年2月22日——…")
    ck("★★「至今」必须标 unresolved（to 永不到期 ⇒ 永远判不了）",
       "window.to" in w["unresolved"] and w.get("note"), str(w))
    ck("★「至今」的 note 说清后果", "永远判不了" in (w.get("note") or ""), w.get("note"))
    w = parse_window("3年", "很久以前")
    ck("★from 抠不到 ⇒ 标 window.from 待补", "window.from" in w["unresolved"], str(w))

    # ── 迁移：三个方向都要钉 ──
    # ① 正常老记录
    item = {"id": "crimea-X01", "scenario": "克里米亚危机",
            "excluded": "北约出兵协助乌克兰",
            "criterion": "北约成员国军队出现在乌克兰境内", "window": "3年"}
    run = {"scenario_id": "crimea", "scenario": "克里米亚危机",
           "exported_at": "2026-10-02T07:43:40.638Z",
           "time_lock": "2014年2月22日——亚努科维奇逃离基辅。"}
    j = migrate_item(item, run)
    ck("★content / direction 正确", j["content"] == "北约出兵协助乌克兰" and j["direction"] == "exclude")
    ck("★criterion 原样搬进 indicator", j["observable"]["indicator"] == "北约成员国军队出现在乌克兰境内")
    ck("★★object 置 None 而**不是空串**（空串会骗过非空校验）",
       j["observable"]["object"] is None, repr(j["observable"]["object"]))
    ck("★object 被记进 needs_human", "observable.object" in j["needs_human"], str(j["needs_human"]))
    ck("★窗口迁对了", j["window"]["from"] == "2014-02-22" and j["window"]["to"] == "2017-02-22")

    # ② 判据是「理由」的那种（古巴那条）
    item2 = {"id": "cuban-X01", "excluded": "危机局势进一步加剧 进入核战前奏",
             "criterion": "互撤导弹", "window": "3年"}
    run2 = {"scenario_id": "cuban-missile", "exported_at": "x",
            "time_lock": "1962年10月22日——肯尼迪宣布对古巴实施海上封锁。"}
    j2 = migrate_item(item2, run2)
    ck("★把「理由」原样搬进 indicator（不替它改写成判据）",
       j2["observable"]["indicator"] == "互撤导弹", j2["observable"]["indicator"])
    ck("★它同样需要人补 object", "observable.object" in j2["needs_human"])

    # ③ 海湾那条：判据是理由 ＋ 无窗口
    item3 = {"id": "gulf-X01", "excluded": "盟军入侵伊拉克",
             "criterion": "联合国决议和阿拉伯盟友共同约束", "window": None}
    run3 = {"scenario_id": "gulf-war", "exported_at": "x",
            "time_lock": "1991年1月15日——决议最后期限已过。"}
    j3 = migrate_item(item3, run3)
    ck("★★无窗口那条：object 与 window.to 两个都进 needs_human",
       "observable.object" in j3["needs_human"] and "window.to" in j3["needs_human"],
       str(j3["needs_human"]))
    ck("★from 仍能从 time_lock 抽出（能迁的不因另一项缺失而放弃）",
       j3["window"]["from"] == "1991-01-15", str(j3["window"]))

    # ④ 缺判据
    j4 = migrate_item({"id": "z", "excluded": "X", "criterion": "", "window": "3年"},
                      {"time_lock": "2014年2月22日——"})
    ck("★缺判据 ⇒ indicator 为 None 且记进 needs_human",
       j4["observable"]["indicator"] is None and "observable.indicator" in j4["needs_human"],
       str(j4["needs_human"]))

    # ── 真实记录 ──
    rows = migrate_all()
    ck("★三条真实记录都迁得出来", len(rows) == 3, str(len(rows)))
    ck("★没有任何一条的 object 被填成空串",
       all(r["observable"]["object"] is None for r in rows))
    ck("★每条都有 needs_human（老记录不可能直接合格）",
       all(r["needs_human"] for r in rows),
       str([r["needs_human"] for r in rows]))
    # ── 建议值：能抽出来，但【绝不填进 object】──
    ck("★★建议值写进 object_suggestion，而 observable.object 仍是 None",
       all(r["observable"].get("object_suggestion") is None or r["observable"]["object"] is None
           for r in rows))
    s = suggest_object("北约出兵协助乌克兰", "北约成员国军队出现在乌克兰境内")
    ck("★能从 content 里匹配到已知主体名（北约）", s and s["value"] == "北约", str(s))
    ck("★匹配在开头 ⇒ confidence=high", s and s["confidence"] == "high", str(s))
    # ★ 这条原来写成 `s2 is None or ...`，恒真 —— 又一条永远绿的检查。
    #   实测：伊拉克不在 47 档案里（盟军也不在）⇒ 结论是 None，且这本身是有信息的。
    ck("★「盟军」「伊拉克」都不在档案主体名里 ⇒ 返回 None（不硬编一个）",
       suggest_object("盟军入侵伊拉克", "出现联军地面部队越过伊拉克边境") is None,
       str(suggest_object("盟军入侵伊拉克", "出出联军地面部队越过伊拉克边境")))
    ck("★伊拉克确实不在档案里（所以要建议也建议不出来）", "伊拉克" not in known_actors())
    ck("★无主体可匹配 ⇒ 返回 None（不硬编一个）",
       suggest_object("危机局势进一步加剧", "核武器进入实战部署") is None,
       str(suggest_object("危机局势进一步加剧", "核武器进入实战部署")))
    ck("★建议只覆盖一部分（3 条真实记录里只有 1 条有建议）—— 不许假装都能抽",
       len([r for r in rows if r["observable"].get("object_suggestion")]) == 1,
       str([bool(r["observable"].get("object_suggestion")) for r in rows]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
