# -*- coding: utf-8 -*-
"""audit_layers.py —— 逐项体检结构诊断工具的 L0–L11 + SUL + 反馈回路

★★ 问的问题只有一个，但它能一次问穿每一层：
    **这一层填进去的东西，有没有人读？**

  工具里到处是 `updateState('X','path')` / `toggleCheck` / 评分组 —— 用户填了，
  写进了 state。但只有 `diagnose()` / `renderDiagnosis()` / 导出 / 配图提示词
  真正【读】了它，那一层才算参与推理。**写了没人读 = 装饰性输入**：
  用户以为自己在提供诊断依据，其实什么都没影响。

  这与本项目一贯的病同型：
    · 八维值域文档称「代码真相」，而代码全工作区零命中
    · 地图标题称「GDELT 实时」，而全文 GDELT 只出现 1 次
    · 档案越写越厚，却没有导入路径（审计 F20）
    · 工具里 11 层填了，但没人读 → 就是下一个

运行：  python audit_layers.py            # 体检
        python audit_layers.py --selftest
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
DIAG = os.path.join(WS, "construct-lab-site", "public", "diagnostic-tool.html")

# 只写不读的判定用这些「读者」函数体 —— 在它们之外出现的 state 路径都算没被消费
READERS = ["diagnose", "renderDiagnosis", "renderFearRadar", "renderOrderBars",
           "updateSUL", "updateProgress", "genGzhHTML", "genSubstackMD",
           "genVisPrompt", "exportReport", "loadArchive", "cascadeL2", "updateConfig"]


def read_html() -> str:
    with io.open(DIAG, encoding="utf-8") as fh:
        return fh.read()


def fn_body(src: str, name: str) -> str:
    """抓一个函数的函数体（按花括号配平）。"""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return ""
    i = src.index("{", m.end() - 1)
    depth, started = 0, False
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
            started = True
        elif src[j] == "}":
            depth -= 1
            if started and depth == 0:
                return src[i:j + 1]
    return ""


def layer_blocks(src: str) -> list:
    """按 layer-title 把 HTML 切成层块。返回 [(层号, 标题, 块文本)]。"""
    marks = []
    # ★ 这里修过一个 bug：原来写的是 `<span class="layer-num[^"]*">`，
    #   要求 class 之后【紧跟】>。而 L11 的那一行是
    #       <span class="layer-num" style="background:...">L11</span>
    #   多了个 style 属性 ⇒ L11 匹配不到 ⇒ 它的整块内容被并进了 L10 那一行。
    #   后果是「工具里没有 L11」这个错结论（实际有），以及 L10 的数字被污染。
    #   教训：切分用的正则必须允许标签里还有别的属性。
    for m in re.finditer(r'<span class="layer-num[^"]*"[^>]*>([^<]+)</span>'
                         r'<span class="layer-icon"[^>]*>[^<]*</span>\s*([^<]*)<', src):
        marks.append((m.start(), m.group(1).strip(), m.group(2).strip()))
    out = []
    for i, (pos, num, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        out.append((num, title, src[pos:end]))
    return out


def state_paths_in(text: str) -> set:
    """文本里出现的 state 路径（state.a.b.c → a.b.c）。"""
    return set(re.findall(r"\bstate\.([A-Za-z_][\w.]*)", text))


def handler_paths_in(text: str) -> set:
    """从【字符串形式】的状态路径里提取 —— 层块里的输入全靠这些。

    ★ 补这一层是因为第一次体检时逐层全是 0：层里根本不写 `state.X`，
      而是 `updateState('L1_name','actor.name')` / `selectRadio(this,'L2','continuity.type')`
      / `updateSUL('intent',...)` / `toggleCheck(this,'sources')` / 评分组的 data-path。
      只看 `state.` 字面量会把【每一层】都误报成空的。
    """
    out = set()
    for pat in (r"updateState\('[^']*'\s*,\s*'([^']+)'\)",
                r"selectRadio\(this\s*,\s*'[^']*'\s*,\s*'([^']+)'\)",
                r"updateSUL\('([^']+)'",
                r"toggleCheck\(this\s*,\s*'([^']+)'\)",
                r"data-path=\"([^\"]+)\"",
                r"state\.([A-Za-z_][\w.]*)\s*=\s*this\.value"):
        for m in re.findall(pat, text):
            out.add(m if m.startswith("SUL.") else m)
    # updateSUL 的键是 SUL.<k>
    for k in re.findall(r"updateSUL\('([^']+)'", text):
        out.discard(k)
        out.add("SUL." + k)
    return out


def whole_object_reads(reader_text: str) -> set:
    """【整对象被读】的根路径。

    ★ 为什么必须有这个：第一次体检把 L8 的四个核心恐惧判成「只写不读」——
      而工具自己的说明写着「这是诊断的核心输入」。查下去发现是
      `Object.entries(state.fears)` 与 `renderFearRadar(state.fears)` 这类【动态读】，
      字面量提取器看不见。**假阳性。**
      这与本项目一贯的病同型，只不过这次犯病的是我的审计器：
      提取口径不对题 ⇒ 结论反向。
    """
    roots = set()
    for pat in (r"Object\.(?:entries|keys|values)\(state\.([\w.]+)\)",
                r"\brender[A-Za-z]+\(state\.([\w.]+)\)",
                r"\b(?:const|let|var)\s+\w+\s*=\s*state\.([\w.]+)\s*[;,)\n]",
                r"state\.([\w.]+)\["):
        roots |= set(re.findall(pat, reader_text))
    return roots


def is_read(path: str, read_paths: set, read_roots: set) -> bool:
    """路径被读 ⟺ 它本身出现为字面量，或它的某个前缀被【整对象】读过。"""
    if path in read_paths:
        return True
    parts = path.split(".")
    for i in range(1, len(parts) + 1):
        if ".".join(parts[:i]) in read_roots:
            return True
    # 整对象读的根若在本路径之下（如读了 order.internal.basic，就算 order.internal 被用）
    for r in read_roots:
        if r.startswith(path + ".") or r == path:
            return True
    return False


def rating_map_paths(src: str) -> dict:
    """从 initRatingGroups() 的 map 里取出「哪个层有哪些路径」。

    ★ 为什么不解析 HTML 就够了：L3/L5/L8 的评分组在基座 HTML 里【没有】data-path，
      是 initRatingGroups() 运行时按容器 id 注入的：
          'L3_grid': ['existence.sovereignty', ...]
          'L5_grid': ['maintenance.legitimacy', ...]
          'L8_grid': ['fears.identity_loss', ...]
      只看 HTML 会把这三层误报成「0 条路径」—— 残缺的逐层表比没有更糟，
      因为它看起来像结论。
    """
    body = fn_body(src, "initRatingGroups")
    out = {}
    for m in re.finditer(r"'(L\d+)[A-Za-z_]*'\s*:\s*(\[[^\]]*\]|'[^']+')", body):
        cid, val = m.group(1), m.group(2)
        paths = re.findall(r"'([A-Za-z_][\w.]*)'", val)
        out.setdefault(cid, []).extend(p for p in paths if "." in p)
    # l6Map 里的键是 'L6_int_basic':'order.internal.basic' 这类
    for m in re.finditer(r"'(L\d+)_[a-z_]+'\s*:\s*'([A-Za-z_][\w.]*)'", body):
        out.setdefault(m.group(1), []).append(m.group(2))
    return out


def run() -> dict:
    src = read_html()
    layers = layer_blocks(src)
    injected = rating_map_paths(src)

    reader_text = "\n".join(fn_body(src, r) for r in READERS)
    read_paths = state_paths_in(reader_text) | handler_paths_in(reader_text)
    read_roots = whole_object_reads(reader_text)

    rating_paths = {p.strip("'") for p in
                    re.findall(r"'(?:existence|maintenance|fears|order)\.[a-z_.]+'", src)}
    all_written = (state_paths_in(src) | handler_paths_in(src) | rating_paths
                   | {p for v in injected.values() for p in v})

    rows = []
    for num, title, block in layers:
        paths = state_paths_in(block) | handler_paths_in(block)
        paths |= set(injected.get(num, []))          # ★ 补上运行时注入的那三层
        rd = sorted(p for p in paths if is_read(p, read_paths, read_roots))
        orf = sorted(p for p in paths if not is_read(p, read_paths, read_roots))
        rows.append({"num": num, "title": title, "paths": sorted(paths),
                     "writes": len(paths), "read": rd, "orphan": orf,
                     "injected": sorted(injected.get(num, []))})

    orphans = sorted(p for p in all_written if not is_read(p, read_paths, read_roots))
    # 按层归类孤儿，便于定位
    by_layer = {}
    for L in rows:
        for p in L["orphan"]:
            by_layer.setdefault(L["num"], []).append(p)
    return {"layers": rows, "read_paths": sorted(read_paths),
            "read_roots": sorted(read_roots), "injected": injected,
            "all_written": sorted(all_written), "orphans": orphans, "by_layer": by_layer}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    r = run()
    print("=" * 100)
    print("# 结构诊断工具 · 逐项体检（L0–L11 + SUL + 反馈回路）")
    print("=" * 100)
    print("  基座：%s" % os.path.relpath(DIAG, WS))
    print("  问的问题只有一个：**这一层填进去的东西，有没有人读？**")
    print("  读者 = %s" % "、".join(READERS[:6]) + " …")
    print("  整对象被读的根 = %s" % ("、".join("state." + r for r in r["read_roots"]) or "（无）"))
    print()
    print("  %-6s %-30s %6s %6s %6s  %s" % ("层", "标题", "路径", "被读", "只写", "只写不读的（装饰性输入）"))
    print("  " + "-" * 96)
    for L in r["layers"]:
        flag = "⛔" if (L["orphan"] and not L["read"]) else ("⚠️" if L["orphan"] else "✅")
        print("  %-6s %-30s %6d %6d %6d  %s"
              % (L["num"], L["title"][:30], L["writes"], len(L["read"]), len(L["orphan"]),
                 flag + (" " + "、".join(L["orphan"][:4]) if L["orphan"] else "")))
    print("  " + "-" * 96)
    print("\n  ★ 全局：写进 state 的路径 %d 条，被读者消费的 %d 条"
          % (len(r["all_written"]), len([p for p in r["all_written"] if p in r["read_paths"]])))
    if r["orphans"]:
        print("\n  ⛔ **只写不读（填了没人用的）共 %d 条**：" % len(r["orphans"]))
        for p in r["orphans"]:
            print("       · state.%s" % p)
    else:
        print("\n  ✅ 没有只写不读的路径。")
    print("=" * 100)
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

    print("# audit_layers 自证")
    src = read_html()
    ck("★能读到基座", len(src) > 50000, str(len(src)))

    # 层切分
    layers = layer_blocks(src)
    ck("★层块切出 ≥12 个（L0–L11 + SUL）", len(layers) >= 12, str(len(layers)))
    nums = [n for n, _t, _b in layers]
    ck("★层号含 L0..L11 与 SUL",
       "L0" in nums and "L11" in nums and "SUL" in nums, str(nums))

    # fn_body 配平
    b = fn_body(src, "diagnose")
    ck("★fn_body 能抓到 diagnose 的函数体", len(b) > 200, str(len(b)))
    ck("★fn_body 花括号配平", b.count("{") == b.count("}"),
       "%d vs %d" % (b.count("{"), b.count("}")))
    ck("★fn_body 对不存在的函数返回空串（不崩）", fn_body(src, "__nope__") == "")

    # state 路径提取
    ck("★state 路径提取正确",
       state_paths_in("x state.a.b = state.c; state.d") == {"a.b", "c", "d"},
       str(state_paths_in("x state.a.b = state.c; state.d")))

    # 反向：孤儿判定必须能【失败】—— 用一个真实存在的、被读的路径验
    r = run()
    ck("★读者集合非空（否则所有路径都会被误判成孤儿）",
       len(r["read_paths"]) >= 5, str(len(r["read_paths"])))
    ck("★不是所有写入路径都被判成孤儿（否则判定器坏了）",
       len(r["orphans"]) < len(r["all_written"]),
       "%d / %d" % (len(r["orphans"]), len(r["all_written"])))
    ck("★每个层都有路径或明确为空", isinstance(r["layers"], list) and len(r["layers"]) >= 12)
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
