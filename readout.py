# -*- coding: utf-8 -*-
"""readout.py —— 给「方向扩张性」配一个【独立测出来的】读出口

═══ 为什么必须做这一步（TaoPaw §9.6 §2 门槛 ⑦）═══════════════════════════════
八维的值 ≡ 其证据（构型矩阵单元格）的【确定性函数】：
    值 = match_scale(维度, 那个单元格的文本)
⇒ 统计量与它的零点【共用同一个估计量】⇒ 零分辨率。
   换句话说：拿八维的值去「验证」八维的矩阵，等于拿同一份数据自证。

要过第 ⑦ 条，只有一条路：**另找一个不是同一份数据的量**，看它是否随该维度改变。

═══ 外部量从哪来 ═══════════════════════════════════════════════════════════
`actor_timelines/*.json` 的 `skeleton_cow` —— 29 个主体、约 5.5 千条事件段，
来源是 COW MID 5.0 / COW 领土变更 / Kaggle War Records(HCED v2) / UCDP。
它与八维的构型矩阵【没有任何共同来源】，是独立测出来的。

读出口候选（全部来自同一份外部骨架，但三个不同侧面）：
  R1 领土净变化 = TERR_GAIN − TERR_LOSS          ← 扩张／收缩最直接的测量
  R2 近期对外争端 = type ∈ {MID, WAR} 且 year_end ≥ 2000
  R3 领土变更总数 = TERR_GAIN + TERR_LOSS

运行：  python readout.py            # 出结论
        python readout.py --selftest # 数学部分自证（Spearman / 置换零分布）
"""
from __future__ import annotations

import glob
import json
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AXES = os.path.join(HERE, "data", "eightdim.json")
TIMELINES = os.path.join(HERE, "actor_timelines")

# ISO3（时间线用的码） → 主体文件夹码（八维用的码）
ISO3_TO_ACTOR = {
    "USA": "US", "CHN": "CN", "RUS": "RU", "JPN": "JP", "DEU": "DE", "FRA": "FR",
    "GBR": "GB", "IND": "IN", "IRN": "IR", "ISR": "IL", "EGY": "EG", "PAK": "PK",
    "KOR": "KR", "VNM": "VN", "TWN": "TW", "SGP": "SG", "SAU": "SA", "TUR": "TR",
    "BRA": "BR", "CAN": "CA", "MEX": "MX", "PHL": "PH", "PRK": "KP", "SRB": "RS",
    "UKR": "UA", "AUS": "AUS", "ITA": "IT", "ESP": "ES", "IRQ": "IQ",
}

RECENT_FROM = 2000
RECENT_TERR_FROM = 1990

# ── 口径对账：外部量覆盖到哪一年 vs 轴值声明的是哪一年 ───────────────────────
# ★★ 这是一条【我上一轮漏掉】的检查，也是本步最重要的产出。
#    上一轮我拿 R2 的 p=0.276 判「幂够 ⇒ 效应不在那里」——
#    但我【没有查外部量覆盖到哪一年】。实测：COW MID 5.0 止于 2014，
#    而档案声明的「当前方向基线」是 2026 年的判断 ⇒ 错位 12 年。
#    统计功效够 ≠ 构造有效。「量错了东西 + 功效足够」会稳定地报出「无效应」，
#    而那个「无效应」对框架【不构成证据】——它只证明这两份数据对不上。
AXIS_TIME = 2026        # actors/*/「当前方向基线」= 2026 年的判断
TOLERANCE_Y = 3         # 允许的错位年数
READOUT_WINDOW = {
    "R1_terr_net": ("COW Territorial Change v6", 2015),
    "R2_recent_dispute": ("COW MID 5.0", 2014),
    "R3_terr_total": ("COW Territorial Change v6", 2015),
    "R4_recent_terr_net": ("COW Territorial Change v6", 2015),
    # ★ 第 6 步新增：UCDP GED v26.1 覆盖到 2025 ⇒ 与 2026 的轴值口径对齐（错位 1 年）
    "R5_ucdp_abroad": ("UCDP GED v26.1", 2025),
    "R6_ucdp_trend": ("UCDP GED v26.1", 2025),
    "R7_ucdp_home": ("UCDP GED v26.1", 2025),
}


def source_coverage() -> dict:
    """按来源统计覆盖年限 —— 口径对账的事实基础。"""
    by = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(TIMELINES, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        for s in d.get("skeleton_cow") or []:
            src = s.get("source") or "(无 source 字段)"
            by[src].append(s.get("year_end") or s.get("year_start") or 0)
    return {k: {"n": len(v), "min": min(v), "max": max(v)} for k, v in by.items()}


def caliber_check(key: str, axis_time: int = AXIS_TIME, tol: int = TOLERANCE_Y) -> dict:
    """读出口的窗口末端 vs 轴值声明时点 ⇒ 错位年数 ⇒ 合格／不合格。"""
    src, end = READOUT_WINDOW[key]
    lag = axis_time - end
    return {"key": key, "source": src, "window_end": end,
            "axis_time": axis_time, "lag": lag, "ok": lag <= tol}


# ── 外部量：从 COW 骨架算读出口 ─────────────────────────────────────────────
def readouts() -> dict:
    out = {}
    for path in sorted(glob.glob(os.path.join(TIMELINES, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        code = d.get("code") or os.path.basename(path)[:-5]
        sk = d.get("skeleton_cow") or []
        agg = Counter()
        recent = 0
        gain_r = loss_r = 0
        for s in sk:
            t = s.get("type")
            agg[t] += 1
            if t in ("MID", "WAR") and (s.get("year_end") or 0) >= RECENT_FROM:
                recent += 1
            if t in ("TERR_GAIN", "TERR_LOSS") and (s.get("year_end") or 0) >= RECENT_TERR_FROM:
                if t == "TERR_GAIN":
                    gain_r += 1
                else:
                    loss_r += 1
        gain, loss = agg["TERR_GAIN"], agg["TERR_LOSS"]
        out[ISO3_TO_ACTOR.get(code, code)] = {
            "cow_code": code, "episodes": len(sk),
            "TERR_GAIN": gain, "TERR_LOSS": loss,
            "R1_terr_net": gain - loss,
            "R2_recent_dispute": recent,
            "R3_terr_total": gain + loss,
            # R4 是【看到 R1 符号反了之后】才加的 —— 属探索性，不是预登记
            "R4_recent_terr_net": gain_r - loss_r,
            "MID": agg["MID"], "WAR": agg["WAR"], "ALLIANCE": agg["ALLIANCE"],
        }
    return out


# ── 统计：Spearman ＋ 置换零分布（不引第三方库）─────────────────────────────
def ranks(xs: list[float]) -> list[float]:
    """平均秩（并列取平均）。"""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranks(xs), ranks(ys))


def permutation_p(xs, ys, R=2000, seed=20261002) -> tuple[float, float]:
    """置换零分布：打乱 ys，看 |ρ| 能到多大。返回 (实测ρ, 双侧p)。"""
    rho = spearman(xs, ys)
    rng = random.Random(seed)
    sh = list(ys)
    ge = 0
    for _ in range(R):
        rng.shuffle(sh)
        if abs(spearman(xs, sh)) >= abs(rho) - 1e-12:
            ge += 1
    return rho, (ge + 1) / (R + 1)


POW_K = 7.849


def analyse() -> dict:
    with open(AXES, encoding="utf-8") as fh:
        ax = json.load(fh)
    axis_vals = {a["code"]: a["dims"]["方向扩张性"]["value"]
                 for a in ax["actors"]
                 if a["dims"]["方向扩张性"]["value"] is not None}
    ro = readouts()
    both = sorted(set(axis_vals) & set(ro))
    return {"axis_vals": axis_vals, "readouts": ro, "both": both,
            "n_timeline": len(ro), "n_axis": len(axis_vals)}


UCDP_PATH = os.path.join(HERE, "data", "ucdp_actors.json")


def ucdp_readouts() -> dict:
    """从 UCDP GED v26.1 聚合结果算读出口（覆盖到 2025 ⇒ 与 2026 的轴值口径对齐）。"""
    if not os.path.exists(UCDP_PATH):
        return {}
    with open(UCDP_PATH, encoding="utf-8") as fh:
        d = json.load(fh)
    out = {}
    for code, ys in d["actors"].items():
        def s(a, b, k="abroad"):
            return sum(ys.get(str(y), {}).get(k, 0) for y in range(a, b + 1))
        out[code] = {
            "R5_ucdp_abroad": s(2023, 2025),
            "R6_ucdp_trend": s(2023, 2025) - s(2020, 2022),
            "R7_ucdp_home": s(2023, 2025, "home"),
        }
    return out


# 读出口登记表：(显示名, 键, 是否新加)
READOUT_SPEC = [
    ("R1 领土净变化（全程）", "R1_terr_net"),
    ("R2 近期对外争端（≥2000）", "R2_recent_dispute"),
    ("R3 领土变更总数（全程）", "R3_terr_total"),
    ("R4 近期领土净变化（≥1990）⚠️探索性", "R4_recent_terr_net"),
    ("R5 UCDP 对外投射（2023-25）", "R5_ucdp_abroad"),
    ("R6 UCDP 对外投射趋势（23-25 减 20-22）", "R6_ucdp_trend"),
    ("R7 UCDP 本国境内（2023-25）〔对照〕", "R7_ucdp_home"),
]


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    A = analyse()
    ucdp = ucdp_readouts()
    for code, vals in ucdp.items():
        A["readouts"].setdefault(code, {}).update(vals)
    both = sorted(set(A["axis_vals"]) & set(A["readouts"]))
    A["both"] = both
    print("=" * 92)
    print("# 「方向扩张性」的读出口检验 —— 外部量：COW 骨架 ＋ UCDP GED v26.1")
    print("=" * 92)
    print("\n  八维里有方向扩张性值的主体：%d" % A["n_axis"])
    print("  COW 骨架覆盖：%d　UCDP 覆盖：%d" % (A["n_timeline"], len(ucdp)))
    print("  ★ 可用于检验的 n（至少有一个读出口）= %d" % len(both))

    if len(both) < 5:
        print("\n  ⛔ n < 5，做不了检验。")
        return 1

    print("\n  ── 逐主体（方向值 ／ R2 ／ R5 对外投射 ／ R7 本国）")
    print("     %-6s %6s %8s %10s %10s" % ("主体", "方向", "R2", "R5", "R7"))
    for c in both:
        r = A["readouts"][c]
        print("     %-6s %6d %8s %10s %10s"
              % (c, A["axis_vals"][c], r.get("R2_recent_dispute", "—"),
                 r.get("R5_ucdp_abroad", "—"), r.get("R7_ucdp_home", "—")))

    print("\n  ── 各读出口 × 「方向扩张性」（★ n 逐个算：UCDP 覆盖稀疏，不许混用）")
    verdicts = {}
    for name, key in READOUT_SPEC:
        cs = [c for c in both if key in A["readouts"][c]]
        if len(cs) < 6:
            print("\n     %s　n=%d ⇒ 样本太少，跳过" % (name, len(cs)))
            continue
        xs = [A["axis_vals"][c] for c in cs]
        ys = [A["readouts"][c][key] for c in cs]
        if len(set(xs)) < 2:
            print("\n     %s　轴值恒定 ⇒ 无区分力，跳过" % name)
            continue
        rho, p = permutation_p(xs, ys)
        groups = defaultdict(list)
        for v, y in zip(xs, ys):
            groups[v].append(y)
        means = {v: sum(g) / len(g) for v, g in sorted(groups.items())}
        sd = (sum((y - sum(ys) / len(ys)) ** 2 for y in ys) / max(1, len(ys) - 1)) ** 0.5
        cal = caliber_check(key) if key in READOUT_WINDOW else None
        print("\n     %s" % name)
        print("       n = %d　主体：%s" % (len(cs), "、".join(cs)))
        print("       分组均值 %s" % " ／ ".join("方向%d: %.2f" % (v, m) for v, m in means.items()))
        print("       Spearman ρ = %+.3f　置换 p = %.3f（R=2000）　噪声底 sd = %.2f" % (rho, p, sd))
        hi = [m for v, m in means.items() if v == 4]
        lo = [m for v, m in means.items() if v == 2]
        n_need = None
        if hi and lo and hi[0] != lo[0] and sd > 0:
            delta = abs(hi[0] - lo[0])
            n_need = POW_K * (sd / delta) ** 2
            print("       Δ(方向4−方向2) = %.2f ⇒ n_需 ≈ %.0f　n_有 = %d ⇒ %s"
                  % (delta, n_need, len(cs), "够" if len(cs) >= n_need else "**这一版测不了**"))
        if cal:
            print("       口径：%s 窗口末 %s ⇒ 错位 %d 年 ⇒ %s"
                  % (cal["source"], cal["window_end"], cal["lag"],
                     "✅ 合格（p 值可当证据）" if cal["ok"] else "⛔ 不合格（p 值不能当证据）"))
        verdicts[name] = {"rho": rho, "p": p, "sd": sd, "n": len(cs),
                          "n_need": n_need, "caliber_ok": bool(cal and cal["ok"])}

    print("\n  ── 负对照：把【全部八根轴】都对 R2（近期对外争端）跑一遍")
    print("     （TaoPaw §4.5：「正 / 负对照 ⛔ 不许省」——没有对照，任何相关性都不可信）")
    with open(AXES, encoding="utf-8") as fh:
        axd = json.load(fh)
    any_sig = []
    for dim in axd["scales"]:
        vals = {a["code"]: a["dims"][dim]["value"] for a in axd["actors"]
                if a["dims"][dim]["value"] is not None}
        cs = sorted(set(vals) & set(A["readouts"]))
        if len(cs) < 8:
            print("     %-12s n=%2d ⇒ 样本太少，跳过" % (dim, len(cs)))
            continue
        x = [vals[c] for c in cs]
        if len(set(x)) < 2:
            print("     %-12s 取值恒定 ⇒ 无区分力，跳过" % dim)
            continue
        y = [A["readouts"][c]["R2_recent_dispute"] for c in cs]
        rho, p = permutation_p(x, y)
        if p < 0.05:
            any_sig.append(dim)
        print("     %-12s n=%2d  ρ=%+.3f  p=%.3f  %s"
              % (dim, len(cs), rho, p, "★显著" if p < 0.05 else "不显著"))
    print("     ⇒ 八根轴里能显著预测「近期对外争端」的：%s"
          % ("、".join(any_sig) if any_sig else "**一根都没有**"))

    print("\n" + "=" * 92)
    print("  口径对账：外部量覆盖到哪一年 vs 轴值声明的是哪一年")
    print("=" * 92)
    print("\n  %-34s %7s %7s %7s" % ("source", "条数", "最早", "最晚"))
    cov = source_coverage()
    for src, c in sorted(cov.items(), key=lambda kv: -kv[1]["n"]):
        print("  %-34s %7d %7d %7d" % (src[:34], c["n"], c["min"], c["max"]))
    print("\n  轴值声明的时点 = %d（档案「当前方向基线」）　容差 = ±%d 年"
          % (AXIS_TIME, TOLERANCE_Y))
    print("\n  %-22s %-28s %6s %8s %s" % ("读出口", "来源", "窗口末", "错位", "判定"))
    cal = {}
    print("\n  %-38s %-26s %6s %7s %s" % ("读出口", "来源", "窗口末", "错位", "判定"))
    for name, key in READOUT_SPEC:
        if key not in READOUT_WINDOW:
            continue
        c = caliber_check(key)
        cal[key] = c
        print("  %-38s %-26s %6d %6d年 %s"
              % (name[:38], c["source"][:26], c["window_end"], c["lag"],
                 "✅ 合格" if c["ok"] else "⛔ 错位过大"))
    ok_keys = [k for k, c in cal.items() if c["ok"]]
    bad_keys = [k for k, c in cal.items() if not c["ok"]]

    print("\n" + "=" * 92)
    print("  结论")
    print("=" * 92)
    if bad_keys:
        print("  ⛔ 口径不合格（p 值【不能当证据用】）：%s" % "、".join(bad_keys))
        print("     —— 这正是上一轮（§9.2）我据 p=0.276 判「效应不在那里」时漏掉的那一步。")
    if ok_keys:
        print("  ✅ 口径合格（p 值可当证据）：%s" % "、".join(ok_keys))

    m = len(verdicts)
    if m:
        print("\n  比较了 %d 个读出口 ⇒ Bonferroni 阈值 = 0.05/%d = %.4f" % (m, m, 0.05 / m))
    usable = {k: v for k, v in verdicts.items() if v["caliber_ok"]}
    if not usable:
        print("\n  ⛔ **没有一个【口径合格】的读出口 ⇒ 这一版仍然测不了。**")
        return 2
    print("\n  ── 只看【口径合格】的读出口")
    for name, v in usable.items():
        mark = "★显著" if v["p"] < 0.05 else "不显著"
        print("     %-40s ρ=%+.3f  p=%.3f  n=%d  %s"
              % (name[:40], v["rho"], v["p"], v["n"], mark))
        if v["n_need"]:
            print("        n_需 ≈ %.0f　n_有 = %d ⇒ %s"
                  % (v["n_need"], v["n"], "够" if v["n"] >= v["n_need"] else "不足"))
    sig = [k for k, v in usable.items() if v["p"] < 0.05]
    bonf = [k for k, v in usable.items() if v["p"] < 0.05 / max(1, m)]
    print("\n  未校正 p<0.05：%s" % ("、".join(sig) if sig else "**一个都没有**"))
    print("  Bonferroni 后仍显著：%s" % ("、".join(bonf) if bonf else "**一个都没有**"))

    # ── 留一法：ρ 会不会只由【一个主体】撑着？ ─────────────────────────────
    key_of = {nm: k for nm, k in READOUT_SPEC}
    print("\n  ── 留一法（drop-one）稳健性：这个 ρ 靠几个主体撑着？")
    for name, v in usable.items():
        key = key_of.get(name)
        cs = [c for c in both if key in A["readouts"][c]]
        if len(cs) < 5:
            continue
        base = v["rho"]
        worst = None
        for drop in cs:
            sub = [c for c in cs if c != drop]
            xs2 = [A["axis_vals"][c] for c in sub]
            ys2 = [A["readouts"][c][key] for c in sub]
            if len(set(xs2)) < 2:
                continue
            r2_, _ = permutation_p(xs2, ys2, R=0)      # 只要 rho
            if worst is None or abs(r2_ - base) > abs(worst[1] - base):
                worst = (drop, r2_)
        if worst:
            print("     %-40s ρ=%+.3f　去掉 %s 后 ρ=%+.3f　（Δ=%+.3f）"
                  % (name[:40], base, worst[0], worst[1], worst[1] - base))

    if not sig:
        powered = [k for k, v in usable.items()
                   if v["n_need"] and v["n"] >= v["n_need"]]
        strong = [k for k in powered
                  if verdicts[k]["n"] >= 1.5 * (verdicts[k]["n_need"] or 1)]
        marginal = [k for k in powered if k not in strong]
        if strong:
            print("\n  ⇒ 有【功效充分】(n ≥ 1.5·n_需) 的口径合格读出口：%s" % "、".join(strong))
            print("     ⇒ 可以判「**没有可检出的效应**」。")
        if marginal:
            print("\n  ⇒ 有【功能只是边缘】(n 仅略大于 n_需) 的口径合格读出口：%s" % "、".join(marginal))
            print("     ⇒ 只能判「**证据不足**」—— ⛔ 不许说成「证明无效」，")
            print("        也不许因为 ρ 看着大就说成「有效应」。")
        if not powered:
            print("\n  ⇒ 口径合格但【功效都不足】⇒ 仍属「这一版测不了」，不是「没有效应」。")
    return 0 if sig else 1
    best = max(verdicts.items(), key=lambda kv: abs(kv[1]["rho"]))
    print("  最强的一个：%s，ρ = %+.3f，p = %.3f，n = %d"
          % (best[0], best[1]["rho"], best[1]["p"], best[1]["n"]))
    print()
    print("  ⚠️ 边界（不许含糊）")
    print("   · 这是【外部量是否随维度改变】的检验，不是「维度正确」的检验。")
    print("   · COW 骨架与八维矩阵来源不同 ⇒ 这一步【能】回答第 ⑦ 条；")
    print("     但它只给一根轴配了读出口，其余七根仍然没有。")
    print("   · n = %d 是【主体数】，不是观测数 —— 与八维账本同一条纪律：" % len(both))
    print("     一个主体只算一格，不许把它的多条冲突事件当多个样本。")
    print("=" * 92)
    return 0 if sig else 1


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

    print("=" * 92)
    print("# 读出口模块 · 自证")
    print("=" * 92)
    check("ranks 并列取平均秩", ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0],
          str(ranks([10, 20, 20, 30])))
    check("spearman 完全单调 ⇒ +1", abs(spearman([1, 2, 3, 4], [5, 6, 7, 8]) - 1.0) < 1e-9)
    check("spearman 完全反调 ⇒ −1", abs(spearman([1, 2, 3, 4], [8, 7, 6, 5]) + 1.0) < 1e-9)
    check("pearson 常数序列 ⇒ 0（不是 NaN）", pearson([1, 1, 1], [2, 3, 4]) == 0.0)
    # 置换检验：真相关必须显著、纯噪声必须不显著
    xs = [4, 4, 3, 3, 2, 2, 4, 3]
    ys = [10, 9, 5, 6, 1, 2, 11, 4]
    _rho, p = permutation_p(xs, ys)
    check("植入强相关 ⇒ p < 0.05", p < 0.05, "p=%.3f" % p)
    rng = random.Random(7)
    noise = [rng.random() for _ in xs]
    _r2, p2 = permutation_p(xs, noise)
    check("纯噪声 ⇒ p 不显著（>0.05）", p2 > 0.05, "p=%.3f" % p2)
    check("置换检验可复现（同种子同结果）",
          permutation_p(xs, ys)[0] == permutation_p(xs, ys)[0])
    r = readouts()
    check("读出口覆盖 29 个主体", len(r) == 29, str(len(r)))
    check("R1 = TERR_GAIN − TERR_LOSS（结构与定义一致）",
          all(v["R1_terr_net"] == v["TERR_GAIN"] - v["TERR_LOSS"] for v in r.values()))
    # ── 口径对账（★ 本步新加，两个方向都证）──
    c = caliber_check("R2_recent_dispute")
    check("★口径：轴值 2026 vs COW MID 止于 2014 ⇒ 错位 12 年 ⇒ 不合格",
          c["lag"] == 12 and not c["ok"], str(c))
    c_ok = caliber_check("R2_recent_dispute", axis_time=2015)
    check("★口径：把轴值时点改到 2015 ⇒ 错位 1 年 ⇒ 合格（门是可过的）",
          c_ok["ok"], str(c_ok))
    c_tol = caliber_check("R2_recent_dispute", axis_time=2016, tol=2)
    check("★口径：2016／容差 2 ⇒ 错位 2 年 ⇒ 刚好合格",
          c_tol["lag"] == 2 and c_tol["ok"], str(c_tol))
    cov = source_coverage()
    check("★口径：COW MID 5.0 的最大年确实是 2014",
          cov.get("COW MID 5.0", {}).get("max") == 2014, str(cov.get("COW MID 5.0")))
    check("★口径：全部来源合起来最新不超过 2020",
          max(v["max"] for v in cov.values()) <= 2020,
          str(max(v["max"] for v in cov.values())))
    print("\n  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    print("=" * 92)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
