// 行为测试：在 node 里用最小 DOM 桩【跑真实代码路径】。
//
// ★ 为什么不用真浏览器：我试了 Chromium（ms-playwright/chromium-1228，149.0.7827.55）：
//     · 默认 --headless（=new）不往 stdout 写 --dump-dom
//     · --headless=old 只在【管道】下偶尔能拿到，重定向到文件恒为 0 字节
//     · --screenshot 也不产文件；不带 --headless 时会真启动浏览器去连网并挂住
//   我没能在本环境里稳定拿到真浏览器的 DOM。**所以这里如实标为「DOM 桩」，
//   不冒充端到端浏览器测试。** 它证的是：脚本能加载并跑到 init、
//   状态机与渲染函数正确、导出内容正确 —— 但【不证 CSS/真实事件】。
//
// 这比 check_page.js 强的地方：那个只解析语法（new Function），
// 一个语法健全的页面照样能在 init() 里抛错、或导出按钮根本产不出东西。

const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const bigScript = [...src.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).sort((a, b) => b.length - a.length)[0];

// ── 最小 DOM 桩 ────────────────────────────────────────────────
const downloaded = [];
const alerts = [];
function el(id) {
  return {
    id, innerHTML: "", textContent: "", value: "", href: "", download: "",
    style: {}, dataset: {},
    classList: { add() {}, remove() {}, contains() { return false; } },
    click() { downloaded.push({ name: this.download }); },
    appendChild() {}, insertBefore() {}, getElementsByTagName() { return []; },
    parentNode: { insertBefore() {} },
  };
}
const nodes = {};
const document = {
  getElementById(id) { return (nodes[id] = nodes[id] || el(id)); },
  querySelectorAll() { return []; },
  addEventListener() {},
  createElement() { return el("a"); },
  getElementsByTagName() { return []; },
  body: el("body"), head: el("head"),
};
class FakeBlob {
  constructor(parts, opts) { this.parts = parts; this.type = (opts || {}).type || ""; }
}
let lastBlob = null;
const URL_ = {
  createObjectURL(b) { lastBlob = b; return "blob:fake"; },
  revokeObjectURL() {},
};
const alert = m => alerts.push(m);
const confirm = () => true;

const sandbox = { document, Blob: FakeBlob, URL: URL_, alert, confirm,
                  console, setTimeout, JSON, Math, Object, Array, String, Number,
                  Date, parseInt, parseFloat, RegExp, Error };
// 渲染路径用到的浏览器 API —— 缺一个就会在这里崩，而崩了正是本测试要抓的
sandbox.scrollTo = () => {};
sandbox.addEventListener = () => {};
sandbox.matchMedia = () => ({ matches: false, addEventListener() {} });
sandbox.requestAnimationFrame = fn => setTimeout(fn, 0);
sandbox.location = { href: "file:///fake/index.html", hash: "" };
sandbox.window = sandbox;

// ── 加载：这一步本身就在测 init() 会不会抛 ──────────────────────
let nPass = 0, nFail = 0;
const ck = (name, cond, detail) => {
  if (cond) { nPass++; console.log("  ✅ " + name); }
  else { nFail++; console.log("  ❌ " + name + "   " + (detail === undefined ? "" : detail)); }
};

console.log("# backtest-tool · 行为测试（DOM 桩，非真浏览器）");
let loadOk = true, loadErr = "";
try {
  new Function("document", "Blob", "URL", "alert", "confirm", "window",
               bigScript)(document, FakeBlob, URL_, alert, confirm, sandbox);
} catch (e) { loadOk = false; loadErr = e.message; }
ck("★脚本加载并执行 init() 不抛异常", loadOk, loadErr);

// init() → renderScenarioGrid() 应把场景卡写进 #scenario-grid
const gridHtml = (nodes["scenario-grid"] || {}).innerHTML || "";
ck("★init 后场景网格已渲染（3 个场景）",
   (gridHtml.match(/scenario-card/g) || []).length === 3,
   "找到 " + (gridHtml.match(/scenario-card/g) || []).length + " 个");
ck("场景卡含三个场景名",
   ["古巴导弹危机", "海湾战争", "克里米亚危机"].every(x => gridHtml.includes(x)));

// ── 驱动流程：进场景 → 到第 4 步 → 看排除栏 ─────────────────────
// 注意：这些函数是 new Function 作用域内的，我拿不到引用。
// 所以改用【页面自己暴露的入口】：onclick 里调用的那些函数挂在 window 上吗？
// 这个工具用的是内联 onclick，函数是全局的 —— 在 new Function 作用域里不是全局。
// ⇒ 改为从源码里抓出需要的函数，在同一作用域里重新拼一个可调用的接口。
function grab(name) {
  const i = bigScript.indexOf("function " + name + "(");
  if (i < 0) return null;
  let d = 0, started = false;
  for (let j = i; j < bigScript.length; j++) {
    if (bigScript[j] === "{") { d++; started = true; }
    else if (bigScript[j] === "}") { d--; if (started && d === 0) return bigScript.slice(i, j + 1); }
  }
  return null;
}
const wanted = ["startBacktest", "render", "renderStep4", "renderExclusions",
                "addExclusion", "removeExclusion", "buildExclusionRecord",
                "exportExclusions", "exportBacktest", "collectState", "goStep"];
const missing = wanted.filter(w => !grab(w));
ck("所有需要的函数都能抓到", missing.length === 0, missing.join(","));

const api = new Function("document", "Blob", "URL", "alert", "confirm", "window",
  bigScript + "\nreturn {" + wanted.map(w => w + ":typeof " + w + "==='function'?" + w + ":null").join(",") +
  ", getState:function(){return state;}, setState:function(s){state=s;}, getBT:function(){return currentBT;}};"
)(document, FakeBlob, URL_, alert, confirm, sandbox);

ck("startBacktest 可调用", typeof api.startBacktest === "function");
api.startBacktest("cuban-missile");
ck("★startBacktest 后 currentBT 正确",
   api.getBT() && api.getBT().id === "cuban-missile", String(api.getBT() && api.getBT().id));
ck("★startBacktest 重置了 exclusions", Array.isArray(api.getState().exclusions));

// 到第 4 步：renderStep4 应含「我排除的路径」一栏
const step4 = api.renderStep4();
ck("★第 4 步渲染出「我排除的路径」", step4.includes("我排除的路径"));
// 空状态：只该有引导语 + 添加按钮，【不该】有输入格
// （我第一次把断言写成「空状态就要有三个输入格」——那是错的，行还没加）
ck("★空状态：有引导语与添加按钮", step4.includes("不可能发生") && step4.includes("+ 添加排除断言"));
ck("★空状态：不该出现输入格", !step4.includes('data-excfield="excluded"'));

// 加一条【有判据】的 → 应出现三个输入格，且不标红
api.addExclusion();
let h0 = api.renderExclusions();
ck("★加一条后出现三个输入格（路径/判据/窗口）",
   h0.includes('data-excfield="excluded"') &&
   h0.includes('data-excfield="criterion"') &&
   h0.includes('data-excfield="window"'));
let st = api.getState();
st.exclusions[0] = { excluded: "美国空袭古巴", criterion: "出现美军对古巴本土的空中打击", window: "13天" };
let h = api.renderExclusions();
ck("有判据 ⇒ 不出现「缺判据」告警", !h.includes("缺判据 ⇒"), h.slice(0, 120));
ck("有判据 ⇒ 汇总显示可证伪 1 条", /可证伪\s*1\s*条/.test(h.replace(/<[^>]+>/g, "")), h.match(/可证伪[^<]*/));

// 再加一条【缺判据】的 → 必须标红
api.addExclusion();
st = api.getState();
st.exclusions[1] = { excluded: "苏联公开拒绝撤走导弹", criterion: "", window: "13天" };
h = api.renderExclusions();
ck("★缺判据 ⇒ 出现「缺判据」告警", h.includes("缺判据 ⇒"), "");
ck("★缺判据 ⇒ 该行左边框标红（--danger）", /border-left:3px solid var\(--danger\)/.test(h));
ck("★缺判据 ⇒ 汇总显示不可证伪 1 条", /不可证伪\s*1\s*条/.test(h.replace(/<[^>]+>/g, "")),
   (h.replace(/<[^>]+>/g, "").match(/不可证伪[^；]*/) || [""])[0]);

// ── 导出：内容必须正确 ────────────────────────────────────────
downloaded.length = 0;
api.exportExclusions();
ck("★导出触发了一次下载", downloaded.length === 1, "次数=" + downloaded.length);
ck("★下载文件名形如 exclusions-<id>.json",
   downloaded[0] && downloaded[0].name === "exclusions-cuban-missile.json",
   downloaded[0] && downloaded[0].name);
const payload = lastBlob ? lastBlob.parts.join("") : "";
let rec = null;
try { rec = JSON.parse(payload); } catch (e) { }
ck("★导出内容是合法 JSON", !!rec, payload.slice(0, 80));
ck("★schema 正确", rec && rec.schema === "construct-exclusion-v1", rec && rec.schema);
ck("★summary 正确：total=2 falsifiable=1 unfalsifiable=1",
   rec && rec.summary.total === 2 && rec.summary.falsifiable === 1 && rec.summary.unfalsifiable === 1,
   rec && JSON.stringify(rec.summary));
ck("★不可证伪的那条 id 被列出",
   rec && rec.summary.unfalsifiable_ids.length === 1 && /-X02$/.test(rec.summary.unfalsifiable_ids[0]),
   rec && rec.summary.unfalsifiable_ids.join(","));

// 导出 Markdown：也要含排除那一段
downloaded.length = 0;
api.exportBacktest();
const md = lastBlob ? lastBlob.parts.join("") : "";
ck("★Markdown 含「我排除的路径」段", md.includes("我排除的路径"));
ck("★Markdown 就地标出缺判据的那条", md.includes("未填判据 ⇒ 这条断言不可证伪，不携带信息"));
ck("★Markdown 提示不可证伪的条数与 id",
   md.includes("不可证伪 1 条") || /有 1 条断言缺判据/.test(md), "");

console.log(`\n  通过 ${nPass}，失败 ${nFail}`);
console.log("  ⚠️ 覆盖范围：脚本加载/状态机/渲染/导出内容。**不含** CSS 与实际浏览器事件。");
process.exit(nFail === 0 ? 0 : 1);
