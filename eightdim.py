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
from itertools import combinations

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
    """把三种载体都收进一个 dict（键=行名/小节名/引用块标签）：
       ① 表格行 `| 标签 | 值 |`
       ② 小节标题 `### L2 …：A + B`
       ③ 引用块头部 `> 状态方向基线：→（维持…）`
    ★ ③ 是必须的：`方向基线` 这类字段【只写在引用块头部】，不在表格里。
      （同一个坑在 construct-lab-site 审计里踩过一次：字段在 blockquote，不在表。）
    """
    out: dict[str, str] = {}
    for cells in table_rows(text):
        k, v = cells[0], cells[1]
        if k and k not in out:
            out[k] = v
    for m in re.finditer(r"^#{2,4}\s+(.+)$", text, re.M):
        h = m.group(1).strip().replace("L2 ", "").replace("L2", "").strip()
        if "：" in h:
            k, v = h.split("：", 1)
            k = k.replace(" + 构型", "").replace("+构型", "").strip()
            if k and k not in out:
                out[k] = v.strip()
    for line in text.split("\n"):
        s = line.strip()
        if not s.startswith(">"):
            continue
        body = strip_md(s.lstrip(">").strip())
        for part in body.split("|"):
            if "：" not in part:
                continue
            k, v = part.split("：", 1)
            k, v = k.strip(), v.strip()
            if k and v and k not in out:
                out[k] = v
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
    """在维度对应的量表里做子串匹配（长键优先）。未命中返回 (None, None) —— 不填默认。

    ★ 单字键必须【锚定在单元格开头】：量表里的 强/中/弱/↑/→/↓ 只有一个字，
      若在全串里找，任何单元格都可能碰巧含「中」字而被误判成「中＝3」。
      实测就发生过：「身份连续性」有两个值来自 `连续性类型` 单元格里碰巧的「中」。
      （矩阵单元格的写法是 `强（建国文本+宪法框架250年）`，量词在开头。）
    """
    for key, val in sorted(SCALES[dim]["keys"].items(), key=lambda kv: -len(kv[0])):
        if len(key) == 1:
            if key in raw[:8]:
                return val, key
        elif key in raw:
            return val, key
    return None, None


# ★★ 第二条取值来源：矩阵覆盖不到时，回退到【主体自己的档案字段】。
#   为什么必须回退：矩阵是多国列、全域只有约 15 个国家列 ——
#   只用矩阵，覆盖到不了 47 份档案的量级（目标 (1)：覆盖 4 → 40+）。
#   规矩不变：仍是【对着同一组量表做子串匹配】，匹配不到就 None，不发明映射。
FIELD_SOURCES = {
    "身份连续性":   ["连续性类型", "Identity连续性"],
    "存在方式":     ["深层Identity", "存在方式"],
    "方法灵活性":   ["方法轨迹类型", "方法轨迹"],
    "维持机制":     ["构型", "当前方法阶段", "当前方法"],
    "方向扩张性":   ["方向基线", "当前方向"],
    "秩序价值":     ["深层Identity", "秩序价值"],
    "恐惧深度":     ["核心恐惧", "终极恐惧"],
}


def encode_actor(code: str, text: str, mats: list[dict], pool: list[dict]) -> dict:
    """取值顺序：① 构型对照矩阵（分析师显式对比，保真度最高）
                  ② 主体自己的档案字段（覆盖面最广）
                  ③ None + 理由（绝不填默认）"""
    ordered = sorted(pool, key=lambda p: (p["owner"] != code,
                                          -sum(len(v) for v in p["data"].values())))
    fields = field_rows(text)
    dims: dict[str, dict] = {}
    for dim in SCALES:
        got = None
        # ① 矩阵
        for p in ordered:
            src_dim = DUPLICATE_OF.get(dim, dim)   # 同源维度读同一格（声明只有一处）
            raw = p["data"].get(code, {}).get(src_dim)
            if not raw:
                continue
            val, key = match_scale(dim, raw)
            if val is not None:
                got = {"value": val, "key": key, "source": "矩阵(%s 档案)" % p["owner"],
                       "text": raw[:90], "reason": None}
                break
        # ② 档案字段
        if got is None:
            for fname in FIELD_SOURCES.get(dim, []):
                cell = fields.get(fname)
                if cell is None:
                    for k, v in fields.items():
                        if fname in k:
                            cell = v
                            break
                if not cell:
                    continue
                val, key = match_scale(dim, cell)
                if val is not None:
                    got = {"value": val, "key": key, "source": "档案字段(%s)" % fname,
                           "text": cell[:90], "reason": None}
                    break
        dims[dim] = got or {"value": None, "key": None, "source": None, "text": None,
                            "reason": "矩阵与该档案字段都未命中量表词（不填默认）"}
    # ★★ 他者复杂度：优先用【结构计数】—— 数他者系统表的条目数。
    #   这是【结构量】而非文本匹配：2 条→双极、3 条→三重、4+ 条→四重。
    n = hezhe_count(text)
    if n:
        key = "四重" if n >= 4 else "三重" if n == 3 else "双极" if n == 2 else "双"
        dims["他者复杂度"] = {"value": SCALES["他者复杂度"]["keys"].get(key),
                             "key": key, "source": "他者系统(结构计数)",
                             "text": "他者系统表 %d 条" % n, "reason": None}
    return dims


def actor_sources() -> list[tuple[str, list[str]]]:
    """枚举 actors/ 下的全部主体 —— 覆盖两种组织形态：
       ① 子目录式（Tier1/CN、Tier2/DE、Tier3/组织/NATO）
       ② 平铺 md 式（Tier3/企业/NVDA.md、Tier3/组织/UN.md）
    """
    found: dict[str, list[str]] = {}

    def add(code: str, paths: list[str]) -> None:
        found.setdefault(code, []).extend(paths)

    for tier in ("Tier1", "Tier2"):
        base = os.path.join(ACTORS_DIR, tier)
        if not os.path.isdir(base):
            continue
        for e in sorted(os.listdir(base)):
            p = os.path.join(base, e)
            if os.path.isdir(p):
                add(e, sorted(os.path.join(p, f) for f in os.listdir(p) if f.endswith(".md")))
    for grp in ("企业", "组织"):
        base = os.path.join(ACTORS_DIR, "Tier3", grp)
        if not os.path.isdir(base):
            continue
        for e in sorted(os.listdir(base)):
            p = os.path.join(base, e)
            if os.path.isdir(p):
                add(e, sorted(os.path.join(p, f) for f in os.listdir(p) if f.endswith(".md")))
            elif e.endswith(".md"):
                add(e[:-3], [p])
    return [(c, ps) for c, ps in found.items() if ps]


def collect() -> list[dict]:
    """★ 矩阵散落在各主体文件夹的不同 md 里 ⇒ 全收进一个池，再按国家列取值。
    ★ 主体清单取【全部 47 个】（Tier1+Tier2+Tier3），因为矩阵是多国列：
      埃及档案的表里有「以色列」列、沙特档案的表里有「以色列」列，
      故以色列的值来自【别人的】矩阵；而 Tier3 的字段回退需要它自己在清单里。
    """
    srcs = actor_sources()
    folder_mats: dict[str, list[dict]] = {}
    folder_text: dict[str, str] = {}
    for code, paths in srcs:
        chunks, mats = [], []
        for path in paths:
            with open(path, encoding="utf-8") as fh:
                t = fh.read()
            chunks.append(t)
            mats += harvest(t)
        folder_text[code] = "\n\n".join(chunks)
        if mats:
            folder_mats[code] = mats
    pool = [{"owner": c, "data": m} for c, ms in folder_mats.items() for m in ms]
    actors = []
    for code, _paths in srcs:
        actors.append({"code": code,
                       "matrices_in_folder": len(folder_mats.get(code, [])),
                       "dims": encode_actor(code, folder_text[code],
                                            folder_mats.get(code, []), pool)})
    return actors


# ── 审计：这个维度到底会不会【区分】？ ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# 账本（Mechanism Ledger）—— 照 TaoPaw 的纪律移植
#
# TaoPaw 原话（机制算子对账.md §9.1）：
#   「l2_relations_ab.txt 自初始提交起没再生成过……『猫格与个体.md』还在拿它当
#     『实测』引用 —— 而且当时看不出来，因为日志里没写『我是在哪一版引擎上跑的』。」
# TaoPaw 原话（本地模拟实验平台-方案.md §4.3）：
#   「指纹不匹配 ⇒ 老 batch 标『过期』，⛔ 不许当证据用」
#
# 移植过来是三把戳 + 一道闸门：
#   ① 编码器指纹  eightdim.py@<行数>行·<FNV1a32>   （= TaoPaw 的引擎指纹）
#   ② 语料指纹    archives@<份数>份·<FNV1a32>       （= 输入侧：47 份档案的内容）
#   ③ 量表指纹    scales·<FNV1a32>                  （= 规则侧：量表与映射）
#   任一不匹配 ⇒ 产物【过期】，不许当证据用。
#
# ConStruct 此前【完全没有】这套：全仓 指纹 0 处 / 台账 0 处 / 过期标记 0 处。
# 后果实测过一次：我第一版编码器按行取值，把覆盖率假性压到 9%，
# 而 eightdim.json 里【没有任何东西】能说明它是哪一版、基于哪批档案算的。
# ══════════════════════════════════════════════════════════════════════════════

def fnv1a32(data: bytes) -> str:
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h


def encoder_print() -> str:
    """① 编码器自身的戳：文件@行数·FNV1a32（TaoPaw 的 `behavior_engine.dart@<行>·<hash>` 同格式）"""
    with open(__file__, "rb") as fh:
        raw = fh.read()
    return "eightdim.py@%d行·%s" % (raw.count(b"\n") + 1, fnv1a32(raw))


def corpus_print() -> str:
    """② 语料指纹：喂进去的每一份档案的【路径:大小:内容hash】排序后总哈希。
    这一把戳是「档案改了 ⇒ 编码过期」能否被机器查出来的关键。"""
    parts = []
    srcs = actor_sources()
    for code, paths in sorted(srcs):
        for p in sorted(paths):
            with open(p, "rb") as fh:
                raw = fh.read()
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            parts.append("%s:%d:%s" % (rel, len(raw), fnv1a32(raw)))
    return "archives@%d份·%s" % (len(srcs), fnv1a32("\n".join(parts).encode("utf-8")))


def scales_print() -> str:
    """③ 量表指纹：量表本身也是会改的 —— 改了它，老编码同样失效。"""
    payload = json.dumps([SCALES, FIELD_SOURCES, ROW_ALIASES, COUNTRY_ALIASES, DUPLICATE_OF],
                         ensure_ascii=False, sort_keys=True)
    return "scales·%s" % fnv1a32(payload.encode("utf-8"))


def git_head() -> str:
    """直接读 .git，不走 subprocess（沙箱里管道捕获可能 EPERM）。"""
    for cand in (os.path.join(HERE, ".git"), os.path.join(ROOT, ".git")):
        try:
            with open(os.path.join(cand, "HEAD")) as fh:
                ref = fh.read().strip()
            if ref.startswith("ref: "):
                with open(os.path.join(cand, ref[5:].strip())) as fh:
                    return fh.read().strip()[:7]
            return ref[:7]
        except Exception:
            continue
    return "?"


def fingerprints() -> dict:
    return {"encoder": encoder_print(), "corpus": corpus_print(),
            "scales": scales_print(), "git": git_head()}


def ledger(actors: list[dict]) -> dict:
    """独立格数 vs 伪重复 —— TaoPaw §4.6 的纪律：
       「『跑得多』不等于『知道得多』……平台必须把『独立样本』做成机器算的数。」
    套到八维：47 主体 × 8 维 = 376 个数字看着很多，独立信息量是多少？
    """
    nominal = len(actors) * len(SCALES)
    filled = sum(1 for a in actors for v in a["dims"].values() if v["value"] is not None)
    kinds = Counter()
    owners = Counter()
    for a in actors:
        for v in a["dims"].values():
            if v["value"] is None:
                continue
            src = v["source"] or "?"
            kinds[src.split("(")[0]] += 1
            if "矩阵(" in src:
                owners[src.split("(")[1].split(" ")[0]] += 1
    n_mat = sum(owners.values())
    return {
        "nominal_cells": nominal,
        "filled_cells": filled,
        "fill_rate": round(filled / nominal, 4) if nominal else 0.0,
        "source_kinds": dict(kinds),
        "independent_matrix_owners": len(owners),
        "cells_from_matrices": n_mat,
        "pseudo_replication_matrix": round(n_mat / len(owners), 2) if owners else 0.0,
        "note": ("一个非空格 ≠ 一次独立观测：同一份矩阵一次给出多国多行。"
                 "与 TaoPaw 那句同构 ——「同一条命的第 1000 天，不是第 1000 个样本」。"),
    }


def gate() -> int:
    """新鲜度闸门：不重新编码，只比对【已落盘产物】的戳与当前状态。
    TaoPaw §4.3：「指纹不匹配 ⇒ 老 batch 标『过期』，⛔ 不许当证据用」"""
    print("─" * 92)
    print("# 八维编码 · 新鲜度闸门")
    print("─" * 92)
    if not os.path.exists(OUT):
        print("  ❌ 未找到产物 %s —— 先跑 python eightdim.py" % os.path.relpath(OUT, ROOT))
        return 1
    with open(OUT, encoding="utf-8") as fh:
        stored = json.load(fh)
    old = stored.get("fingerprint") or {}
    new = fingerprints()
    bad = 0
    # ★ 只用【描述内容的】三把戳判定：编码器 / 语料 / 量表。
    #   git commit 只作 provenance【不参与判定】——
    #   否则产物一提交，HEAD 立刻变，产物会把自己判成过期（自指死锁）。
    for key, label in (("encoder", "编码器"), ("corpus", "语料  "), ("scales", "量表  ")):
        o, n = old.get(key), new.get(key)
        ok = (o == n)
        if not ok:
            bad += 1
        print("  %s %s  存=%s" % ("✅" if ok else "❌", label, o or "(无)"))
        if not ok:
            print("             现=%s" % n)
    print("  ⓘ git    %s（provenance，不参与判定：产物一旦提交，HEAD 必然变）"
          % (old.get("git") or "(无)"))
    print("─" * 92)
    if bad:
        print("  ⛔ 产物【过期】：%d 把戳不匹配 ⇒ 不许当证据用。" % bad)
        print("     修法：重新跑 python eightdim.py，并【重新核对】由此得出的结论。")
        return 1
    print("  ✅ 新鲜：三把内容戳全部匹配。")
    return 0


def entropy(vals: list) -> float:
    import math
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0.0
    c = Counter(vals)
    n = len(vals)
    return -sum((k / n) * math.log2(k / n) for k in c.values())


def judge_dimension(dim: str, actors: list[dict]) -> dict:
    """★ 纯判定函数 —— audit() 与 --selftest 【共用同一个】。
    不重写被检查的逻辑：否则自证只能证明「副本自洽」，不能证明审计本身会失败。
    """
    got = [a["dims"][dim]["value"] for a in actors
           if a["dims"].get(dim, {}).get("value") is not None]
    kinds = len(set(got))
    cov = len(got) / max(1, len(actors))
    if not got:
        verdict, level = "✗ 零覆盖 —— 无法区分（该维度当前不可用）", "bad"
    elif kinds == 1:
        verdict, level = "✗ 常量（所有主体同值）—— 装饰，不区分", "bad"
    elif kinds == 2:
        verdict, level = "⚠ 仅二分 —— 区分力弱", "weak"
    else:
        verdict, level = "✓ 可区分（%d 种取值，熵 %.2f）" % (kinds, entropy(got)), "ok"
    return {"dim": dim, "filled": len(got), "coverage": cov,
            "kinds": kinds, "verdict": verdict, "level": level}


def derived_duplicates(actors: list[dict]) -> Counter:
    """从【数据】推出哪些维度对共享同一格证据（同 source ＋ 同 text）。
    TaoPaw §9.4：「账本里手写的读者表如果和代码扫出来的对不上就报 ❌」——
    对应到这里，同源不该只靠手写声明，要能从数据扫出来、两边对账。
    """
    pairs = Counter()
    for a in actors:
        bycell = defaultdict(list)
        for d, v in a["dims"].items():
            if v.get("value") is not None and v.get("source") and v.get("text"):
                bycell[(v["source"], v["text"])].append(d)
        for _cell, ds in bycell.items():
            if len(ds) >= 2:
                for x, y in combinations(sorted(ds), 2):
                    pairs[(x, y)] += 1
    return pairs


def reconcile_duplicates(actors: list[dict]) -> list[tuple]:
    """声明的同源 vs 数据里扫出来的同源 —— 【两个方向】都查。"""
    derived = derived_duplicates(actors)
    declared = {tuple(sorted((k, v))) for k, v in DUPLICATE_OF.items()}
    found = set(derived)
    problems = []
    for p in sorted(declared - found):
        problems.append(("❌ 账本声明同源、数据里扫不出来", p[0], p[1], 0))
    for p in sorted(found - declared):
        problems.append(("❌ 数据里确是同源、账本没声明", p[0], p[1], derived[p]))
    return problems


def dim_defect(dim: str, actors: list[dict]) -> bool:
    """★ 单条规则、单处定义：一个维度算不算不合格。
    两种情形都算，且【每维只计一次】：
      · 区分力不合格（零覆盖／常量）
      · 同源重复（八根轴里两根是同一格数据）—— 这一条【独立于对账】：
        即使账本声明与数据一致（对账 ✅），同源本身依然是框架缺陷。
    """
    return judge_dimension(dim, actors)["level"] == "bad" or dim in DUPLICATE_OF


def audit_bad_count(actors: list[dict]) -> int:
    """不合格维度数 + 对账不一致数 —— audit() 与 --selftest 共用这一个数。"""
    return (sum(1 for d in SCALES if dim_defect(d, actors))
            + len(reconcile_duplicates(actors)))


def audit(actors: list[dict]) -> int:
    dims = list(SCALES.keys())
    bad = audit_bad_count(actors)      # ★ 汇总只由这一个函数算，避免与表体分歧
    led = ledger(actors)
    print("=" * 92)
    print("# 八维结构诊断 · 区分性审计（%d 个主体）" % len(actors))
    print("=" * 92)
    # ── 账本：独立格数 vs 伪重复（TaoPaw §4.6 的纪律做成机器算的数）──
    print("\n【账本 · 独立格数 vs 伪重复】")
    print("  名义格数 = %d（%d 主体 × 8 维）　实际非空 = %d（%.0f%%）"
          % (led["nominal_cells"], len(actors), led["filled_cells"], led["fill_rate"] * 100))
    print("  独立来源种类 = %d 种：%s"
          % (len(led["source_kinds"]),
             "　".join("%s %d" % (k, v) for k, v in
                       sorted(led["source_kinds"].items(), key=lambda kv: -kv[1]))))
    print("  其中矩阵来源 = %d 格 ÷ %d 份矩阵 ⇒ 伪重复倍数 %.1f"
          % (led["cells_from_matrices"], led["independent_matrix_owners"],
             led["pseudo_replication_matrix"]))
    print("  ⚠️ %s" % led["note"])

    print("\n  %-12s %8s %8s %10s  %s" % ("维度", "有值", "覆盖率", "取值种类", "判定"))
    print("  " + "-" * 82)
    for d in dims:
        j = judge_dimension(d, actors)
        note = ""
        if d in DUPLICATE_OF:
            note = "  ← 与「%s」同源（账本声明）" % DUPLICATE_OF[d]
        print("  %-12s %8d %7.0f%% %10d  %s%s"
              % (d, j["filled"], j["coverage"] * 100, j["kinds"], j["verdict"], note))

    print("\n  每个主体填了几维（满分 8）：")
    dist = Counter(sum(1 for v in a["dims"].values() if v["value"] is not None) for a in actors)
    for k in sorted(dist, reverse=True):
        print("    %d 维：%d 个主体" % (k, dist[k]))

    print("\n  全 8 维填充的主体：", end="")
    full = [a["code"] for a in actors if all(v["value"] is not None for v in a["dims"].values())]
    print("、".join(full) if full else "（无）")

    # ── 同源对账：声明 vs 数据扫出来的（TaoPaw §9.4 的纪律）──
    print("\n【同源对账 · 账本声明 vs 数据扫出来的】")
    probs = reconcile_duplicates(actors)
    if probs:
        for msg, x, y, n in probs:
            extra = "（数据里 %d 个主体同格）" % n if n else ""
            print("  %s：%s ↔ %s%s" % (msg, x, y, extra))
    else:
        decl = "、".join("%s↔%s" % (k, v) for k, v in sorted(DUPLICATE_OF.items()))
        print("  ✅ 两边一致：%s" % (decl or "（无声明）"))

    print("\n" + "=" * 92)
    print("  判定汇总：%d 个维度不合格（零覆盖／常量／同源对账不一致）" % bad)
    print("  ⚠️ 边界：覆盖率只说明【从档案里能否直接匹配到量表词】，")
    print("     不代表语义正确；未匹配≠该维度不适用，只表示【不允许我填默认值】。")
    print("=" * 92)
    return bad


# ══════════════════════════════════════════════════════════════════════════════
# 自证（--selftest）：植入已知缺陷，验证审计【必须抓到】
# TaoPaw §9.4 原话：「它不是一个永远绿灯的摆设。」
# 每条断言都打在 judge_dimension / ledger / reconcile_duplicates 这些【真函数】上，
# 不另写副本 —— 否则证明的只是副本自洽。
# ══════════════════════════════════════════════════════════════════════════════

def selftest() -> int:
    n_pass = n_fail = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal n_pass, n_fail
        if cond:
            n_pass += 1
            print("  ✅ %s" % name)
        else:
            n_fail += 1
            print("  ❌ %s   %s" % (name, detail))

    def mk(vals: dict, code: str = "T") -> dict:
        return {"code": code,
                "dims": {d: {"value": vals.get(d), "key": None, "source": None,
                             "text": None, "reason": None} for d in SCALES}}

    print("=" * 92)
    print("# 八维审计 · 自证（植入缺陷，审计必须抓到）")
    print("=" * 92)

    print("\n【A｜维度判定：四种形态各植一个】")
    ones = [mk({"身份连续性": 3}) for _ in range(5)]
    check("常量（5 个主体同值）⇒ bad", judge_dimension("身份连续性", ones)["level"] == "bad",
          judge_dimension("身份连续性", ones)["verdict"])
    empt = [mk({}) for _ in range(5)]
    check("零覆盖（全空）⇒ bad", judge_dimension("身份连续性", empt)["level"] == "bad")
    two = [mk({"身份连续性": v}) for v in (3, 4, 3, 4, 3)]
    check("仅二分（{3,4}）⇒ weak", judge_dimension("身份连续性", two)["level"] == "weak")
    three = [mk({"身份连续性": v}) for v in (2, 3, 4, 2, 3)]
    check("三分（{2,3,4}）⇒ ok", judge_dimension("身份连续性", three)["level"] == "ok")
    part = [mk({"身份连续性": 3}), mk({"身份连续性": 4}), mk({}), mk({}), mk({})]
    check("覆盖率 = 2/5 = 0.4",
          abs(judge_dimension("身份连续性", part)["coverage"] - 0.4) < 1e-9,
          str(judge_dimension("身份连续性", part)["coverage"]))

    print("\n【B｜熵：钉子值，不是感觉】")
    check("全同 ⇒ 熵 0.0", abs(entropy([3, 3, 3, 3]) - 0.0) < 1e-9)
    check("两值各半 ⇒ 熵 1.0", abs(entropy([3, 4, 3, 4]) - 1.0) < 1e-9)
    check("空 ⇒ 熵 0.0", entropy([]) == 0.0)

    print("\n【C｜账本：伪重复】")
    same = []
    for i in range(4):
        a = mk({d: (i % 3) + 2 for d in SCALES})
        for d in SCALES:                      # 全部来自同一份矩阵
            a["dims"][d]["source"] = "矩阵(XX 档案)"
            a["dims"][d]["text"] = "cell-%s" % d
        same.append(a)
    L = ledger(same)
    check("全部同源 ⇒ 伪重复倍数 = 格数",
          abs(L["pseudo_replication_matrix"] - L["cells_from_matrices"]) < 1e-9,
          str(L["pseudo_replication_matrix"]))
    indep = []
    for i in range(4):
        a = mk({d: (i % 3) + 2 for d in SCALES})
        for j, d in enumerate(SCALES):        # 每【格】一个独一无二的来源
            a["dims"][d]["source"] = "矩阵(X%d_%d 档案)" % (i, j)
            a["dims"][d]["text"] = "cell"
        indep.append(a)
    L2 = ledger(indep)
    check("每格独立 ⇒ 伪重复倍数 = 1.0",
          abs(L2["pseudo_replication_matrix"] - 1.0) < 1e-9,
          str(L2["pseudo_replication_matrix"]))
    check("（对照）全部来源同一个 ⇒ 倍数 = 格数 32",
          abs(ledger(same)["pseudo_replication_matrix"] - 32.0) < 1e-9,
          str(ledger(same)["pseudo_replication_matrix"]))
    ctrl = []
    for i in range(4):
        a = mk({d: 3 for d in SCALES})
        for j, d in enumerate(SCALES):        # 每【维】一个来源，四主体共用
            a["dims"][d]["source"] = "矩阵(M%d 档案)" % j
            a["dims"][d]["text"] = "cell"
        ctrl.append(a)
    check("（对照）每维一个来源、四主体共用 ⇒ 倍数 = 主体数 4.0",
          abs(ledger(ctrl)["pseudo_replication_matrix"] - 4.0) < 1e-9,
          str(ledger(ctrl)["pseudo_replication_matrix"]))

    print("\n【D｜同源对账：两个方向都要能报 ❌】")
    dup = []
    for i in range(3):
        a = mk({"存在方式": 4, "秩序价值": 5})
        for d in ("存在方式", "秩序价值"):
            a["dims"][d]["source"] = "矩阵(US 档案)"
            a["dims"][d]["text"] = "山巅之城/制度实验/例外论"
        dup.append(a)
    found = derived_duplicates(dup)
    check("数据里扫得出同源对（存在方式↔秩序价值）",
          ("秩序价值", "存在方式") in found or ("存在方式", "秩序价值") in found, str(dict(found)))
    saved = dict(DUPLICATE_OF)
    DUPLICATE_OF.clear()
    probs = reconcile_duplicates(dup)
    check("★改【账本】：清空声明 ⇒ 必须报『数据里同源、账本没声明』",
          len(probs) == 1 and "没声明" in probs[0][0], str(probs))
    DUPLICATE_OF["不存在的A"] = "不存在的B"
    probs2 = reconcile_duplicates(dup)
    check("★改【数据】：声明了一对扫不出来的 ⇒ 必须报『声明了但扫不出』",
          any("扫不出" in p[0] for p in probs2), str(probs2))
    DUPLICATE_OF.clear()
    DUPLICATE_OF.update(saved)
    probs3 = reconcile_duplicates(dup)
    check("还原声明后 ⇒ 两边一致（无 ❌）", probs3 == [], str(probs3))

    print("\n【E｜指纹：同内容同哈希、改一字节必变】")
    check("同内容 ⇒ 同哈希", fnv1a32(b"abc") == fnv1a32(b"abc"))
    check("改一字节 ⇒ 哈希必变", fnv1a32(b"abc") != fnv1a32(b"abd"))
    check("空串也稳定", fnv1a32(b"") == fnv1a32(b""))

    print("\n【F｜真产物上复算一遍（不是只测合成品）】")
    real = collect()
    j = judge_dimension("方向扩张性", real)
    check("真数据：方向扩张性应判 ok（≥3 种取值）", j["level"] == "ok", j["verdict"])
    check("真数据：合格维度数 = 1（同源重复那一根）", audit_bad_count(real) == 1,
          str(audit_bad_count(real)))

    print("\n" + "=" * 92)
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    if n_fail:
        print("  ❌ 审计有断言不成立 ⇒ 不能当结论用。")
    else:
        print("  ✅ 全部植入缺陷都被抓到 ⇒ 审计不是永远绿灯的摆设。")
    print("=" * 92)
    return 0 if n_fail == 0 else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if "--gate" in sys.argv:
        return gate()

    fp = fingerprints()
    # ── TaoPaw 的 stampHeader()：戳打在第一行 —— 重定向抓走的输出也能拿到 ──
    print(fp["encoder"])
    print("%s ｜ %s ｜ git %s" % (fp["corpus"], fp["scales"], fp["git"]))

    actors = collect()
    if "--audit" not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump({"fingerprint": fp, "scales": SCALES, "duplicate_of": DUPLICATE_OF,
                       "ledger": ledger(actors), "actors": actors},
                      fh, ensure_ascii=False, indent=2)
        print("已写出 %s（%d 主体）" % (os.path.relpath(OUT, ROOT), len(actors)))
    return 0 if audit(actors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
