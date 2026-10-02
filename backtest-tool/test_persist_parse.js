// 测【持久化的解析那一步】—— 这是唯一有真风险的地方：
// 恢复映射靠解析 DOM 自己的内联 handler，正则匹配不上就【静默不恢复】。
// 所以必须拿真实的基座 HTML 去验，而不是验我自己写的样例。
const fs = require("fs");
const path = require("path");

const WS = path.join(__dirname, "..", "..");
const DIAG = path.join(WS, "construct-lab-site", "public", "diagnostic-tool.html");
const base = fs.readFileSync(DIAG, "utf8");
let ok = true;
const ck = (n, c, d) => {
  if (c) console.log("  ✅ " + n);
  else { ok = false; console.log("  ❌ " + n + "   " + (d || "")); }
};

console.log("# 持久化 · 解析步骤（对着真实基座 " + path.basename(DIAG) + " 验）");

// ── 通用提取器：与 build_tool.py 的实现保持同一组模式 ──
function handlerSrc(tag) {
  const g = (n) => { const m = new RegExp('\\b' + n + '="([^"]*)"').exec(tag); return m ? m[1] : ''; };
  return g('onchange') + ' ' + g('oninput') + ' ' + g('onclick');
}
function extract(tag) {
  const s = handlerSrc(tag);
  let m;
  if ((m = /updateState\('([^']+)'\s*,\s*'([^']+)'\)/.exec(s))) return { path: m[2], via: 'state' };
  if ((m = /selectRadio\(this\s*,\s*'[^']*'\s*,\s*'([^']+)'\)/.exec(s))) return { path: m[1], via: 'radio' };
  if ((m = /updateSUL\('([^']+)'/.exec(s))) return { path: 'SUL.' + m[1], via: 'value' };
  if (/updateConfig\(/.test(s)) return { path: 'config.lockMode', via: 'value' };
  if ((m = /state\.([A-Za-z0-9_.]+)\s*=\s*this\.value/.exec(s))) return { path: m[1], via: 'value' };
  if ((m = /toggleCheck\(this\s*,\s*'([^']+)'/.exec(s))) return { path: m[1], via: 'check' };
  return null;
}

const tags = [...base.matchAll(/<(input|select|textarea|button)\b[^>]*>/g)].map(m => m[0]);
const found = { state: [], radio: [], value: [], check: [] };
tags.forEach(t => { const i = extract(t); if (i) found[i.via].push(i.path); });

ck("★updateState 解析出 ≥3 处（L1_name / L6_role / L10_strategy / L0_desc）",
   found.state.length >= 3, JSON.stringify(found.state));
ck("★selectRadio 解析出 ≥1 处（continuity.type，三个按钮同一路径）",
   found.radio.length >= 1, JSON.stringify(found.radio));
// ★ 这两条是修复前会失败的：SUL 用 oninput、构型用 updateConfig
ck("★★updateSUL 解析出 5 个键 —— 滑块用的是 oninput 不是 onchange（修复前这里解析出 0）",
   found.value.filter(p => p.indexOf('SUL.') === 0).length === 5,
   JSON.stringify(found.value.filter(p => p.indexOf('SUL.') === 0)));
ck("★★updateConfig 解析出 config.lockMode —— 构型是 <select>，不是 selectRadio（修复前完全漏掉）",
   found.value.indexOf('config.lockMode') >= 0, JSON.stringify(found.value));
ck("★直接赋值的模式（onchange=\"state.X=this.value\"）也被覆盖",
   found.value.indexOf('config.label') >= 0 || found.value.indexOf('continuity.label') >= 0,
   JSON.stringify(found.value));
ck("★toggleCheck 解析出 ≥1 处", found.check.length >= 1, JSON.stringify(found.check));

const stateSrc = base.match(/const state = \{([\s\S]*?)\n\s*\};/);
ck("★能找到 state 定义", !!stateSrc);
if (stateSrc) {
  const paths = [...new Set([].concat(found.state, found.radio, found.value))];
  const bad = paths.filter(p => {
    const head = p.split('.')[0];
    return !(new RegExp("\\b" + head + "\\s*:").test(stateSrc[1]) || head === 'SUL');
  });
  ck("★解析出的所有路径，其根键在 state 里都存在（否则恢复会写进不存在的键）",
     bad.length === 0, JSON.stringify(bad));
  const cats = [...new Set(found.check)];
  const missing = cats.filter(c => !new RegExp("\\b" + c + "\\s*:").test(stateSrc[1]));
  ck("★勾选分类名都能在 state 里找到", missing.length === 0, JSON.stringify(missing));
}

// ── 评分组：基座没有静态 data-path（靠 initRatingGroups 运行时注入）──
ck("★基座里【没有】静态 data-path 的评分组 ⇒ 恢复必须发生在 initRatingGroups 之后",
   !/class="[^"]*rating-group[^"]*"[^>]*data-path=/.test(base));
ck("★基座里评分组的 data-path 由 initRatingGroups 的 map 注入（9 个路径）",
   (base.match(/'(existence|maintenance|fears|order)\.[a-z_.]+'/g) || []).length >= 9,
   String((base.match(/'(existence|maintenance|fears|order)\.[a-z_.]+'/g) || []).length));

// ── 反向：不该匹配到无关的 ──
ck("★RE_UPDATE 不匹配 loadArchive(this.value)", extract('<select onchange="loadArchive(this.value)">') === null);
ck("★updateMeta() 不被误认成状态写入", extract('<input onchange="updateMeta()">') === null);
ck("★updateSUL 不会被 updateState 抢先匹配",
   (extract('<input oninput="updateSUL(\'intent\',this.value)">') || {}).path === 'SUL.intent');

console.log("\n  " + (ok ? "全部通过 ✅" : "有失败 ❌"));
process.exit(ok ? 0 : 1);
