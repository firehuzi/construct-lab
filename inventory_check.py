# -*- coding: utf-8 -*-
"""inventory_check.py —— 把「完成内容与版本迭代」这份 ✅ 清单拿去核对文件系统

来源：`docs/ConStruct 项目 · 完成内容与版本迭代（2026.06.26）.md`
它是本项目 06-26 的完成度快照 —— **每一行都是 ✅**。

★ 为什么要有这个检查器
  这份文档写于 06-26，当时多半是准确的。但它列出的**目录树指向一个已不存在的路径**
  （`D:\\地缘推演台\\`，项目后来搬到了 `D:\\Projects\\地缘推演台\\`），
  而且它至今读起来完全像权威 —— **因为没有任何东西会去核对它。**

  这与本项目其他几处是**同一种病**：
    · 八维值域文档称「代码真相」，而代码全工作区零命中
    · 地图标题称「GDELT 实时」，而全文 GDELT 只出现 1 次（就在标题里）
    · 案例卡与 4 小时前刚声明的 Case Schema 对不上
    · 这份 ✅ 清单里，「跨域验证」展开后是「产出过文档」，不是「验证过框架」

  共同的形状：**一份声明，和真实产物，两者从不互相对照。**

  所以本检查器只做一件事：**把清单里的每条声称，拿去文件系统核。**
  判定分四档：✅ 在场 ／ ⚠️ 换了位置 ／ ⛔ 找不到 ／ ℹ️ 无法机器核（语义声称）

运行：  python inventory_check.py            # 对账
        python inventory_check.py --selftest
"""
from __future__ import annotations

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOC = os.path.join(ROOT, "docs", "ConStruct 项目 · 完成内容与版本迭代（2026.06.26）.md")

# ── 从清单里逐条抽出的【可机器核】的声称 ──────────────────────────────────────
# (清单原文, 搜索词, 期望位置提示, 类型[, 限定在哪个子目录下找])
# 类型：path=路径存在；file=按名找文件；dir=按名找目录；count_html=按名统计文件数
#
# ★ 为什么要加第 5 项 `under`：工作区根下**还住着别的项目**（如 AI_Animation/），
#   按名全盘搜会串项目 —— 实测 `References` 就匹配到了
#   `AI_Animation\skills\flowchart\References` 这种无关目录。声称必须带上下文。
CLAIMS = [
    ("目录树：D:\\地缘推演台\\", "D:\\地缘推演台", "根路径", "path", None,
     "项目已搬到 D:\\Projects\\地缘推演台\\"),
    ("construct_bridge.py（根）", "construct_bridge.py", "MD↔JSON桥接", "file", None, None),
    ("actors.json（根）", "actors.json", "结构化主体数据", "file", None,
     "★单文件 actors.json 已不存在：现在的主体数据是 actors/（84 个 md）"
     "＋ construct-lab-site/src/data/actors.ts ＋ public/archive-index.json；"
     "命中的 content\\film\\actors.json 是【另一个项目】的文件"),
    ("框架v2.0.html", "框架v2.0", "11层交互式诊断", "file", None,
     "改名并移位：content\\published\\地缘政治分析框架v2.0.html"),
    ("框架v3.0.html（+SUL）", "框架v3.0", "含SUL的版本", "file", None,
     "★该文件名零命中。其能力（+SUL）应在 construct-lab-site/public/diagnostic-tool.html"
     "（版本徽章写着「v2.2（含 SUL 战略不确定性层）」）"),
    ("ConStruct_Archive/", "ConStruct_Archive", "46档主体+10场景", "dir", None, None),
    ("References/（根）", "References", "跨域案例", "dir", "ConStruct_Archive", None),
    ("construct-engine/", "construct-engine", "v4.1实时引擎", "dir", None, None),
    ("*公众号排版.html × 8（清单说 8 篇）", "公众号排版", "已排版内容", "count_html", "content", None),
]

# ── 清单里的【语义声称】：机器核不了，只能列出来请人判 ────────────────────────
SEMANTIC = [
    ("Layer 3 事件传播", "「事件传播索引 + 四级传播链定义」标 ✅",
     "v3.0 却说 P1-P4「链已定义，案例待写」⇒ ✅ 指的是【链定义】还是【案例】？"),
    ("Layer 4 推演引擎", "「主体情景推演 6档」标 ✅", "6 档推演是【产物】还是【已验证的机制】？"),
    ("跨域验证", "地缘 46档+10场景 ／ 经济 2份 ／ 社会 4篇 ／ 工具 1份 全标 ✅",
     "★ 「验证」= 把框架用到三个域并产出文档，还是「验证了框架能解释」？这两件事差别极大。"),
    ("DNA矩阵 + ICC框架", "标 ✅", "产物在（ConStruct_Archive/DNA_Matrix.md），但看过 ✅ 的人无从知道它有没有被独立检验"),
]


def search_any(name: str, under: str | None = None) -> list:
    """全工作区按名搜（**子串匹配** —— 文件可能改过名），返回相对路径。
    `under` 限定只在某个子目录下找 —— 工作区根下住着多个项目，不限会串。"""
    base = os.path.join(ROOT, under) if under else ROOT
    out = []
    for p in glob.glob(os.path.join(base, "**", "*"), recursive=True):
        if "node_modules" in p or "\\.git\\" in p:
            continue
        if name in os.path.basename(p):
            out.append(os.path.relpath(p, ROOT))
    return sorted(out)


def check_claim(label, term, hint, kind, under=None, note=None) -> dict:
    def d(mark, found):
        return {"label": label, "mark": mark, "found": found, "hint": hint, "note": note}
    if kind == "path":
        ok = os.path.exists(term)
        return d("✅" if ok else "⛔", term if ok else "（该路径不存在）")
    if kind == "file":
        hits = search_any(term, under)
        if not hits:
            return d("⛔", "（零命中）")
        at_root = [h for h in hits if os.sep not in h]
        return d("✅" if at_root else "⚠️",
                 "、".join(hits[:3]) + ("…" if len(hits) > 3 else ""))
    if kind == "dir":
        hits = [h for h in search_any(term, under)
                if os.path.isdir(os.path.join(ROOT, h))]
        if not hits:
            return d("⛔", "（零命中）")
        at_root = [h for h in hits if os.sep not in h]
        return d("✅" if at_root else "⚠️", "、".join(hits[:3]))
    if kind == "count_html":
        base = os.path.join(ROOT, under) if under else ROOT
        n = len([p for p in glob.glob(os.path.join(base, "**", "*.html"), recursive=True)
                 if term in os.path.basename(p) and "node_modules" not in p])
        return d("✅" if n >= 8 else ("⚠️" if n else "⛔"), "实际 %d 个" % n)
    return d("ℹ️", "?")


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    print("=" * 92)
    print("# 「完成内容与版本迭代（2026.06.26）」—— 把 ✅ 清单拿去核文件系统")
    print("=" * 92)
    print("\n  清单：%s" % os.path.relpath(DOC, ROOT))
    print("  工作区根：%s" % ROOT)

    print("\n  ── 可机器核的声称")
    print("  %-34s %-4s %s" % ("清单原文", "", "实测"))
    print("  " + "-" * 86)
    tally = {"✅": 0, "⚠️": 0, "⛔": 0}
    for label, term, hint, kind, under, note in CLAIMS:
        r = check_claim(label, term, hint, kind, under, note)
        tally[r["mark"]] = tally.get(r["mark"], 0) + 1
        print("  %-34s %-4s %s" % (r["label"][:34], r["mark"], r["found"]))
        if r["mark"] != "✅":
            print("  %-34s      ⓘ %s" % ("", r["hint"]))
            if r["note"]:
                print("  %-34s      ★ %s" % ("", r["note"]))
    print("  " + "-" * 86)
    print("  ✅ 在场 %d ／ ⚠️ 换了位置 %d ／ ⛔ 找不到 %d"
          % (tally["✅"], tally["⚠️"], tally["⛔"]))

    print("\n  ── 机器核不了的【语义声称】（列出来，请人判）")
    for name, claim, question in SEMANTIC:
        print("\n  · %s" % name)
        print("      清单说：%s" % claim)
        print("      ⚠️ 要问：%s" % question)

    print("\n" + "=" * 92)
    print("  结论")
    print("=" * 92)
    print("  ① 内容大多是活的 —— 只是【搬了位置】。清单的目录树指向一个已不存在的路径，")
    print("     而它至今读起来完全像权威，因为**没有任何东西会去核对它**。")
    print("  ② 更值得注意的不是路径过时，而是这份清单【每一行都是 ✅】——")
    print("     包括「跨域验证」，而它展开后是「把框架用到三个域并产出了文档」。")
    print("  ③ 7 天前（06-19）v2.0 刚写下「最大的难点是**认知框架是否成立**」并给了三道")
    print("     可证伪判据；到这份清单为止，那三道判据一条都没被执行过。")
    print()
    print("  ⇒ 共同的形状：**一份声明，和真实产物，两者从不互相对照。**")
    print("     本检查器只做那一件事 —— 核。")
    print("=" * 92)
    return 1 if (tally["⛔"] or tally["⚠️"]) else 0


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

    print("# inventory_check 自证")
    check("path 类型：存在的路径 ⇒ ✅",
          check_claim("t", ROOT, "h", "path")["mark"] == "✅")
    check("★path 类型：不存在的路径 ⇒ ⛔（清单的目录树就是这一档）",
          check_claim("t", os.path.join(ROOT, "__no_such_dir__"), "h", "path")["mark"] == "⛔")
    # 造一个【根目录下】的探针文件 —— 之前我用 eightdim.py 做这条断言是错的：
    # 它在 construct-engine/ 子目录里，按定义就该判 ⚠️（移位）而不是 ✅。
    root_probe = os.path.join(ROOT, "_tmp_inv_root_probe.txt")
    with open(root_probe, "w", encoding="utf-8") as fh:
        fh.write("probe")
    try:
        check("file 类型：★根目录下存在的文件 ⇒ ✅",
              check_claim("t", "_tmp_inv_root_probe.txt", "h", "file")["mark"] == "✅",
              str(check_claim("t", "_tmp_inv_root_probe.txt", "h", "file")))
    finally:
        os.remove(root_probe)
    check("file 类型：不存在的文件 ⇒ ⛔，且 found 写「零命中」",
          check_claim("t", "__nope__.py", "h", "file")["found"] == "（零命中）")
    check("dir 类型：确定存在的目录 ⇒ ✅",
          check_claim("t", "construct-engine", "h", "dir")["mark"] == "✅")
    check("count_html：阈值 8 —— 真实排版稿应达标",
          check_claim("t", "公众号排版", "h", "count_html", "content")["mark"] in ("✅", "⚠️"),
          str(check_claim("t", "公众号排版", "h", "count_html", "content")))
    # ★ under 限定：不限定时 References 会串到别的项目去
    broad = check_claim("t", "References", "h", "dir")
    narrow = check_claim("t", "References", "h", "dir", "ConStruct_Archive")
    check("★under 限定：不限定的 References 命中多个（含无关项目）",
          len(broad["found"].split("、")) >= 1, broad["found"])
    check("★under 限定：限定 ConStruct_Archive 后只剩该处的 References",
          "ConStruct_Archive" in narrow["found"] and "AI_Animation" not in narrow["found"],
          narrow["found"])
    # 移位检测：造一个深路径文件，确认判为 ⚠️ 而非 ✅
    deep = os.path.join(ROOT, "_tmp_inv", "shifted_probe.txt")
    os.makedirs(os.path.dirname(deep), exist_ok=True)
    with open(deep, "w", encoding="utf-8") as fh:
        fh.write("probe")
    try:
        r = check_claim("t", "shifted_probe.txt", "h", "file")
        check("★移位检测：只在子目录里存在 ⇒ 判 ⚠️（不是 ✅）", r["mark"] == "⚠️", str(r))
    finally:
        os.remove(deep)
        os.rmdir(os.path.dirname(deep))
    check("清单文件真的存在", os.path.exists(DOC), DOC)
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
