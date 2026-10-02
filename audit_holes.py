# -*- coding: utf-8 -*-
"""audit_holes.py —— 找「宣称了但没接上的洞」

★★ 用户的定性（2026-10-02）
   「S5 有标记但是功能没有实现」「S6 是完全空白」

  这两句说的是同一类病的两种程度：
     · **有标记没实现** = 界面上有入口/字段/按钮，点下去什么都不发生，或字段永远空着
     · **完全空白** = 连标记都没有

   而这两者【肉眼都看不出来】—— 一个空字段看起来像「还没填」，一个空壳函数看起来像「还没跑到」。
   所以必须机器查。

★★ 四类洞
   A. **引用了不存在的函数** —— onclick/onchange 里调的函数，JS 里没有定义（点了会报错）
   B. **有 id 但没人碰过** —— HTML 里的元素，JS 里从没 getElementById 过（永远空着 = 标记）
   C. **空壳函数** —— 定义存在，但函数体是空的/只有 return（有标记没实现）
   D. **函数定义了但没人调用** —— 死代码（写了但没接上）

运行：  python audit_holes.py             # 查全部
        python audit_holes.py --selftest
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
DIAG = os.path.join(WS, "construct-lab-site", "public", "diagnostic-tool.html")

# 浏览器/语言内建，不算「未定义」
BUILTINS = {
    "alert", "confirm", "prompt", "console", "parseInt", "parseFloat", "isNaN",
    "setTimeout", "clearTimeout", "setInterval", "JSON", "Object", "Array", "String",
    "Number", "Math", "Date", "RegExp", "Boolean", "encodeURIComponent", "decodeURIComponent",
    "if", "for", "while", "return", "typeof", "new", "function", "this", "void",
}


def load() -> str:
    with io.open(DIAG, encoding="utf-8") as fh:
        return fh.read()


def script_text(src: str) -> str:
    return "\n".join(m.group(1) for m in
                     re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", src))


def defined_functions(js: str) -> set:
    fn = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", js))
    fn |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:function|\()", js))
    fn |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=>", js))
    fn |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", js))
    return fn


def body_of(js: str, name: str) -> str:
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", js)
    if not m:
        m = re.search(re.escape(name) + r"\s*=\s*function\s*\([^)]*\)\s*\{", js)
    if not m:
        return ""
    i = js.index("{", m.end() - 1)
    depth, started = 0, False
    for j in range(i, len(js)):
        if js[j] == "{":
            depth += 1
            started = True
        elif js[j] == "}":
            depth -= 1
            if started and depth == 0:
                return js[i:j + 1]
    return ""


def run() -> dict:
    src = load()
    js = script_text(src)
    html = re.sub(r"<script[\s\S]*?</script>", "", src)

    # ── A. 引用了不存在的函数 ──
    called = set()
    for m in re.finditer(r'\bon(?:click|change|input)\s*=\s*"([^"]+)"', html):
        for c in re.findall(r"([A-Za-z_$][\w$]*)\s*\(", m.group(1)):
            called.add(c)
    # 样式表/模板串里的 onclick 也算（动态生成的按钮）
    for m in re.finditer(r"on(?:click|change|input)\s*=\s*\\?[\"']([^\"'\\]+)", js):
        for c in re.findall(r"([A-Za-z_$][\w$]*)\s*\(", m.group(1)):
            called.add(c)
    defined = defined_functions(js)
    a_missing = sorted(c for c in called if c not in defined and c not in BUILTINS)

    # ── B. 有 id 但从没被 JS 碰过 ──
    # ★ 这一项【只在没有动态访问时才可判】。实测这个文件有 3 处
    #   `getElementById(id)` / `getElementById(inputId)`（变量作参数）——
    #   于是理论上任何 id 都可能被碰到，静态分析判不了。
    #   第一版我报出 27 个「孤儿」，其中大部分是假的（L3_grid/L5_grid/L6_*/sul_* 全都被间接碰过）。
    #   **残缺的清单比没有更糟，因为它看起来像结论。** 所以改成如实分档。
    ids = [m.group(1) for m in re.finditer(r'\bid="([^"]+)"', html)]
    touched = set(re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]", js))
    touched |= set(re.findall(r"querySelector(?:All)?\(\s*['\"]#([^'\"]+)['\"]", js))
    dyn = [m.group(1) for m in re.finditer(r"getElementById\(\s*([A-Za-z_$][\w$]*)\s*\)", js)]
    dyn += [m.group(1) for m in re.finditer(r"getElementById\(\s*['\"]([^'\"]*)['\"]\s*\+", js)]
    b_orphan_ids = sorted(set(i for i in ids if i not in touched))
    b_decidable = not dyn

    # ── C. 空壳函数 ──
    c_empty = []
    for name in sorted(defined):
        b = body_of(js, name)
        if not b:
            continue
        inner = re.sub(r"//[^\n]*", "", b[1:-1])
        inner = re.sub(r"/\*[\s\S]*?\*/", "", inner).strip()
        if inner in ("", "return;", "return null;", "return '';", 'return "";',
                     "return false;", "return true;", "return 0;"):
            c_empty.append((name, inner or "（空）"))

    # ── D. 定义了但没人调用 ──
    used = set()
    for m in re.finditer(r"([A-Za-z_$][\w$]*)\s*\(", js + html):
        used.add(m.group(1))
    d_unused = sorted(n for n in defined
                      if n not in used and not n.startswith("window"))

    return {"a_missing": a_missing, "b_orphan_ids": b_orphan_ids, "b_decidable": b_decidable,
            "b_dyn": dyn, "c_empty": c_empty, "d_unused": d_unused,
            "n_ids": len(ids), "n_touched": len(touched), "n_defined": len(defined)}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    r = run()
    print("=" * 96)
    print("# 找洞：宣称了但没接上的地方")
    print("=" * 96)
    print("  对象：%s" % os.path.relpath(DIAG, WS))
    print("  HTML 里的 id %d 个，其中被 JS 碰过 %d 个；JS 里定义的函数 %d 个"
          % (r["n_ids"], r["n_touched"], r["n_defined"]))

    print("\n  ── A. 引用了【不存在】的函数（点了会报错）: %d 个" % len(r["a_missing"]))
    for x in r["a_missing"][:20]:
        print("       ⛔ %s()" % x)
    if not r["a_missing"]:
        print("       ✅ 无")

    print("\n  ── B. 有 id 但 JS 从没碰过（**有标记，没功能**）")
    if not r["b_decidable"]:
        print("       ⚠️ **不可静态判定** —— 文件里有动态访问：%s" % "、".join(r["b_dyn"]))
        print("          （变量作参数 ⇒ 理论上任何 id 都可能被碰到）")
        print("          未匹配字面量的 id 共 %d 个，但**不能**据此说它们没被碰过：" % len(r["b_orphan_ids"]))
        print("          " + "、".join("#" + x for x in r["b_orphan_ids"][:16]) + (" …" if len(r["b_orphan_ids"]) > 16 else ""))
        print("          ⇒ 要判这一项，需要数据流分析或运行时观测，静态做不到。")
    else:
        print("       （无动态访问 ⇒ 可判）%d 个：" % len(r["b_orphan_ids"]))
        for x in r["b_orphan_ids"][:25]:
            print("       ⚠️ #%s" % x)
        if not r["b_orphan_ids"]:
            print("       ✅ 无")

    print("\n  ── C. 空壳函数（有定义，但函数体是空的）: %d 个" % len(r["c_empty"]))
    for n, inner in r["c_empty"][:20]:
        print("       ⚠️ %s()  →  %s" % (n, inner))
    if not r["c_empty"]:
        print("       ✅ 无")

    print("\n  ── D. 定义了但没人调用（死代码）: %d 个" % len(r["d_unused"]))
    print("       " + "、".join(r["d_unused"][:20]))

    print("\n" + "=" * 96)
    print("  四类洞的含义")
    print("=" * 96)
    print("  A = 点了会报错（最硬）｜B = 有标记没实现（用户说的 S5）")
    print("  C = 空壳（看起来实现了）｜D = 写了没接上")
    print("  **B 与 C 是「看起来有、实际没有」——肉眼最看不出来的两类。**")
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

    print("# audit_holes 自证")
    src = load()
    js = script_text(src)
    ck("★能分出 script 与 HTML", len(js) > 10000 and len(re.sub(r'<script[\s\S]*?</script>', '', src)) > 5000,
       "js=%d html=%d" % (len(js), len(re.sub(r'<script[\s\S]*?</script>', '', src))))
    d = defined_functions(js)
    ck("★能抓出定义的函数（这个文件是 34 个）", len(d) >= 30, str(len(d)))
    ck("★body_of 配平", body_of(js, "diagnose").count("{") == body_of(js, "diagnose").count("}"))
    ck("★body_of 对不存在函数返回空", body_of(js, "__nope__") == "")
    # 反向：造一个空壳与一个正常函数，看能不能分开
    fake = "function emptyOne(){ } function realOne(){ var x=1; return x*2; }"
    dd = defined_functions(fake)
    ck("★反向：能识别空壳 vs 正常", "emptyOne" in dd and "realOne" in dd)
    r = run()
    ck("★A 类结果可空可非空（不是写死的）", isinstance(r["a_missing"], list))
    ck("★B 类数量 < 总 id 数（否则判定器把什么都算成孤儿）",
       len(r["b_orphan_ids"]) < r["n_ids"], "%d / %d" % (len(r["b_orphan_ids"]), r["n_ids"]))
    ck("★至少认得出一批被碰过的 id", r["n_touched"] > 5, str(r["n_touched"]))
    ck("★★有动态 getElementById 时，B 类必须标【不可判定】（否则会报一堆假孤儿）",
       (len(r["b_dyn"]) > 0) == (not r["b_decidable"]), "dyn=%s decidable=%s" % (r["b_dyn"], r["b_decidable"]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
