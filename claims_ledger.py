# -*- coding: utf-8 -*-
"""claims_ledger.py —— 把 6 份规划文档的「声称」收成一本【可核、且会过期】的账

★★ 为什么要有它
  把这 6 份文档连起来看，这个项目的轨迹是清楚的：

    06-19  路线图 v2.0      最大难点是【认知框架是否成立】＋三道可证伪判据
    06-22  发展规划 v3.0    Phase 0 ✅「超额完成」；验证类产出【全部未启动】
    06-26  完成内容与版本迭代 【每一行都是 ✅】
    06-26  Engine v5.0 迁移  转向基础设施
    07-24  数据层 + Phase0   转向数据栈
    07-30  新定位           转向复杂系统认知基础设施

  ⇒ 从 06-22 起「✅」越来越多，而 v2.0 那三道阈值越来越远。

  共同的形状：**一份声明，和真实产物，两者从不互相对照。**
  不是有人撒谎 —— 是【一份满 ✅ 的清单 ＋ 没有任何检查器 = 谁都不必面对那个问题】。

  所以本账只做一件事：**每条声称都配一条机器可跑的核对规则，状态由机器算，不由人打。**

★★ 与 inventory_check.py 的关系
  那个只核了 06-26 一份清单。本账把【6 份文档】的声称收在一起，并多加一列：
  **指纹** —— 账本身会随产物变化而失效（照 eightdim.py 的指纹/新鲜度闸门那套规矩）。

运行：  python claims_ledger.py            # 算状态并写 data/claims-ledger.json
        python claims_ledger.py --gate     # 不重算，只比对已落盘账与新事实 ⇒ 有没有漂移
        python claims_ledger.py --selftest
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
LEDGER = os.path.join(HERE, "data", "claims-ledger.json")

# ══ 声称登记表 ══════════════════════════════════════════════════════════════════
# 每条：id / 来源文档 / 原文摘句 / 核对规则 / 人工备注
# 核对规则 kind：
#   path     —— 该路径存在？
#   find     —— 按名（子串）在全工作区找，可选 under 限定
#   count    —— 统计匹配某模式的文件数，与阈值比
#   doc_text —— 在 docs/ 全集中搜一个模式（用于「这件事有没有被记录下来」这类核对）
#   semantic —— 机器核不了，标 ℹ️ 并把该问的问题写出来
DOC_V2 = "# ConStruct · 发展路线图 v2.0.txt"
DOC_V3 = "ConStruct_发展规划_v3.0.md"
DOC_INV = "ConStruct 项目 · 完成内容与版本迭代（2026.06.26）.md"
DOC_V5 = "ConStruct_Engine_v5.0_迁移路线图.md"
DOC_DATA = "ConStruct_Phase0_验证指南.md"
DOC_0730 = "ConStruct Lab：复杂系统结构化认知基础设施项目.txt"
DOC_FOUND = "## 全球地缘政治认知引擎项目开发计划书（V1.0）.txt"
DOC_ENG = "## ConStruct Engine · 系统设计文档v1.0.txt"
DOC_CWKB3 = "ConStruct World Model Knowledge Base（CWKB）v3.0.txt"

C = [
    # ══ 立项文档（06-19/06-20）设计的东西，建了没有 ══════════════════════════════
    #   这一组是本账【最要紧】的部分：它们全是「记录失败／记录反例／限时验证」的构件。
    dict(id="F-1", doc=DOC_ENG, quote="SQLite是唯一的数据真相源。Markdown永远是从SQLite生成的",
         kind="find", term="schema.sql",
         note="立项设计把 SQLite 定为唯一真相源。版本演进.md 后来明写存储其实是 JSON 文件。"),
    dict(id="F-2", doc=DOC_FOUND, quote="Prediction Graveyard 预测坟场：记录失败预测／误判原因／模型修正",
         kind="find", term="graveyard",
         note="★ 这是立项时就设计的【失败账本】—— 全工程零命中。"),
    dict(id="F-3", doc=DOC_FOUND, quote="Counterexample Library 反例库：表象与本质不一致案例",
         kind="find", term="counterexample",
         note="★ 立项时就设计的【反例账本】—— 零命中。"),
    dict(id="F-4", doc=DOC_CWKB3, quote="Strategic Playbook Library 战略剧本库（v3.0 最值钱的动态数据库）",
         kind="find", term="playbook"),
    dict(id="F-5", doc=DOC_CWKB3, quote="Layer 8 约束层／Layer 9 激励层／Layer 10 战略目标层",
         kind="find", term="Constraint",
         note="找 x_Constraint.yaml 一类文件。ConStruct_Archive 下只有 Tier1/2/3 + Scenarios + References。"),
    dict(id="F-6", doc="## ConStruct Lab · 全球地缘政治知识库建设方案.txt",
         quote="知识库六层（Layer1 理论 … Layer6 主体档案），总预估约10天完成MVP",
         kind="find", term="construct-knowledge-base"),
    dict(id="F-7", doc=DOC_ENG, quote="Phase 2：引擎核心 + 美国30天实验",
         kind="doc_text", pattern=r"30\s*天实验.{0,40}(完成|已跑|跑完|结果|结论|命中)",
         note="★ 立项时【唯一一个有时限、可证伪的活体协议】。用【结果的形态】搜"
              "（「30天实验…完成/结果」），不是判据措辞。0 命中 ⇒ 未见跑过的记录。"),
    # ══ CWKB_Vault 的实况（06-26，43 文件）—— v3.0「Phase 1 日本 MVP」的落地 ══════
    dict(id="CV-1", doc=DOC_CWKB3, quote="Phase 1（2周）：日本MVP（概念+档案+约束+激励+目标+剧本）",
         kind="count",
         pattern=["**/CWKB_Vault/08_Constraint/*.md", "**/CWKB_Vault/09_Incentive/*.md",
                  "**/CWKB_Vault/10_Objectives/*.md"],
         under=None, threshold=3,
         note="08/09/10 三层各有「日本.md」⇒ 日本 MVP 确实做了。"),
    dict(id="CV-2", doc=DOC_CWKB3, quote="约束/激励/目标三层应覆盖主要大国（Phase 2：美中欧俄）",
         kind="count",
         pattern=["**/CWKB_Vault/08_Constraint/*.md", "**/CWKB_Vault/09_Incentive/*.md",
                  "**/CWKB_Vault/10_Objectives/*.md"],
         under=None, threshold=47,
         note="★ 阈值按主体总数 47 算。实测只有日本 1 个主体 × 3 层 ⇒ 建了首条就停了。"),
    dict(id="CV-3", doc=DOC_FOUND, quote="Prediction Graveyard：记录失败预测／误判原因／模型修正",
         kind="count", pattern="**/CWKB_Vault/Special/Prediction_Graveyard/*.md", under=None,
         threshold=10,
         note="★ 坟场的意义是【持续记录失败】。实测 1 条（俄罗斯经济半年崩溃）⇒ 有首条，未成库。"),
    dict(id="CV-4", doc=DOC_FOUND, quote="Counterexample Library：表象与本质不一致案例",
         kind="count", pattern="**/CWKB_Vault/Special/Counterexamples/*.md", under=None,
         threshold=10, note="实测 1 条（日本加息）。"),
    dict(id="CV-5", doc=DOC_CWKB3, quote="五大动态数据库（含 Event Chain / Strategy Timeline）",
         kind="count",
         pattern=["**/CWKB_Vault/Special/Event_Chains/*.md",
                  "**/CWKB_Vault/Special/Strategy_Timeline/*.md"],
         under=None, threshold=1, note="★ 这两个目录【空】。"),
    dict(id="CV-6", doc=DOC_CWKB3, quote="索引层（Index Layer）—— 知识层与引擎之间的枢纽",
         kind="count", pattern="**/CWKB_Vault/Indexes/*", under=None, threshold=1,
         note="★ 设计里的「索引层」是空的。"),
    dict(id="F-8", doc=DOC_ENG, quote="rules/ 每个主体一份 signal + del 规则（US/EU/Japan…）",
         kind="count", pattern="**/rules/*.json", under="construct-engine", threshold=47,
         note="★ 设计是【每个主体一份】；实测 rules/ 只有 5 个文件（CN/JP/RU/US/USA）⇒ 覆盖 4/47。"),
    dict(id="F-9", doc=DOC_CWKB3, quote="（新增）CWKB_v3.0_source.txt 与 CWKB v3.0.txt 是否同一份",
         kind="dup", a="ConStruct World Model Knowledge Base（CWKB）v3.0.txt",
         b="CWKB_v3.0_source.txt",
         note="两文件字节完全相同（同一 SHA256）⇒ 同一份文档两个名字。"
              "版本演进.md 已记过一次同类：磁盘上 v1.2 有两份。"),
    # ── v2.0 的三道可证伪判据：最要紧的一组 ──
    # ★ 模式必须找【结果的形态】（"命中率 = 58%"），不能找【判据的形态】（"命中率 > 65%"）。
    #   第一版我用的是判据措辞，于是必然命中重述判据的那几份文档，永远显示 ✅。
    dict(id="V2-1", doc=DOC_V2, quote="框架在50%以上事件上解释失效，则需修正框架设计",
         kind="doc_text", pattern=r"解释率\s*[:=＝]|解释失效\s*\d|失效\s*\d+\s*%",
         note="找【结果的形态】（如「解释率 = X%」）。搜不到 ⇒ 这道判据从未被执行过。"),
    dict(id="V2-2", doc=DOC_V2, quote="信号识别准确率低于60%，则需修正信号规则库",
         kind="doc_text", pattern=r"信号(识别)?准确率\s*[:=＝]\s*\d|准确率\s*[:=＝]\s*\d",
         note="v2.0 的 Phase 1 判据。需要 Signal Detector 已启动才有意义。"),
    dict(id="V2-3", doc=DOC_V2, quote="预测命中率超过65%",
         kind="doc_text", pattern=r"命中率\s*[:=＝]\s*\d",
         note="v2.0 的 Phase 2 判据。需要 Action Predictor 已启动才有意义。"),

    # ── v3.0 自认「未启动」的三项：现在启动了没有 ──
    dict(id="V3-1", doc=DOC_V3, quote="Signal Detector ❌ 未启动",
         kind="find", term="signal", under="construct-engine",
         note="限定在 construct-engine 下找（不限定会串到别的项目：实测命中了 CyberPPT 的图标）。"),
    dict(id="V3-2", doc=DOC_V3, quote="Action Predictor ❌ 未启动",
         kind="find", term="predict", under="construct-engine",
         note="限定在 construct-engine 下找有没有名为 predict* 的实现文件。"),
    dict(id="V3-3", doc=DOC_V3, quote="预测案例库 ❌ 未启动",
         kind="count", pattern="**/predict*.json", under=None, threshold=1,
         note="找有没有预测案例的落盘数据。"),

    # ── 06-26 清单的路径声称（inventory_check.py 已单独核过一遍）──
    dict(id="INV-1", doc=DOC_INV, quote="D:\\地缘推演台\\",
         kind="path", arg="D:\\地缘推演台", note="项目已搬到 D:\\Projects\\地缘推演台\\"),
    dict(id="INV-2", doc=DOC_INV, quote="construct_bridge.py", kind="find", term="construct_bridge.py"),
    dict(id="INV-3", doc=DOC_INV, quote="框架v2.0.html", kind="find", term="框架v2.0"),
    dict(id="INV-4", doc=DOC_INV, quote="框架v3.0.html（+SUL）", kind="find", term="框架v3.0"),
    dict(id="INV-5", doc=DOC_INV, quote="ConStruct_Archive/", kind="find", term="ConStruct_Archive"),
    dict(id="INV-6", doc=DOC_INV, quote="References/", kind="find", term="References",
         under="ConStruct_Archive"),
    dict(id="INV-7", doc=DOC_INV, quote="*公众号排版.html 8篇", kind="count",
         pattern="**/*公众号排版*.html", under="content", threshold=8),

    # ── v5.0 迁移路线图的 Phase 0/1 产出 ──
    dict(id="V5-1", doc=DOC_V5, quote="产出: docker-compose.yml 文件",
         kind="find", term="docker-compose.yml"),
    dict(id="V5-2", doc=DOC_V5, quote="0.6 PostgreSQL + TimescaleDB 启动 / create_hypertable",
         kind="find", term="init-pg.sql"),
    dict(id="V5-3", doc=DOC_V5, quote="0.11 Neo4j 导入 46 主体 → MATCH (a:Actor) count 46",
         kind="find", term="init-neo4j.cypher"),
    dict(id="V5-4", doc=DOC_V5, quote="0.10 写 healthcheck.sh — 挨个轮询 /health",
         kind="find", term="healthcheck"),
    dict(id="V5-5", doc=DOC_V5, quote="Phase 1: GDELT 管道 python pipeline.py --gdelt-only",
         kind="find", term="collect_gdelt.py"),

    # ── 数据层 / Phase0 验证指南 ──
    dict(id="D-1", doc=DOC_DATA, quote="phase0.bat verify（六步）",
         kind="find", term="phase0.bat"),
    dict(id="D-2", doc=DOC_DATA, quote="每条事件带 source_ref + confidence + verification_status=pending",
         kind="find", term="verify_events.py",
         note="该文件确实在 construct-stack/scripts/ 里。"),
    dict(id="D-3", doc=DOC_DATA, quote="数据流（GDELT 采集）→ 真相源（PG+TSDB）→ 图谱（Neo4j）核心链条跑通",
         kind="semantic",
         question="「跑通」是谁在什么时候验的？有没有留下一次性可复跑的凭据（脚本输出/日志/指纹）？"),

    # ── 07-30 新定位的声称 ──
    dict(id="N-1", doc=DOC_0730, quote="ConStruct 100 — 100个高质量案例",
         kind="count", pattern="**/data/cases/*.json", under="construct-engine", threshold=100,
         note="★ 实测只有 1 份（CS_FIN_2026_002_case_card.json）⇒ 距 100 还差 99。"),
    dict(id="N-2", doc=DOC_0730, quote="让任何案例都可以被机器读取（Case JSON Schema V1.0）",
         kind="find", term="case_schema_check.py",
         note="对账器已建；实测真案例卡 10 个 schema 字段里缺 9 个。"),
    dict(id="N-3", doc=DOC_0730, quote="核心资产：ConStruct Annotation Framework（实体/状态/关系/动态 四层）",
         kind="semantic",
         question="四层标注体系目前只是文档里的四段话，还是已经有可机读的定义（schema/枚举/校验器）？"),

    # ── 跨文档：新定位把旧构件丢掉了没有 ──
    dict(id="X-1", doc=DOC_0730, quote="（反查）新定位文档里还提不提八维/构型/结构诊断",
         kind="doc_text", pattern=r"八维|构型|结构诊断", only=DOC_0730, expect_zero=True,
         note="反查型：命中 0 次【就是】要确认的结论（实测 0 次）。"),
]


# ══ 核对引擎 ════════════════════════════════════════════════════════════════════
def _glob(pattern, under: str | None) -> list:
    """pattern 可以是【一个字符串或一串字符串】。
    ★ 为什么要支持列表：Python 的 glob 【不支持】花括号展开（`{a,b}` 是 bash 语法）。
      我第一版写了 `0[89]_*`（漏掉 10_Objectives）和 `{Event_Chains,Strategy_Timeline}`
      （被当成字面量）—— 前者报了假数字，后者【碰巧】结果正确但机制是错的。
    """
    pats = pattern if isinstance(pattern, (list, tuple)) else [pattern]
    base = os.path.join(ROOT, under) if under else ROOT
    out = []
    for pat in pats:
        for p in glob.glob(os.path.join(base, pat), recursive=True):
            if "node_modules" in p or "\\.git\\" in p:
                continue
            r = os.path.relpath(p, ROOT)
            if r not in out:
                out.append(r)
    return sorted(out)


def find_by_name(term: str, under: str | None = None) -> list:
    """★ 必须同时找【文件与目录】—— 只找文件会让 ConStruct_Archive/ 这种目录被误报零命中
    （我第一版就是只判 isfile，于是两个确实存在的目录被报 ⛔）。

    ★ 必须【忽略大小写】—— 第二版我用的是大小写敏感的 `in`，于是：
        术语 "graveyard" 匹配不到目录 `Prediction_Graveyard`
        术语 "counterexample" 匹配不到目录 `Counterexamples`
        术语 "playbook" 匹配不到目录 `Playbooks`
      三个【确实存在】的东西被报成 ⛔ 零命中。这是本检查器最危险的一个 bug ——
      它会让整份结论反向。修法是 .lower()。
    """
    t = term.lower()
    return [p for p in _glob("**/*", under) if t in os.path.basename(p).lower()]


def count_in_text(text: str, pattern: str) -> int:
    """在一个文本里数模式的命中数。抽出来是为了【可自证】：
    「判据的形态」与「结果的形态」必须能被分开检验。"""
    return len(re.findall(pattern, text))


def doc_text_count(pattern: str, only: str | None = None, exclude: str | None = None) -> int:
    """在 docs/ 里搜模式。
    ★ 必须能【排除声称自己的来源文档】—— 否则搜「判据的措辞」必然搜到写下它的那份文档，
      于是「判据有没有被执行」永远显示 ✅。这是本检查器第一版最严重的假阳性。
    """
    files = [os.path.join(DOCS, only)] if only else sorted(glob.glob(os.path.join(DOCS, "*")))
    n = 0
    for p in files:
        if not os.path.isfile(p):
            continue
        if exclude and os.path.basename(p) == exclude:
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                n += count_in_text(fh.read(), pattern)
        except OSError:
            pass
    return n


def evaluate(c: dict) -> dict:
    """算一条声称的【当下状态】。判定：✅ 成立 ／ ⚠️ 部分 ／ ⛔ 不成立 ／ ℹ️ 机器核不了。"""
    k = c["kind"]
    if k == "path":
        ok = os.path.exists(c["arg"])
        return {"status": "✅" if ok else "⛔", "evidence": c["arg"] if ok else "该路径不存在"}
    if k == "find":
        hits = find_by_name(c["term"], c.get("under"))
        if hits:
            at_root = [h for h in hits if os.sep not in h]
            return {"status": "✅" if at_root else "⚠️",
                    "evidence": "、".join(hits[:3]) + ("…" if len(hits) > 3 else "")}
        return {"status": "⛔", "evidence": "零命中"}
    if k == "count":
        n = len(_glob(c["pattern"], c.get("under")))
        th = c["threshold"]
        st = "✅" if n >= th else ("⚠️" if n else "⛔")
        return {"status": st, "evidence": "%d / 阈值 %d" % (n, th)}
    if k == "doc_text":
        # ★ 排除声称自己的来源文档：搜「判据的措辞」必然会搜到写下它的那一份，
        #   那样「判据有没有被执行」就永远显示 ✅ —— 这是第一版最严重的假阳性。
        n = doc_text_count(c["pattern"], c.get("only"), exclude=c["doc"])
        if c.get("expect_zero"):
            # 反查型声称：命中 0 次【就是】要确认的结论
            return {"status": "✅" if n == 0 else "⚠️",
                    "evidence": "docs/（除本文档外）命中 %d 处%s"
                                % (n, "　⇒ 结论成立" if n == 0 else "　⇒ 结论不成立，别处提过")}
        return {"status": "⚠️" if n == 0 else "✅",
                "evidence": "docs/（除本文档外）命中 %d 处%s" % (n, "　⇒ 【未见任何结果记录】" if n == 0 else "")}
    if k == "dup":
        pa, pb = os.path.join(DOCS, c["a"]), os.path.join(DOCS, c["b"])
        if not (os.path.isfile(pa) and os.path.isfile(pb)):
            return {"status": "⛔", "evidence": "至少一份不存在"}
        ha = hashlib.sha256(open(pa, "rb").read()).hexdigest()[:16]
        hb = hashlib.sha256(open(pb, "rb").read()).hexdigest()[:16]
        if ha == hb:
            return {"status": "⚠️", "evidence": "两份【字节完全相同】（%s）⇒ 重复文件" % ha}
        return {"status": "✅", "evidence": "两份不同（%s vs %s）" % (ha, hb)}
    return {"status": "ℹ️", "evidence": "机器核不了"}


def claim_fingerprint(c: dict) -> str:
    """单条声称的指纹：核对规则变了，指纹就变（照 eightdim 的规矩）。"""
    payload = json.dumps({k: c.get(k) for k in
                          ("id", "kind", "arg", "term", "pattern", "under", "threshold", "only")},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def compute() -> dict:
    rows = []
    for c in C:
        r = evaluate(c)
        rows.append({"id": c["id"], "doc": c["doc"], "quote": c["quote"],
                     "kind": c["kind"], "fingerprint": claim_fingerprint(c),
                     "status": r["status"], "evidence": r["evidence"],
                     "note": c.get("note") or c.get("question")})
    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    return {"claims": rows, "tally": tally,
            "ledger_print": hashlib.sha256(
                json.dumps([(r["id"], r["status"], r["fingerprint"]) for r in rows],
                           ensure_ascii=False).encode("utf-8")).hexdigest()[:12]}


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    cur = compute()
    if "--gate" in sys.argv:
        print("─" * 92)
        print("# 声称账 · 漂移闸门（比对已落盘账 与 当前事实）")
        print("─" * 92)
        if not os.path.exists(LEDGER):
            print("  ❌ 未找到账 %s —— 先跑 python claims_ledger.py" % os.path.relpath(LEDGER, ROOT))
            return 1
        with open(LEDGER, encoding="utf-8") as fh:
            old = json.load(fh)
        o = {r["id"]: r for r in old["claims"]}
        drift = 0
        for r in cur["claims"]:
            a = o.get(r["id"])
            if not a:
                print("  ⚠️ %-6s 新增声称（老账里没有）" % r["id"])
                drift += 1
            elif a["status"] != r["status"]:
                print("  ❌ %-6s 状态漂移：%s → %s　%s"
                      % (r["id"], a["status"], r["status"], r["evidence"]))
                drift += 1
            elif a["fingerprint"] != r["fingerprint"]:
                print("  ⚠️ %-6s 核对规则改了（指纹 %s → %s）"
                      % (r["id"], a["fingerprint"], r["fingerprint"]))
                drift += 1
        print("─" * 92)
        if drift:
            print("  ⛔ 有 %d 条漂移 ⇒ 老账不能再当证据用。重跑 python claims_ledger.py。" % drift)
            return 1
        print("  ✅ 无漂移：%d 条声称全部与落盘账一致。" % len(cur["claims"]))
        return 0

    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, ensure_ascii=False, indent=2)

    print("=" * 92)
    print("# 6 份规划文档 · 声称账（状态由机器算，不由人打）")
    print("=" * 92)
    print("\n  %-7s %-4s %-46s %s" % ("id", "", "声称", "证据"))
    print("  " + "-" * 86)
    for r in cur["claims"]:
        print("  %-7s %-4s %-46s %s" % (r["id"], r["status"], r["quote"][:46], r["evidence"]))
    print("  " + "-" * 86)
    print("  " + "　".join("%s %d" % (k, v) for k, v in sorted(cur["tally"].items())))
    print("  账指纹 = %s　→ %s" % (cur["ledger_print"], os.path.relpath(LEDGER, ROOT)))

    sem = [r for r in cur["claims"] if r["status"] == "ℹ️"]
    if sem:
        print("\n  ── 机器核不了的（要人判）")
        for r in sem:
            print("\n  · %s　%s" % (r["id"], r["quote"][:60]))
            print("      %s" % r["note"])

    print("\n" + "=" * 92)
    print("  这张账的意义")
    print("=" * 92)
    print("  · 它把 6 份文档的声称收在【一处】，且状态是【算出来的】—— 不是谁打的 ✅。")
    print("  · 每条声称带【指纹】：核对规则一改，--gate 立刻报漂移。")
    print("  · 于是「已完成」从此会【过期】—— 这正是 06-26 那份清单缺的那一列。")
    print("=" * 92)
    return 0


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

    print("# claims_ledger 自证")
    check("path：存在的路径 ⇒ ✅",
          evaluate({"kind": "path", "arg": ROOT})["status"] == "✅")
    check("path：不存在的路径 ⇒ ⛔",
          evaluate({"kind": "path", "arg": os.path.join(ROOT, "__nope__")})["status"] == "⛔")
    check("find：存在的文件 ⇒ ✅ 或 ⚠️（移位）",
          evaluate({"kind": "find", "term": "eightdim.py"})["status"] in ("✅", "⚠️"))
    check("find：零命中 ⇒ ⛔ 且证据写「零命中」",
          evaluate({"kind": "find", "term": "__nope__"})["evidence"] == "零命中")
    check("count：阈值 1 且确有一份 ⇒ ✅",
          evaluate({"kind": "count", "pattern": "**/data/cases/*.json",
                    "under": "construct-engine", "threshold": 1})["status"] == "✅")
    check("★count：阈值 100 而只有 1 份 ⇒ ⚠️【部分】（不是 ⛔）—— ConStruct 100 的真实现状",
          evaluate({"kind": "count", "pattern": "**/data/cases/*.json",
                    "under": "construct-engine", "threshold": 100})["status"] == "⚠️")
    check("count：一份都没有 ⇒ ⛔",
          evaluate({"kind": "count", "pattern": "**/__nope__/*.json", "threshold": 1})["status"] == "⛔")
    check("★find 必须能找到【目录】（只判 isfile 会把 ConStruct_Archive 误报零命中）",
          any(os.path.basename(h) == "ConStruct_Archive" for h in find_by_name("ConStruct_Archive")),
          str(find_by_name("ConStruct_Archive")[:2]))
    # ★ 大小写：第二版在这里翻过车 —— 小写术语匹配不到大驼峰目录
    check("★find 忽略大小写：小写 graveyard 能找到 Prediction_Graveyard",
          any("Graveyard" in h for h in find_by_name("graveyard")),
          str(find_by_name("graveyard")[:2]))
    check("★find 忽略大小写：小写 counterexample 能找到 Counterexamples",
          any("Counterexample" in h for h in find_by_name("counterexample")),
          str(find_by_name("counterexample")[:2]))
    check("★find 忽略大小写：小写 playbook 能找到 Playbooks",
          any("Playbook" in h for h in find_by_name("playbook")),
          str(find_by_name("playbook")[:2]))
    # ★ 判据 vs 结果：这两个字符串必须被区别对待，否则「判据有没有被执行」永远 ✅
    crit = "验证标准：预测命中率 > 65%"
    res = "实测命中率 = 58%"
    pat = r"命中率\s*[:=＝]\s*\d"
    check("★判据的形态（「命中率 > 65%」）⇒ 不算结果", count_in_text(crit, pat) == 0,
          str(count_in_text(crit, pat)))
    check("★结果的形态（「命中率 = 58%」）⇒ 才算结果", count_in_text(res, pat) == 1,
          str(count_in_text(res, pat)))
    check("doc_text：默认【排除本文档】—— 搜判据措辞不会搜到写下它的那一份",
          doc_text_count(r"框架在50%以上事件上解释失效", exclude=DOC_V2) == 0,
          str(doc_text_count(r"框架在50%以上事件上解释失效", exclude=DOC_V2)))
    check("doc_text：搜不到 ⇒ ⚠️（判据从未被记录）",
          evaluate({"kind": "doc_text", "pattern": r"绝不可能出现的字符串XYZQ",
                    "doc": "X.md"})["status"] == "⚠️")
    check("doc_text：搜得到 ⇒ ✅",
          evaluate({"kind": "doc_text", "pattern": r"ConStruct", "doc": "X.md"})["status"] == "✅")
    check("★doc_text + expect_zero：0 命中 ⇒ ✅（反查型，语义是反的）",
          evaluate({"kind": "doc_text", "pattern": r"绝不可能XYZQ", "doc": "X.md",
                    "expect_zero": True})["status"] == "✅")
    check("doc_text + expect_zero：有命中 ⇒ ⚠️",
          evaluate({"kind": "doc_text", "pattern": r"ConStruct", "doc": "X.md",
                    "expect_zero": True})["status"] == "⚠️")
    check("semantic ⇒ ℹ️（不冒充机器判）",
          evaluate({"kind": "semantic"})["status"] == "ℹ️")
    # dup：同内容 ⇒ ⚠️（重复文件）；不同内容 ⇒ ✅
    cw3 = "ConStruct World Model Knowledge Base（CWKB）v3.0.txt"
    cw2 = "ConStruct World Model Knowledge Base（CWKB）v2.0.txt"
    check("★dup：两份字节相同 ⇒ ⚠️ 重复文件",
          evaluate({"kind": "dup", "a": cw3, "b": "CWKB_v3.0_source.txt"})["status"] == "⚠️")
    check("★dup：两份不同 ⇒ ✅",
          evaluate({"kind": "dup", "a": cw3, "b": cw2})["status"] == "✅")
    check("dup：文件不存在 ⇒ ⛔",
          evaluate({"kind": "dup", "a": "__nope__", "b": cw2})["status"] == "⛔")
    # ★ glob 支持【列表】（Python glob 不展开花括号，所以多模式必须靠列表）
    n1 = len(_glob(["**/CWKB_Vault/08_Constraint/*.md", "**/CWKB_Vault/09_Incentive/*.md",
                    "**/CWKB_Vault/10_Objectives/*.md"], None))
    check("★glob 列表：08+09+10 三层合计命中 3 份（单模式 0[89]_* 只能命中 2）",
          n1 == 3, str(n1))
    n2 = len(_glob(["**/CWKB_Vault/Special/Event_Chains/*.md",
                    "**/CWKB_Vault/Special/Strategy_Timeline/*.md"], None))
    check("★glob 列表：两个空目录合计 0（花括号写法会静默变 0，结果同但机制错）",
          n2 == 0, str(n2))
    # 指纹两个方向
    a = {"id": "T", "kind": "find", "term": "abc"}
    b = {"id": "T", "kind": "find", "term": "abc"}
    c2 = {"id": "T", "kind": "find", "term": "abd"}
    check("指纹：同规则 ⇒ 同指纹", claim_fingerprint(a) == claim_fingerprint(b))
    check("★指纹：改核对规则 ⇒ 指纹必变", claim_fingerprint(a) != claim_fingerprint(c2))
    check("真账能算出来且条数 > 20", len(compute()["claims"]) > 20,
          str(len(compute()["claims"])))
    check("真账里确实含 V2-1（v2.0 的第一道判据）",
          any(r["id"] == "V2-1" for r in compute()["claims"]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
