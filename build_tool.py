# -*- coding: utf-8 -*-
"""build_tool.py —— 把引擎的计算结果组装成一个【单文件】新版工具

★★ 为什么必须是单文件
  工具要能双击打开（file:// 直接跑，无需服务器）。而 file:// 下浏览器
  不允许页面加载同目录的其它 .js/.json（CORS）。所以：
    · 数据不能 fetch ⇒ 必须【内联】进 HTML
    · 模块不能拆成多个 .js ⇒ 必须拼进同一个 <script>
  这决定了架构：**引擎（Python）算 → 构建器内联 → 单文件交付**。

★★ 板块
  ① 历史回溯（时间锁推演）—— 源 = backtest-tool/index.html 里 @@MODULE:backtest@@ 之间的块
  ② 排除断言账 —— 源 = exclusion_ledger.ingested_rows()（每次构建时由引擎算）
  ③ 主体档案 —— 源 = ConStruct_Archive / actors 目录索引

  这三块的【判定逻辑都在引擎里】，前端只负责显示 —— 免得同一件事有两套口径。

运行：  python build_tool.py            # 构建 tool/index.html
        python build_tool.py --selftest
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                    # 工作区根
BASE = os.path.join(HERE, "backtest-tool", "index.html")
OUT_DIR = os.path.join(HERE, "tool")
OUT = os.path.join(OUT_DIR, "index.html")

MARK_A = "<!-- @@MODULE:backtest:START@@ -->"
MARK_B = "<!-- @@MODULE:backtest:END@@ -->"

ARCHIVE_DIRS = [os.path.join(ROOT, "ConStruct_Archive"),
                os.path.join(ROOT, "actors")]


# ══ 引擎侧：算数据 ══════════════════════════════════════════════════════════════
def ledger_data() -> dict:
    """调引擎算排除断言账 —— 前端不重算，只显示。"""
    sys.path.insert(0, HERE)
    try:
        import exclusion_ledger as EL
    except Exception as e:                                  # noqa: BLE001
        return {"error": "无法导入 exclusion_ledger: %s" % e, "rows": []}
    rows = EL.ingested_rows()
    # 每条记录的全部问题（不是只报第一个）+ 汇总
    out = []
    for r in rows:
        out.append({k: v for k, v in r.items()})
    tally = {}
    for r in rows:
        for f in (r.get("flags") or []):
            tally[f] = tally.get(f, 0) + 1
    return {
        "rows": out,
        "tally": tally,
        "total": len(rows),
        "clean": len(rows) - len([r for r in rows if (r.get("flags") or [])]),
        "problem_ratio": (len([r for r in rows if (r.get("flags") or [])]) / len(rows))
                          if rows else None,
        "thresholds": {
            "war_deaths": getattr(EL, "WAR_DEATH_THRESHOLD", None),
            "war_source": getattr(EL, "WAR_THRESHOLD_SOURCE", ""),
            "war_defined": getattr(EL, "WAR_THRESHOLD_DEFINED", ""),
        },
    }


def archive_data() -> dict:
    """主体档案索引。目录不在就返回空表（不报错 —— 工具在别处也能跑）。"""
    items = []
    for d in ARCHIVE_DIRS:
        if not os.path.isdir(d):
            continue
        for p in sorted(glob.glob(os.path.join(d, "**", "*.md"), recursive=True)):
            rel = os.path.relpath(p, ROOT)
            parts = rel.replace("\\", "/").split("/")
            items.append({"name": os.path.splitext(os.path.basename(p))[0],
                          "tier": parts[1] if len(parts) > 2 else "",
                          "path": rel,
                          "size": os.path.getsize(p)})
    return {"items": items, "count": len(items)}


def build_data() -> dict:
    return {"built_by": "build_tool.py",
            "ledger": ledger_data(),
            "archive": archive_data()}


# ══ 组装 ════════════════════════════════════════════════════════════════════════
TAB_BAR = """
  <!-- @@BUILD:tabbar@@ 由 build_tool.py 生成 -->
  <div id="mod-tabs" style="display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 6px;padding-bottom:12px;border-bottom:1px solid var(--border)">
    <button class="btn btn-primary" data-mod="backtest" onclick="switchModule('backtest')">🧭 历史回溯</button>
    <button class="btn" data-mod="ledger" onclick="switchModule('ledger')">📒 排除断言账</button>
    <button class="btn" data-mod="archive" onclick="switchModule('archive')">🗂 主体档案</button>
    <span style="flex:1"></span>
    <span class="hint" id="mod-tab-note" style="align-self:center;font-size:11px"></span>
  </div>
"""

MODULE_EXTRA = """
  <!-- @@BUILD:modules@@ 由 build_tool.py 生成（板块②③的容器） -->
  <div id="mod-ledger" class="module" style="display:none"></div>
  <div id="mod-archive" class="module" style="display:none"></div>
"""

RUNTIME_JS = r"""
<script>
// ══════════════════════════════════════════════════════════════
// 新版工具运行层：板块切换 + 账/档案的渲染
// 数据由 build_tool.py 在构建时内联为 window.CONSTRUCT_DATA。
// ★ 判定逻辑【不在这里】—— 全在引擎（exclusion_ledger.py）里，这里只显示。
// ══════════════════════════════════════════════════════════════
(function () {
  var D = (typeof window !== 'undefined' && window.CONSTRUCT_DATA) || null;

  window.switchModule = function (mod) {
    ['backtest', 'ledger', 'archive'].forEach(function (m) {
      var el = document.getElementById('mod-' + m);
      if (el) el.style.display = (m === mod) ? '' : 'none';
      var bt = document.querySelector('[data-mod="' + m + '"]');
      if (bt) bt.className = 'btn' + (m === mod ? ' btn-primary' : '');
    });
    var flow = document.getElementById('backtest-flow');
    var sel = document.getElementById('scenario-select');
    if (mod !== 'backtest') {
      if (flow) flow.style.display = 'none';
      if (sel) sel.style.display = 'none';
    } else if (sel && !currentBT) {
      sel.style.display = '';
      if (flow) flow.style.display = 'none';
    }
    if (mod === 'ledger') renderLedgerModule();
    if (mod === 'archive') renderArchiveModule();
    var note = document.getElementById('mod-tab-note');
    if (note) {
      note.textContent = (mod === 'ledger')
        ? '判定由引擎 exclusion_ledger.py 算，本页只显示'
        : (mod === 'archive' ? '档案索引由构建时内联' : '');
    }
  };

  function esc2(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  window.renderLedgerModule = function () {
    var el = document.getElementById('mod-ledger');
    if (!el) return;
    if (!D) { el.innerHTML = '<div class="panel"><h3>📒 排除断言账</h3><div class="hint">构建数据缺失。</div></div>'; return; }
    var L = D.ledger || {};
    if (L.error) { el.innerHTML = '<div class="panel"><h3>📒 排除断言账</h3><div class="hint" style="color:var(--danger)">' + esc2(L.error) + '</div></div>'; return; }
    var h = '<div class="panel"><h3>📒 排除断言账</h3>'
      + '<div class="hint">「不可能发生什么」的断言 —— <strong>单向可证伪</strong>：它发生了就证伪；'
      + '它没发生【只说明尚未被证伪】，不说明被证实。判定由引擎算，本页只显示。</div>';
    if (!L.total) {
      h += '<div class="hint" style="margin-top:10px">还没有记录。到「🧭 历史回溯」里走一个场景、'
        + '点「✔ 提交本次推演」并把排除断言导出到 <code>data/exclusions/</code>，再重新构建。</div></div>';
      el.innerHTML = h; return;
    }
    h += '<div style="margin-top:10px;font-size:13px">共 <strong>' + L.total + '</strong> 条断言　·　'
      + '完全合格 <strong style="color:var(--accent)">' + L.clean + '</strong> 条　·　'
      + '有问题 <strong style="color:var(--danger)">' + (L.total - L.clean) + '</strong> 条';
    if (L.problem_ratio != null) {
      h += '　（有问题比例 <strong style="color:' + (L.problem_ratio > 0 ? 'var(--danger)' : 'var(--accent)')
        + '">' + Math.round(L.problem_ratio * 100) + '%</strong>）';
    }
    h += '</div>';
    Object.keys(L.tally || {}).forEach(function (k) {
      h += '<div class="hint" style="font-size:11px">· ' + esc2(k) + ' × ' + L.tally[k] + '</div>';
    });
    h += '<table style="width:100%;border-collapse:collapse;margin-top:14px;font-size:12px">'
      + '<tr style="color:var(--dim);text-align:left"><th style="padding:6px">场景</th>'
      + '<th style="padding:6px">排除的路径</th><th style="padding:6px">证伪条件</th>'
      + '<th style="padding:6px">窗口</th><th style="padding:6px">问题</th></tr>';
    (L.rows || []).forEach(function (r) {
      var fl = r.flags || [];
      var bad = fl.length > 0;
      h += '<tr style="border-top:1px solid var(--border);vertical-align:top">'
        + '<td style="padding:6px">' + esc2(r.scenario) + '</td>'
        + '<td style="padding:6px">' + esc2(r.excluded) + '</td>'
        + '<td style="padding:6px">' + (esc2(r.criterion) || '<span style="color:var(--danger)">（缺）</span>') + '</td>'
        + '<td style="padding:6px">' + (esc2(r.window) || '<span style="color:var(--danger)">未填</span>') + '</td>'
        + '<td style="padding:6px;color:' + (bad ? 'var(--danger)' : 'var(--accent)') + '">'
        + (bad ? fl.map(function (x) { return esc2(x.split('（')[0]); }).join(' ＋ ')
               : '✅ 无（尚未被证伪）') + '</td></tr>';
    });
    h += '</table>';
    var T = L.thresholds || {};
    if (T.war_deaths) {
      h += '<div class="hint" style="margin-top:12px">预登记阈值：<strong>' + T.war_deaths + '</strong> —— '
        + esc2(T.war_source) + '（冻结于 ' + esc2(T.war_defined) + '）</div>';
    }
    h += '</div>';
    el.innerHTML = h;
  };

  window.renderArchiveModule = function () {
    var el = document.getElementById('mod-archive');
    if (!el) return;
    var A = (D && D.archive) || { items: [], count: 0 };
    var byTier = {};
    (A.items || []).forEach(function (it) {
      var t = it.tier || '（未分层）';
      byTier[t] = (byTier[t] || 0) + 1;
    });
    var h = '<div class="panel"><h3>🗂 主体档案</h3>'
      + '<div class="hint">构建时内联的档案索引，共 <strong>' + A.count + '</strong> 份。</div>';
    Object.keys(byTier).sort().forEach(function (t) {
      h += '<div class="hint" style="font-size:12px">· ' + esc2(t) + '　' + byTier[t] + ' 份</div>';
    });
    h += '<div style="margin-top:12px;max-height:420px;overflow:auto;font-size:12px">';
    (A.items || []).forEach(function (it) {
      h += '<div style="padding:3px 0;border-bottom:1px solid var(--border)">'
        + esc2(it.name) + '　<span style="color:var(--dim);font-size:11px">' + esc2(it.path) + '</span></div>';
    });
    h += '</div></div>';
    el.innerHTML = h;
  };

  // 构建数据缺失时也要给个说法，不静默
  if (!D) {
    var note = document.getElementById('mod-tab-note');
    if (note) note.textContent = '⚠️ 未找到内联数据（请用 build_tool.py 构建，不要直接改本文件）';
  }
})();
</script>
"""


def build() -> tuple:
    with io.open(BASE, encoding="utf-8") as fh:
        html = fh.read()
    if MARK_A not in html or MARK_B not in html:
        raise SystemExit("基座缺少板块锚点 %s / %s" % (MARK_A, MARK_B))

    data = build_data()
    payload = json.dumps(data, ensure_ascii=False)

    # ① 给板块① 包一层容器 + 在它前面插入标签栏
    html = html.replace(MARK_A, TAB_BAR + '  <div id="mod-backtest" class="module">\n' + MARK_A, 1)
    # ② 板块① 结束后插入 ②③ 的容器
    html = html.replace(MARK_B, MARK_B + "\n" + MODULE_EXTRA, 1)
    # ③ 注入数据 + 运行层：插在主脚本【之前】的数据，和 </body> 之前的运行层
    html = html.replace("<script>", "<script>window.CONSTRUCT_DATA=" + payload + ";</script>\n<script>", 1)
    html = html.replace("</body>", RUNTIME_JS + "\n</body>", 1)
    # ④ 标题标明是构建产物
    html = html.replace("<title>地缘推演台 - 历史回溯版 V2</title>",
                        "<title>ConStruct Lab · 分析工具（构建产物）</title>", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    return data, len(html)


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    data, n = build()
    L, A = data["ledger"], data["archive"]
    print("=" * 84)
    print("# 构建新版工具 → %s" % os.path.relpath(OUT, ROOT))
    print("=" * 84)
    print("  输出 %s 字节（%.0f KB）" % ("{:,}".format(n), n / 1024.0))
    print("\n  板块① 历史回溯      源 = backtest-tool/index.html（已加板块锚点）")
    print("  板块② 排除断言账    %d 条（完全合格 %d，有问题 %d）"
          % (L.get("total", 0), L.get("clean", 0), L.get("total", 0) - L.get("clean", 0)))
    for k, v in sorted((L.get("tally") or {}).items(), key=lambda kv: -kv[1]):
        print("       · %-46s %d" % (k, v))
    print("  板块③ 主体档案      %d 份" % A.get("count", 0))
    print("\n  单文件自检：")
    print("    内联数据脚本   %s" % ("有" if "window.CONSTRUCT_DATA=" in io.open(OUT, encoding="utf-8").read() else "缺"))
    print("    外部依赖       %s" % ("无（可双击直接打开）"
          if not re.search(r'<script[^>]*\bsrc=', io.open(OUT, encoding="utf-8").read()) else "有"))
    print("=" * 84)
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

    print("# build_tool 自证")
    with io.open(BASE, encoding="utf-8") as fh:
        base = fh.read()
    check("★基座有板块锚点（没有锚点就没法组装）",
          MARK_A in base and MARK_B in base)
    check("★锚点顺序正确（START 在 END 之前）",
          base.index(MARK_A) < base.index(MARK_B))
    d = build_data()
    check("★引擎侧返回账数据（不是前端自己编的）",
          isinstance(d["ledger"], dict) and "rows" in d["ledger"])
    check("★引擎侧返回档案索引", isinstance(d["archive"], dict) and "items" in d["archive"])
    check("★账里带预登记阈值（阈值必须在引擎侧冻结）",
          "thresholds" in d["ledger"] and d["ledger"]["thresholds"].get("war_deaths") == 1000,
          str(d["ledger"].get("thresholds")))
    _, n = build()
    with io.open(OUT, encoding="utf-8") as fh:
        out = fh.read()
    check("★产物含内联数据", "window.CONSTRUCT_DATA=" in out)
    check("★产物无外部 script 依赖（单文件，可 file:// 打开）",
          not re.search(r'<script[^>]*\bsrc=', out))
    check("★产物含三个板块", all(('mod-' + m) in out for m in ("backtest", "ledger", "archive")))
    check("★产物含标签栏与切换函数", "switchModule" in out and "mod-tabs" in out)
    check("★板块① 是从基座搬过来的（不是重写）", "renderExclusions" in out and "commitBacktest" in out)
    check("★产物比基座大（确实注入了东西）", n > len(base), "%d vs %d" % (n, len(base)))
    check("★标题标明是构建产物", "构建产物" in out)
    # 反向：数据确实内联的是引擎算的值，不是空壳
    m = re.search(r"window\.CONSTRUCT_DATA=(\{.*?\});</script>", out, re.S)
    check("★内联数据能被解析回来", bool(m))
    if m:
        back = json.loads(m.group(1))
        check("★内联的账条数与引擎一致",
              back["ledger"]["total"] == d["ledger"]["total"],
              "%s vs %s" % (back["ledger"]["total"], d["ledger"]["total"]))
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
