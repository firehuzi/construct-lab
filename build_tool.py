# -*- coding: utf-8 -*-
"""build_tool.py —— 组装 ConStruct Lab 新工具（引擎/工具层）

★★ 目标（用户定的方向）
   新版 = 「结构诊断工具」的下一版，**历史回溯是它的一个板块**。
   基座 = construct-lab-site/public/diagnostic-tool.html
          （81 KB，线上 construct-lab.web.app/tool 的来源。
           它已含早先审计 F20 的「档案导入通道」修复；
           而 content/published/地缘政治分析框架v2.1.html 是【旧快照】——
           同一个 <title>，小 11 KB。别再拿它当基座。）

★★ 为什么历史回溯走 iframe 而不是合并 JS
   两个工具都用 `state` 当主状态对象（硬冲突）；CSS 也冲突
   （历史回溯是深色主题，会覆盖诊断工具的配色）。
   ⇒ iframe 完全隔离，零风险。代价：板块② 是一个独立文件
     （tool/modules/backtest.html），不再是「单文件全包」。

★★ 数据内联
   引擎（Python）算 → 构建器内联进 HTML。理由：工具要能双击打开（file://），
   而 file:// 下浏览器不允许页面 fetch 同目录的 json（CORS）。
   ★ 判定逻辑全在引擎里，前端只显示 —— 免得同一件事有两套口径。

运行：  python build_tool.py            # 构建
        python build_tool.py --selftest
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)                      # 工作区根
DIAG = os.path.join(WS, "construct-lab-site", "public", "diagnostic-tool.html")
BACKTEST = os.path.join(HERE, "backtest-tool", "index.html")
OUT_DIR = os.path.join(HERE, "tool")
OUT = os.path.join(OUT_DIR, "index.html")
OUT_MOD = os.path.join(OUT_DIR, "modules")

MARK_A = "<!-- @@MODULE:diag:START@@ -->"
MARK_B = "<!-- @@MODULE:diag:END@@ -->"

ARCHIVE_DIRS = [os.path.join(WS, "ConStruct_Archive"), os.path.join(WS, "actors")]

MODULES = [("diag", "🔍 结构诊断"), ("backtest", "🧭 历史回溯"),
           ("ledger", "📒 排除断言账"), ("archive", "🗂 主体档案")]


# ══ 引擎侧 ══════════════════════════════════════════════════════════════════════
def ledger_data() -> dict:
    sys.path.insert(0, HERE)
    try:
        import exclusion_ledger as EL
    except Exception as e:                                   # noqa: BLE001
        return {"error": "无法导入 exclusion_ledger: %s" % e, "rows": [], "total": 0, "clean": 0}
    rows = EL.ingested_rows()
    tally = {}
    for r in rows:
        for f in (r.get("flags") or []):
            tally[f] = tally.get(f, 0) + 1
    bad = len([r for r in rows if (r.get("flags") or [])])
    return {"rows": rows, "tally": tally, "total": len(rows), "clean": len(rows) - bad,
            "problem_ratio": (bad / len(rows)) if rows else None,
            "thresholds": {"war_deaths": getattr(EL, "WAR_DEATH_THRESHOLD", None),
                           "war_source": getattr(EL, "WAR_THRESHOLD_SOURCE", ""),
                           "war_defined": getattr(EL, "WAR_THRESHOLD_DEFINED", "")}}


def archive_data() -> dict:
    items = []
    for d in ARCHIVE_DIRS:
        if not os.path.isdir(d):
            continue
        for p in sorted(glob.glob(os.path.join(d, "**", "*.md"), recursive=True)):
            rel = os.path.relpath(p, WS)
            parts = rel.replace("\\", "/").split("/")
            items.append({"name": os.path.splitext(os.path.basename(p))[0],
                          "tier": parts[1] if len(parts) > 2 else "",
                          "path": rel, "size": os.path.getsize(p)})
    return {"items": items, "count": len(items)}


def build_data() -> dict:
    return {"built_by": "build_tool.py", "base": os.path.relpath(DIAG, WS),
            "ledger": ledger_data(), "archive": archive_data()}


# ══ 组装 ════════════════════════════════════════════════════════════════════════
TABBAR = """
<!-- @@BUILD:tabbar@@ -->
<div id="mod-tabs" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;
     max-width:900px;margin:0 auto 14px;padding:10px 0;border-bottom:1px solid var(--cl-border,#ddd)">
  <button class="btn btn-primary" data-mod="diag" onclick="switchModule('diag')">🔍 结构诊断</button>
  <button class="btn" data-mod="backtest" onclick="switchModule('backtest')">🧭 历史回溯</button>
  <button class="btn" data-mod="ledger" onclick="switchModule('ledger')">📒 排除断言账</button>
  <button class="btn" data-mod="archive" onclick="switchModule('archive')">🗂 主体档案</button>
</div>
"""

EXTRA = """
<!-- @@BUILD:modules@@ 板块②③④ -->
<div id="mod-backtest" class="module" style="display:none">
  <div style="max-width:900px;margin:0 auto">
    <div class="node-desc" style="margin-bottom:8px">板块② 历史回溯 —— 时间锁推演：
      只看当时已知的信息做判断，<strong>提交后（锁定）才揭示历史</strong>。
      独立文件，与本页样式/状态完全隔离。</div>
    <iframe id="bt-frame" src="modules/backtest.html" style="width:100%;height:82vh;
      border:1px solid var(--cl-border,#ddd);border-radius:8px;background:#0a0a0a"></iframe>
  </div>
</div>
<div id="mod-ledger" class="module" style="display:none"></div>
<div id="mod-archive" class="module" style="display:none"></div>
"""

RUNTIME_JS = r"""
<script>
// ══════════════════════════════════════════════════════════════
// 新工具运行层：板块切换 + 账/档案渲染
// 数据由 build_tool.py 在构建时内联为 window.CONSTRUCT_DATA。
// ★ 判定逻辑【不在这里】—— 全在引擎（exclusion_ledger.py），这里只显示。
// ══════════════════════════════════════════════════════════════
(function () {
  var D = window.CONSTRUCT_DATA || null;
  var NAMES = { diag: '🔍 结构诊断', backtest: '🧭 历史回溯',
                ledger: '📒 排除断言账', archive: '🗂 主体档案' };

  function esc2(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  window.switchModule = function (mod) {
    ['diag', 'backtest', 'ledger', 'archive'].forEach(function (m) {
      var el = document.getElementById('mod-' + m);
      if (el) el.style.display = (m === mod) ? '' : 'none';
      var bt = document.querySelector('[data-mod="' + m + '"]');
      if (bt) bt.className = 'btn' + (m === mod ? ' btn-primary' : '');
    });
    if (mod === 'ledger') renderLedgerModule();
    if (mod === 'archive') renderArchiveModule();
    try { history.replaceState(null, '', '#' + mod); } catch (e) { }
  };

  window.renderLedgerModule = function () {
    var el = document.getElementById('mod-ledger');
    if (!el) return;
    var W = 'max-width:900px;margin:0 auto;';
    if (!D) { el.innerHTML = '<div style="' + W + '">构建数据缺失。</div>'; return; }
    var L = D.ledger || {};
    var h = '<div style="' + W + '">'
      + '<h2 style="margin:0 0 6px">📒 排除断言账</h2>'
      + '<div class="node-desc">「不可能发生什么」的断言 —— <strong>单向可证伪</strong>：'
      + '它发生了就证伪；它没发生<strong>只说明尚未被证伪</strong>，不等于被证实。'
      + '判定由引擎 <code>exclusion_ledger.py</code> 算，本页只显示。</div>';
    if (L.error) { el.innerHTML = h + '<p style="color:#c00">' + esc2(L.error) + '</p></div>'; return; }
    if (!L.total) {
      el.innerHTML = h + '<p>还没有记录。到「🧭 历史回溯」走一个场景、点「✔ 提交本次推演」，'
        + '把排除断言导出到 <code>data/exclusions/</code>，再重新构建。</p></div>';
      return;
    }
    h += '<p style="margin:12px 0 4px">共 <strong>' + L.total + '</strong> 条断言　·　'
      + '完全合格 <strong style="color:#2a7">' + L.clean + '</strong> 条　·　'
      + '有问题 <strong style="color:#c00">' + (L.total - L.clean) + '</strong> 条';
    if (L.problem_ratio != null) h += '　（有问题比例 <strong>' + Math.round(L.problem_ratio * 100) + '%</strong>）';
    h += '</p>';
    Object.keys(L.tally || {}).forEach(function (k) {
      h += '<div class="node-desc" style="font-size:0.7rem">· ' + esc2(k) + ' × ' + L.tally[k] + '</div>';
    });
    h += '<table style="width:100%;border-collapse:collapse;margin-top:14px;font-size:0.78rem">'
      + '<tr style="text-align:left;border-bottom:1px solid #ddd"><th style="padding:6px">场景</th>'
      + '<th style="padding:6px">排除的路径</th><th style="padding:6px">证伪条件</th>'
      + '<th style="padding:6px">窗口</th><th style="padding:6px">问题</th></tr>';
    (L.rows || []).forEach(function (r) {
      var fl = r.flags || [], bad = fl.length > 0;
      h += '<tr style="border-bottom:1px solid #eee;vertical-align:top">'
        + '<td style="padding:6px">' + esc2(r.scenario) + '</td>'
        + '<td style="padding:6px">' + esc2(r.excluded) + '</td>'
        + '<td style="padding:6px">' + (esc2(r.criterion) || '<span style="color:#c00">（缺）</span>') + '</td>'
        + '<td style="padding:6px">' + (esc2(r.window) || '<span style="color:#c00">未填</span>') + '</td>'
        + '<td style="padding:6px;color:' + (bad ? '#c00' : '#2a7') + '">'
        + (bad ? fl.map(function (x) { return esc2(x.split('（')[0]); }).join(' ＋ ')
               : '✅ 无（尚未被证伪）') + '</td></tr>';
    });
    h += '</table>';
    var T = L.thresholds || {};
    if (T.war_deaths) {
      h += '<div class="node-desc" style="margin-top:12px">预登记阈值：<strong>' + T.war_deaths
        + '</strong> —— ' + esc2(T.war_source) + '（冻结于 ' + esc2(T.war_defined) + '）</div>';
    }
    el.innerHTML = h + '</div>';
  };

  window.renderArchiveModule = function () {
    var el = document.getElementById('mod-archive');
    if (!el) return;
    var A = (D && D.archive) || { items: [], count: 0 }, byTier = {};
    (A.items || []).forEach(function (it) {
      var t = it.tier || '（未分层）'; byTier[t] = (byTier[t] || 0) + 1;
    });
    var h = '<div style="max-width:900px;margin:0 auto"><h2 style="margin:0 0 6px">🗂 主体档案</h2>'
      + '<div class="node-desc">构建时内联的档案索引，共 <strong>' + A.count + '</strong> 份。</div>';
    Object.keys(byTier).sort().forEach(function (t) {
      h += '<div class="node-desc" style="font-size:0.72rem">· ' + esc2(t) + '　' + byTier[t] + ' 份</div>';
    });
    h += '<div style="margin-top:12px;max-height:60vh;overflow:auto;font-size:0.75rem">';
    (A.items || []).forEach(function (it) {
      h += '<div style="padding:3px 0;border-bottom:1px solid #eee">' + esc2(it.name)
        + '　<span style="color:#999;font-size:0.68rem">' + esc2(it.path) + '</span></div>';
    });
    el.innerHTML = h + '</div></div>';
  };

  // 构建戳：用户三次导出都来自旧版而我们只能靠字段推断 ⇒ 把指纹印在脸上
  window.renderBuildStamp = function () {
    var el = document.getElementById('build-stamp');
    if (!el) return;
    el.innerHTML = '构建 <strong>' + (D ? D.built_by : '?') + '</strong>'
      + '　｜　基座：' + (D ? esc2(D.base) : '?')
      + '　｜　账内联 ' + ((D && D.ledger && D.ledger.total) || 0) + ' 条'
      + '　｜　档案内联 ' + ((D && D.archive && D.archive.count) || 0) + ' 份'
      + '　｜　<strong>若「🧭 历史回溯」标签点不开或账为空，说明你打开的是旧版</strong>';
  };
  window.renderBuildStamp();

  // 支持 #module 直达
  var h0 = (location.hash || '').replace('#', '');
  if (NAMES[h0]) window.switchModule(h0);
})();
</script>
"""


PERSIST_JS = r"""
<script>
// ══════════════════════════════════════════════════════════════
// 板块① 持久化：11 层填到一半关掉页面就没了（原来 localStorage 0 处）
// ══════════════════════════════════════════════════════════════
// ★ 恢复映射【不另维护一张表】—— 直接解析 DOM 自己的内联 handler：
//     onchange="updateState('L1_name','actor.name')"   ⇒ 元素 → state 路径
//     onchange="updateSUL('intent',this.value)"        ⇒ 滑块 → SUL 键
//     onclick ="selectRadio(this,'L1','continuity.type')" ⇒ 选项 → state 路径
//     onclick ="toggleCheck(this,'others')"            ⇒ 勾选 → state 分类
//   工具改了 HTML，映射自动跟着变 —— 不会漂移。
// ★ 为什么恢复必须走 selectRating 而不能只改 state：
//   createRatingButtons 把 1-3 硬编码为 active（默认值 3），不读 state。
//   所以只有调 selectRating 才会同时改 UI 与 state。
// ══════════════════════════════════════════════════════════════
(function () {
  var KEY = 'construct_diag_v1';
  var LS = (function () { try { return window.localStorage; } catch (e) { return null; } })();

  function getPath(o, p) {
    return String(p).split('.').reduce(function (a, k) {
      return (a == null) ? undefined : a[k];
    }, o);
  }
  function setPath(o, p, v) {
    var ks = String(p).split('.'), i;
    for (i = 0; i < ks.length - 1; i++) { if (o[ks[i]] == null) o[ks[i]] = {}; o = o[ks[i]]; }
    o[ks[ks.length - 1]] = v;
  }
  function deepMerge(dst, src) {
    Object.keys(src || {}).forEach(function (k) {
      var v = src[k];
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        if (dst[k] == null || typeof dst[k] !== 'object') dst[k] = {};
        deepMerge(dst[k], v);
      } else if (v !== undefined) { dst[k] = v; }
    });
  }

  // ── 保存 ──────────────────────────────────────────────────
  var timer = null;
  function snapshot() {
    var nameEl = document.getElementById('analysisName');
    return { v: 1, savedAt: new Date().toISOString(),
             name: nameEl ? nameEl.value : '',
             touched: (typeof __touched !== 'undefined') ? __touched : false,
             state: JSON.parse(JSON.stringify(state)) };
  }
  function save() {
    if (!LS) return false;
    try { LS.setItem(KEY, JSON.stringify(snapshot())); markSaved(); return true; }
    catch (e) { return false; }
  }
  function scheduleSave() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(save, 400);
  }
  function markSaved() {
    var el = document.getElementById('diag-persist-note');
    if (!el) return;
    var d = new Date();
    el.textContent = '💾 已保存到本机（' + d.toTimeString().slice(0, 8) + '）';
    el.style.color = '#2a7';
  }

  // ── 元素 → state 路径：通用提取器 ──────────────────────────
  // ★ 这里修过一轮：原来「一个 handler 一个正则」，实测漏掉两类 ——
  //   ① SUL 滑块用的是 oninput 而不是 onchange ⇒ 5 个键一个都解析不到
  //   ② 构型用的是 <select onchange="updateConfig(this.value)">，不是 selectRadio
  //   ③ 还有 onchange="state.config.label=this.value" 这种直接赋值
  //   漏掉的后果是【静默不恢复】（不报错，只是白填），所以改成通用提取器 + 覆盖全部模式。
  function handlerSrc(el) {
    return (el.getAttribute('onchange') || '') + ' '
         + (el.getAttribute('oninput') || '') + ' '
         + (el.getAttribute('onclick') || '');
  }
  function extract(el) {
    var s = handlerSrc(el), m;
    if ((m = /updateState\('([^']+)'\s*,\s*'([^']+)'\)/.exec(s))) return { path: m[2], via: 'state' };
    if ((m = /selectRadio\(this\s*,\s*'[^']*'\s*,\s*'([^']+)'\)/.exec(s))) return { path: m[1], via: 'radio' };
    if ((m = /updateSUL\('([^']+)'/.exec(s))) return { path: 'SUL.' + m[1], via: 'value' };
    if (/updateConfig\(/.test(s)) return { path: 'config.lockMode', via: 'value' };
    if ((m = /state\.([A-Za-z0-9_.]+)\s*=\s*this\.value/.exec(s))) return { path: m[1], via: 'value' };
    if ((m = /toggleCheck\(this\s*,\s*'([^']+)'/.exec(s))) return { path: m[1], via: 'check' };
    return null;
  }
  function fire(el) {
    try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) { }
    try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) { }
  }

  // ── 恢复 ──────────────────────────────────────────────────
  function restore() {
    var raw = LS && LS.getItem(KEY);
    if (!raw) return false;
    var saved;
    try { saved = JSON.parse(raw); } catch (e) { return false; }
    if (!saved || !saved.state) return false;

    deepMerge(state, saved.state);              // state 是 const ⇒ 只能合并，不能赋值
    try { if (typeof __touched !== 'undefined') __touched = !!saved.touched; } catch (e) { }

    // ① 评分组：走 selectRating（它同时改 UI 与 state）
    //    ★ 必须走 click —— createRatingButtons 把 1-3 硬编码为 active，不读 state
    document.querySelectorAll('.rating-group[data-path]').forEach(function (g) {
      var v = parseInt(getPath(state, g.dataset.path), 10);
      if (!(v >= 1 && v <= 5)) return;
      var btn = g.querySelector('.rating-btn[data-value="' + v + '"]');
      if (btn) btn.click();
    });
    // ② 其余控件：统一走提取器
    var stats = { radio: 0, check: 0, value: 0, skip: 0 };
    document.querySelectorAll('[onchange],[oninput],[onclick]').forEach(function (el) {
      if (el.classList && el.classList.contains('rating-btn')) return;
      var info = extract(el);
      if (!info) { stats.skip++; return; }
      var want = getPath(state, info.path);
      if (info.via === 'radio') {
        if (want != null && want !== '' && String(el.dataset.value) === String(want)) { el.click(); stats.radio++; }
        return;
      }
      if (info.via === 'check') {
        var cat = state[info.path];
        var w = !!(cat && el.dataset.key && cat[el.dataset.key]);
        if (w !== el.classList.contains('active')) { el.click(); stats.check++; }
        return;
      }
      // 文本 / 下拉 / 滑块
      if (want == null || want === '') return;
      if (String(el.value) === String(want)) return;
      el.value = want; fire(el); stats.value++;
    });
    try { window.__restoreStats = stats; } catch (e) { }

    // ③ 分析名称
    var nm = document.getElementById('analysisName');
    if (nm && saved.name) { nm.value = saved.name; }

    try { updateProgress(); diagnose(); } catch (e) { }
    return true;
  }

  // ── 接线 ──────────────────────────────────────────────────
  var restored = restore();

  // 任何改动都排一次保存（捕获阶段，覆盖动态生成的控件）
  ['input', 'change', 'click'].forEach(function (ev) {
    document.addEventListener(ev, function (e) {
      if (e.target && e.target.id === 'diag-clear-btn') return;
      scheduleSave();
    }, true);
  });
  window.addEventListener('beforeunload', function () { if (timer) clearTimeout(timer); save(); });

  // 状态条 + 清空
  function mountBar() {
    var host = document.querySelector('#mod-diag .app-container') || document.body;
    if (!host || document.getElementById('diag-persist-bar')) return;
    var bar = document.createElement('div');
    bar.id = 'diag-persist-bar';
    bar.style.cssText = 'max-width:900px;margin:0 auto 10px;display:flex;gap:10px;'
      + 'align-items:center;flex-wrap:wrap;font-size:0.7rem';
    bar.innerHTML = '<span id="diag-persist-note" class="node-desc">'
      + (restored ? '↩️ 已恢复上次填写的进度（本机保存）' : '💾 进度会自动保存在本机')
      + '</span>'
      + '<button class="btn" id="diag-clear-btn" style="font-size:0.68rem;padding:2px 8px">清空并重新开始</button>';
    host.insertBefore(bar, host.firstChild);
    document.getElementById('diag-clear-btn').onclick = function () {
      if (!confirm('清空本机保存的进度，并重新开始？此操作不可撤销。')) return;
      if (LS) LS.removeItem(KEY);
      location.reload();
    };
  }
  mountBar();
  if (restored) markSaved();
})();
</script>
"""


def build() -> tuple:
    with io.open(DIAG, encoding="utf-8") as fh:
        html = fh.read()
    if MARK_A not in html or MARK_B not in html:
        raise SystemExit("基座 %s 缺少板块锚点" % os.path.relpath(DIAG, WS))

    data = build_data()
    payload = json.dumps(data, ensure_ascii=False)

    # ① 标签栏放 <body> 之后（板块容器之外）
    html = html.replace("<body>", "<body>\n" + TABBAR + '<div id="mod-diag" class="module">', 1)
    # ② 板块① 结束后：闭合容器 + 插入板块②③④
    html = html.replace(MARK_B, MARK_B + "\n</div>" + EXTRA, 1)
    # ③ 构建戳：塞进 app-header 之后
    html = html.replace('<div class="subtitle">从事件到长期存在',
                        '<div class="subtitle">从事件到长期存在', 1)
    html = html.replace("</div>\n<div class=\"toolbar\">",
                        "</div>\n<div class=\"toolbar\">", 1)
    stamp = ('<div id="build-stamp" class="node-desc" style="font-size:0.66rem;margin-top:4px;opacity:.75"></div>')
    html = html.replace('<div class="toolbar">', stamp + '\n<div class="toolbar">', 1)
    # ④ 数据 + 运行层
    html = html.replace("<script>", "<script>window.CONSTRUCT_DATA=" + payload + ";</script>\n<script>", 1)
    html = html.replace("</body>", RUNTIME_JS + PERSIST_JS + "\n</body>", 1)
    html = html.replace("<title>", "<title>ConStruct Lab · 分析工具（构建产物） | ", 1)

    os.makedirs(OUT_MOD, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    # 板块②：历史回溯作为独立文件（iframe 隔离，避免 state / CSS 冲突）
    shutil.copyfile(BACKTEST, os.path.join(OUT_MOD, "backtest.html"))
    return data, len(html)


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    data, n = build()
    L, A = data["ledger"], data["archive"]
    print("=" * 86)
    print("# 组装 ConStruct Lab 新工具")
    print("=" * 86)
    print("  基座   %s" % os.path.relpath(DIAG, WS))
    print("  产物   %s（%.0f KB）" % (os.path.relpath(OUT, WS), n / 1024.0))
    print("         %s（板块②，iframe 隔离）"
          % os.path.relpath(os.path.join(OUT_MOD, "backtest.html"), WS))
    print("\n  板块① 🔍 结构诊断   基座原生（11 层 + SUL + 诊断 + 导出）")
    print("  板块② 🧭 历史回溯   独立文件 + iframe（避免 state/CSS 冲突）")
    print("  板块③ 📒 排除断言账 %d 条（完全合格 %d，有问题 %d）"
          % (L.get("total", 0), L.get("clean", 0), L.get("total", 0) - L.get("clean", 0)))
    for k, v in sorted((L.get("tally") or {}).items(), key=lambda kv: -kv[1]):
        print("       · %-46s %d" % (k, v))
    print("  板块④ 🗂 主体档案   %d 份" % A.get("count", 0))
    print("=" * 86)
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
    with io.open(DIAG, encoding="utf-8") as fh:
        base = fh.read()
    check("★基座是 diagnostic-tool.html（不是那个旧的 70KB 快照）",
          os.path.basename(DIAG) == "diagnostic-tool.html")
    check("★基座含早先审计 F20 的档案导入通道（证明它是新的那份）",
          "审计发现 F20" in base and "archivePick" in base)
    check("★基座有板块锚点且顺序正确",
          MARK_A in base and MARK_B in base and base.index(MARK_A) < base.index(MARK_B))
    old = os.path.join(WS, "content", "published", "地缘政治分析框架v2.1.html")
    if os.path.exists(old):
        with io.open(old, encoding="utf-8") as fh:
            olds = fh.read()
        check("★旧快照确实更小（81KB vs 70KB）—— 用它当基座会丢掉 F20 修复",
              len(base) > len(olds), "%d vs %d" % (len(base), len(olds)))
        check("★旧快照【没有】档案导入通道（所以它不能当基座）",
              "archivePick" not in olds)

    d = build_data()
    check("★引擎侧返回账数据", isinstance(d["ledger"], dict) and "rows" in d["ledger"])
    check("★引擎侧返回档案索引", isinstance(d["archive"], dict) and "items" in d["archive"])
    check("★账里带预登记阈值（阈值在引擎侧冻结）",
          d["ledger"]["thresholds"].get("war_deaths") == 1000)

    _, n = build()
    with io.open(OUT, encoding="utf-8") as fh:
        out = fh.read()
    bt = os.path.join(OUT_MOD, "backtest.html")
    check("★板块② 文件确实产出", os.path.exists(bt))
    if os.path.exists(bt):
        with io.open(bt, encoding="utf-8") as fh:
            bts = fh.read()
        check("★板块② 是完整的历史回溯工具（不是壳）",
              "commitBacktest" in bts and "renderExclusions" in bts and "criterionOverlap" in bts)
    check("★产物含内联数据", "window.CONSTRUCT_DATA=" in out)
    check("★产物含四个板块容器",
          all(('id="mod-' + m + '"') in out for m in ("diag", "backtest", "ledger", "archive")))
    check("★产物含标签栏与 switchModule", "mod-tabs" in out and "switchModule" in out)
    check("★产物含构建戳且脚本会渲染它",
          'id="build-stamp"' in out and "renderBuildStamp" in out)
    check("★板块① 是基座原件（诊断功能仍在）",
          "diagnose" in out and "renderDiagnosis" in out and "updateSUL" in out)
    check("★板块② 用 iframe 指向 modules/backtest.html",
          'id="bt-frame"' in out and 'src="modules/backtest.html"' in out)
    check("★标题标明构建产物", "构建产物" in out)
    check("★产物比基座大（确实注入了东西）", n > len(base), "%d vs %d" % (n, len(base)))
    m = re.search(r"window\.CONSTRUCT_DATA=(\{.*?\});</script>", out, re.S)
    check("★内联数据可解析回来", bool(m))
    if m:
        back = json.loads(m.group(1))
        check("★内联账条数与引擎一致", back["ledger"]["total"] == d["ledger"]["total"])
        check("★内联档案数与引擎一致", back["archive"]["count"] == d["archive"]["count"])
    check("★模块清单与文档一致（四个板块）",
          [m for m, _l in MODULES] == ["diag", "backtest", "ledger", "archive"])
    # ── 板块① 持久化 ──
    check("★产物含持久化脚本", "construct_diag_v1" in out)
    check("★持久化覆盖 5 类控件的恢复路径",
          all(k in out for k in ("selectRating", "selectRadio", "toggleCheck", "updateState", "updateSUL")))
    check("★恢复映射靠【解析 DOM 自己的内联 handler】，不另维护一张表",
          "getAttribute('onchange')" in out and "getAttribute('onclick')" in out)
    check("★用深合并而不是赋值（state 是 const，赋不了值）",
          "deepMerge(state, saved.state)" in out)
    check("★有清空入口（否则本机数据会把人锁死）", "diag-clear-btn" in out)
    check("★有保存状态提示（不然用户不知道存没存）", "diag-persist-note" in out)
    check("★beforeunload 时立即保存（不等防抖）", "beforeunload" in out)
    print("  自证：通过 %d，失败 %d" % (n_pass, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
