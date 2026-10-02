# -*- coding: utf-8 -*-
"""八维结构诊断 —— 从「假测量」重建为「真区分」（第 1 步：可回溯编码）

★★★ 为什么重写而不是补实现：
  值域文档把 parse_matrix / match_scale / encode_dir / SCALE_* 称作「代码真相」，
  而这些符号在【整个工作区】grep 零命中 —— 编码器从未存在。
  更根本的是：它假设存在一套统一的「构型对照矩阵」，
  而实测 96 份矩阵用了【约 110 种不同行名】，源行出现次数只有 1–13 次：
      核心恐惧 13 ｜ 深层Identity 11 ｜ 当前方法 8 ｜ 方法轨迹类型 7
      当前方向 6 ｜ Identity连续性 4 ｜ 他者结构 1
  ⇒ 前提是假的，所以覆盖一直被卡在 4 国。

★★★★★ 本脚本的三条规矩（就是为了不再「假测量」）：
  ① 【不发明映射】—— 只编码能直接从原文匹配到的值；
     匹配不到的维度一律 None，并把【原文证据】留下，交给分析师判断。
  ② 【不填默认】—— 明令禁止「未命中 → 默认 3」。
     默认值与真实值在产物里必须可区分（旧文档自己写「绝不填默认伪装」，规则却反着来）。
  ③ 【每个值可回溯】—— 每个维度都带 source（字段名）、key（命中的量表词）、text（原文单元格）。
     任何数字都能回答「你凭什么给它 3」。

运行：  python eightdim.py                 # 编码 + 落 data/eightdim.json
        python eightdim.py --audit         # 只跑区分性审计（不写文件）
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ACTORS_DIR = os.path.join(ROOT, "actors")
OUT = os.path.join(HERE, "data", "eightdim.json")

# ─────────────────────────────────────────────────────────────────────────────
# 量表：全部来自 content/lexicon/八维诊断值域设定.md（原文照抄，未增删键）
# 说明：这些是【序数编码构型矩阵】，不是测量。
# ─────────────────────────────────────────────────────────────────────────────
SCALES = {
    "身份连续性":   {"keys": {"极强": 5, "强": 4, "中": 3, "弱": 2}, "src": ["Identity连续性", "连续性类型"]},
    "存在方式":     {"keys": {"国体": 5, "山巅": 4, "制度实验": 4, "例外": 4, "天下": 4, "第三罗马": 4, "复兴": 4}, "src": ["深层Identity"]},
    "方法灵活性":   {"keys": {"线性+方法切换": 5, "scope递增式": 4, "循环式": 3, "单向锁定": 2}, "src": ["方法轨迹类型", "方法轨迹"]},
    "维持机制":     {"keys": {"交易式": 3, "复兴": 4, "武力恢复": 4, "冻结局": 4, "scope": 4, "循环": 3, "单向锁定": 4, "B": 4}, "src": ["当前方法阶段", "当前方法", "构型"]},
    "方向扩张性":   {"keys": {"↑": 4, "→": 3, "↓": 2, "扩张": 4, "维持": 3, "收缩": 2}, "src": ["当前方向", "方向基线"]},
    "秩序价值":     {"keys": {"山巅": 5, "例外": 5, "天下": 4, "国体": 3, "第三罗马": 3}, "src": ["深层Identity"]},   # ⚠️ 与「存在方式」同源，见下方 DUPLICATE_OF
    "他者复杂度":   {"keys": {"四重": 4, "三重": 3, "双极": 3, "双": 2}, "src": ["他者结构"]},
    "恐惧深度":     {"keys": {"终结": 4, "孤立": 3, "无法建立": 3, "失控": 3, "消除": 4, "双重复合": 4}, "src": ["核心恐惧"]},
}

# ★★ 结构性缺陷（本项调查发现，旧文档未记录）：
#   「秩序价值」的来源就是「存在方式」的同一格（深层Identity）——
#   即【八根轴里有两根是同一个数据】。值域文档自己写「同源再编码」，
#   但那等于承认雷达把一格数据画了两次。此处显式记录，供审计判定。
DUPLICATE_OF = {"秩序价值": "存在方式"}


def strip_md(s: str) -> str:
    return re.sub(r"[*`]", "", s).strip()


# ── 档案选择：与 construct-lab-site 的 pickCanonical 同精神（优先 v2_archive）──
def canonical_md(folder: str) -> str | None:
    files = [f for f in os.listdir(folder) if f.endswith(".md")]
    if not files:
        return None
    for pref in ("_v2_archive",):
        for f in files:
            if pref in f:
                return os.path.join(folder, f)
    plain = [f for f in files if "_v1" not in f and "_v2" not in f]
    if plain:
        return os.path.join(folder, sorted(plain)[0])
    return os.path.join(folder, sorted(files)[0])


# ── 字段抽取 ────────────────────────────────────────────────────────────────
def table_rows(text: str):
    for line in text.split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = [strip_md(c) for c in line.strip().strip("|").split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            yield cells


def field_rows(text: str) -> dict:
    """把「| 标签 | 值 |」与「### L2 …：A + B」都收进一个 dict（键=行名/小节名）。"""
    out: dict[str, str] = {}
    for cells in table_rows(text):
        k, v = cells[0], cells[1]
        if k and k not in out:
            out[k] = v
    for m in re.finditer(r"^#{2,4}\s+(.+)$", text, re.M):
        h = m.group(1).strip().replace("L2 ", "").replace("L2", "").strip()
        if "：" in h:
            k, v = h.split("：", 1)
            k = k.replace("连续性类型", "连续性类型").replace(" + 构型", "").replace("+构型", "").strip()
            if k and k not in out:
                out[k] = v.strip()
    return out


def hezhe_count(text: str) -> int | None:
    """他者系统：数【表格里的他者条目数】——这是结构量，不是文本判断。"""
    for i, line in enumerate(text.split("\n")):
        if "他者" in line and line.strip().startswith("|"):
            n = 0
            for line2 in text.split("\n")[i + 2:]:
                if not line2.strip().startswith("|"):
                    break
                cells = [c for c in line2.strip().strip("|").split("|") if c.strip()]
                if len(cells) >= 2:
                    n += 1
            return n or None
    return None


# ── 「构型对照矩阵」= 一张表、【多国家列】。按列取值才是 parse_matrix 的本意 ──
ROW_ALIASES = {
    "identity连续性": "身份连续性", "身份连续性": "身份连续性", "连续性": "身份连续性",
    "identity稳定性": "身份连续性", "身份稳定性": "身份连续性", "锚点连续性": "身份连续性",
    "深层identity": "存在方式", "存在方式": "存在方式",
    "方法轨迹类型": "方法灵活性", "方法轨迹": "方法灵活性", "方法切换模式": "方法灵活性",
    "当前方法阶段": "维持机制", "当前方法": "维持机制", "维持机制": "维持机制", "方法阶段": "维持机制",
    "当前方向": "方向扩张性", "方向": "方向扩张性",
    "他者结构": "他者复杂度", "外部他者功能": "他者复杂度",
    "核心恐惧": "恐惧深度", "终极恐惧": "恐惧深度", "终极恐惧性质": "恐惧深度",
}
COUNTRY_ALIASES = {
    "美国": "US", "中国": "CN", "日本": "JP", "俄罗斯": "RU", "俄国": "RU",
    "德国": "DE", "法国": "FR", "英国": "GB", "伊朗": "IR", "印度": "IN",
    "埃及": "EG", "以色列": "IL", "沙特": "SA", "土耳其": "TR", "台湾": "TW",
    "新加坡": "SG", "乌克兰": "UA", "韩国": "KR", "越南": "VN", "塞尔维亚": "RS",
    "朝鲜": "KP", "澳大利亚": "AUS", "欧盟": "EU", "北约": "NATO", "非盟": "AU",
    "东盟": "ASEAN",
}


def norm_country(col: str) -> str | None:
    c = re.split(r"[（(]", col)[0].strip()
    if c in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[c]
    if re.fullmatch(r"[A-Z]{2,3}", c):
        return c
    return None


def norm_row(row: str) -> str | None:
    return ROW_ALIASES.get(row.strip().lower())


def harvest(text: str) -> list[dict]:
    """抽出文本里所有「维度 | 国A | 国B | …」矩阵 → [{'US': {dim: raw}, 'CN': {...}}]"""
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not re.match(r"^\|\s*\*{0,2}\s*维度\s*\*{0,2}\s*\|", line.strip()):
            continue
        cells = [strip_md(c) for c in line.strip().strip("|").split("|")]
        cols = [norm_country(c) for c in cells[1:]]
        if sum(1 for c in cols if c) < 2:      # 至少两个国家列才算对照矩阵
            continue
        data: dict[str, dict] = defaultdict(dict)
        for j in range(i + 2, len(lines)):
            if not lines[j].strip().startswith("|"):
                break
            r = [strip_md(c) for c in lines[j].strip().strip("|").split("|")]
            if not r or not r[0]:
                continue
            dim = norm_row(r[0])
            if not dim:
                continue
            for k, code in enumerate(cols):
                if code and k + 1 < len(r) and r[k + 1] and dim not in data[code]:
                    data[code][dim] = r[k + 1]
        if data:
            out.append(data)
    return out


def match_scale(dim: str, raw: str):
    """在维度对应的量表里做子串匹配（长键优先）。未命中返回 (None, None) —— 不填默认。"""
    for key, val in sorted(SCALES[dim]["keys"].items(), key=lambda kv: -len(kv[0])):
        if key in raw:
            return val, key
    return None, None


def encode_actor(code: str, mats: list[dict], pool: list[dict]) -> dict:
    # 优先级：本主体文件夹里的矩阵 → 行数多的矩阵
    ordered = sorted(pool, key=lambda p: (p["owner"] != code,
                                          -sum(len(v) for v in p["data"].values())))
    dims: dict[str, dict] = {}
    for dim in SCALES:
        got = None
        for p in ordered:
            src_dim = "存在方式" if dim == "秩序价值" else dim   # 秩序价值与存在方式同源
            raw = p["data"].get(code, {}).get(src_dim)
            if not raw:
                continue
            val, key = match_scale(dim, raw)
            got = {"value": val, "key": key,
                   "source": "矩阵(%s 档案)" % p["owner"], "text": raw[:90],
                   "reason": None if val is not None else "命中矩阵但无量表词"}
            if val is not None:
                break
        dims[dim] = got or {"value": None, "key": None, "source": None, "text": None,
                            "reason": "无矩阵含该主体/该维度（不填默认）"}
    return dims


def collect() -> list[dict]:
    """★ 矩阵散落在各主体文件夹的不同 md 里 ⇒ 全收进一个池，再按国家列取值。
    ★ 而主体清单必须取【全部文件夹】——因为矩阵是多国列：
      埃及档案的表里有「以色列」列、沙特档案的表里有「以色列」列，
      故以色列的值来自【别人的】矩阵。只遍历「自有矩阵」的主体就会漏掉它们。
    """
    folder_mats: dict[str, list[dict]] = {}
    all_codes: list[str] = []
    for tier in ("Tier1", "Tier2"):
        base = os.path.join(ACTORS_DIR, tier)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder):
                continue
            all_codes.append(name)
            mats = []
            for fn in sorted(f for f in os.listdir(folder) if f.endswith(".md")):
                with open(os.path.join(folder, fn), encoding="utf-8") as fh:
                    mats += harvest(fh.read())
            if mats:
                folder_mats[name] = mats
    pool = [{"owner": c, "data": m} for c, ms in folder_mats.items() for m in ms]
    actors = []
    for code in all_codes:
        actors.append({"code": code,
                       "matrices_in_folder": len(folder_mats.get(code, [])),
                       "dims": encode_actor(code, folder_mats.get(code, []), pool)})
    return actors


# ── 审计：这个维度到底会不会【区分】？ ─────────────────────────────────────
def entropy(vals: list) -> float:
    import math
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0.0
    c = Counter(vals)
    n = len(vals)
    return -sum((k / n) * math.log2(k / n) for k in c.values())


def audit(actors: list[dict]) -> int:
    dims = list(SCALES.keys())
    bad = 0
    print("=" * 92)
    print("# 八维结构诊断 · 区分性审计（%d 个主体）" % len(actors))
    print("=" * 92)
    print("\n  %-12s %8s %8s %10s  %s" % ("维度", "有值", "覆盖率", "取值种类", "判定"))
    print("  " + "-" * 82)
    for d in dims:
        vals = [a["dims"][d]["value"] for a in actors]
        got = [v for v in vals if v is not None]
        kinds = len(set(got))
        cov = len(got) / max(1, len(actors))
        if not got:
            verdict = "✗ 零覆盖 —— 无法区分（该维度当前不可用）"
            bad += 1
        elif kinds == 1:
            verdict = "✗ 常量（所有主体同值）—— 装饰，不区分"
            bad += 1
        elif kinds == 2:
            verdict = "⚠ 仅二分 —— 区分力弱"
        else:
            verdict = "✓ 可区分（%d 种取值，熵 %.2f）" % (kinds, entropy(got))
        note = ""
        if d in DUPLICATE_OF:
            note = "  ← 与「%s」同源（同一单元格）" % DUPLICATE_OF[d]
            bad += 1
        print("  %-12s %8d %7.0f%% %10d  %s%s" % (d, len(got), cov * 100, kinds, verdict, note))

    print("\n  每个主体填了几维（满分 8）：")
    dist = Counter(sum(1 for v in a["dims"].values() if v["value"] is not None) for a in actors)
    for k in sorted(dist, reverse=True):
        print("    %d 维：%d 个主体" % (k, dist[k]))

    print("\n  全 8 维填充的主体：", end="")
    full = [a["code"] for a in actors if all(v["value"] is not None for v in a["dims"].values())]
    print("、".join(full) if full else "（无）")

    print("\n" + "=" * 92)
    print("  判定汇总：%d 个维度不合格（零覆盖／常量／同源重复）" % bad)
    print("  ⚠️ 边界：覆盖率只说明【从档案里能否直接匹配到量表词】，")
    print("     不代表语义正确；未匹配≠该维度不适用，只表示【不允许我填默认值】。")
    print("=" * 92)
    return bad


def main() -> int:
    actors = collect()
    if "--audit" not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump({"scales": SCALES, "duplicate_of": DUPLICATE_OF, "actors": actors},
                      fh, ensure_ascii=False, indent=2)
        print("已写出 %s（%d 主体）" % (os.path.relpath(OUT, ROOT), len(actors)))
    return 0 if audit(actors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
