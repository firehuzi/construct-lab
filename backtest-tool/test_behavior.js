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
// ★ 字段注册表：原来的桩让 querySelectorAll 恒返回 []，于是【收集逻辑根本没被测到】——
//   这正是那三个「收集/回填不配对」的 bug 能活下来的原因。现在可以注册假字段。
const registry = { "[data-actor]": [], "[data-path]": [], "[data-note]": [] };
const document = {
  getElementById(id) { return (nodes[id] = nodes[id] || el(id)); },
  querySelectorAll(sel) { return registry[sel] || []; },
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
// ★ localStorage 桩：历史记录功能靠它。脚本里用的是 typeof 守卫，
//   不传也能跑（会退化成「历史只在会话内」），但要【测】历史就必须传。
const lsStore = {};
const localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(lsStore, k) ? lsStore[k] : null; },
  setItem(k, v) { lsStore[k] = String(v); },
  removeItem(k) { delete lsStore[k]; },
};

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
  new Function("document", "Blob", "URL", "alert", "confirm", "window", "localStorage",
               bigScript)(document, FakeBlob, URL_, alert, confirm, sandbox, localStorage);
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
const wanted = ["startBacktest", "render", "renderStep0", "renderStep4", "renderExclusions",
                "addExclusion", "removeExclusion", "buildExclusionRecord", "criterionOverlap",
                "exportExclusions", "exportBacktest", "collectState", "commitStep", "goStep",
                "commitBacktest", "navCommit", "loadHistory", "saveHistory", "buildRunRecord", "nextStep", "prevStep",
                "exportHistory", "renderHistoryList", "deleteHistoryRun", "renderScenarioGrid"];
const missing = wanted.filter(w => !grab(w));
ck("所有需要的函数都能抓到", missing.length === 0, missing.join(","));

const api = new Function("document", "Blob", "URL", "alert", "confirm", "window", "localStorage",
  bigScript + "\nreturn {" + wanted.map(w => w + ":typeof " + w + "==='function'?" + w + ":null").join(",") +
  ", getState:function(){return state;}, setState:function(s){state=s;}, getBT:function(){return currentBT;}};"
)(document, FakeBlob, URL_, alert, confirm, sandbox, localStorage);

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
ck("★缺判据 ⇒ 汇总单列「缺判据 1 条」（措辞已从「不可证伪」改为「缺判据」）",
   /缺判据\s*1\s*条/.test(h.replace(/<[^>]+>/g, "")),
   (h.replace(/<[^>]+>/g, "").match(/缺判据[^；]*/) || [""])[0]);

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

// ══════════════════════════════════════════════════════════════
// 用户报的 bug：「自主推演没有提交按钮或者功能缺失」
// 查出的是【一整类】收集/回填不配对，三个实例。这里逐个钉死。
// ══════════════════════════════════════════════════════════════
console.log("\n  ── 用户报的 bug：收集/回填不配对（三个实例）");

// ① 机制复现：旧写法用 parseInt 取索引，而自由笔记的 data-path 是 "free"
ck('★复现旧 bug 的机制：parseInt("free") 是 NaN（旧代码据此造出 paths[NaN] 键）',
   Number.isNaN(parseInt("free", 10)));
ck("★NaN 会作废 forEach 遍历（非索引属性被跳过）⇒ 笔记永远进不了导出",
   (() => { const a = []; a[NaN] = { notes: "x" }; let seen = 0;
            a.forEach(() => seen++); return seen === 0; })());

// ② 自由笔记：注册一个 data-note 字段，收集后必须落在 state.pathNotes
api.startBacktest("cuban-missile");
registry["[data-note]"] = [{ dataset: { note: "free" }, value: "我认为封锁是唯一体面的出路" }];
api.collectState();
ck("★自由笔记被收进 state.pathNotes（不是 paths[NaN]）",
   api.getState().pathNotes === "我认为封锁是唯一体面的出路",
   JSON.stringify(api.getState().pathNotes));
ck("★state.paths 里【没有】NaN 键",
   !Object.getOwnPropertyNames(api.getState().paths).includes("NaN"),
   Object.getOwnPropertyNames(api.getState().paths).join(","));
ck("★自由笔记能【回填】（renderStep4 的 textarea 里有它）",
   api.renderStep4().includes("我认为封锁是唯一体面的出路"));

// ③ 自由笔记必须出现在两个导出里
downloaded.length = 0; api.exportBacktest();
const md2 = lastBlob ? lastBlob.parts.join("") : "";
ck("★自由笔记出现在 Markdown 导出里", md2.includes("认为自己封锁是唯一体面的出路") || md2.includes("我认为封锁是唯一体面的出路"),
   md2.includes("自由笔记") ? "有段落" : "缺段落");

// ④ 决策时间点：旧代码收集写 state.scene.decisionPoint，回填却读 currentBT.timeLocked.decisionPoint
nodes["s-decision"] = el("s-decision");
nodes["s-decision"].value = "1962年10月24日（我修订过）";
api.collectState();
ck("★决策时间点被收进 state.scene.decisionPoint",
   api.getState().scene.decisionPoint === "1962年10月24日（我修订过）",
   JSON.stringify(api.getState().scene.decisionPoint));
ck("★决策时间点能【回填】（renderStep0 里有我修订的值）",
   api.renderStep0().includes("1962年10月24日（我修订过）"));
ck("★修正过的决策时间点出现在 Markdown 导出里",
   /我修订的决策时间点/.test(md2) || /我修订的决策时间点/.test((downloaded.length = 0, api.exportBacktest(), lastBlob.parts.join(""))));

// ⑤ 非法 HTML：<textarea> 不该有 value 属性
// ★ 这里踩过一次：我原先直接对 bigScript 做正则，结果【我自己的注释】里
//   写着 `<textarea id="s-decision" value="...">` 来解释这个 bug，被当成了代码。
//   所以先剥掉整行注释再看 —— 测试要检查代码，不是检查注释。
const codeOnly = bigScript.split("\n").filter(l => !/^\s*\/\//.test(l)).join("\n");
const badTextarea = (codeOnly.match(/<textarea[^>]*\bvalue=/g) || []);
ck("★代码里没有 <textarea ... value= ...>（非法 HTML：textarea 的内容应在标签之间）",
   badTextarea.length === 0, badTextarea.join(" | "));
ck("（注：仅剥整行注释；行尾注释未剥 —— 本检查的已知局限）", true);

// ⑥ 提交入口：必须有显式的提交函数 + 状态回执
ck("★存在 commitStep（显式提交）", typeof api.commitStep === "function");
const r = api.commitStep();
ck("★commitStep 返回可核的计数", r && typeof r.nPaths === "number" && typeof r.badExc === "number",
   JSON.stringify(r));
ck("★提交后写入状态回执 #save-status",
   /已保存/.test((nodes["save-status"] || {}).innerHTML || ""),
   (nodes["save-status"] || {}).innerHTML);
ck("★回执里包含排除断言的条数与「缺判据」告警",
   /排除断言/.test((nodes["save-status"] || {}).innerHTML || ""));

// ⑦ 界面里真有那个按钮（★ 按钮的 onclick 已从 commitStep 改成 navCommit ——
//    因为最后一步它是【提交】而不是【保存草稿】。断言跟着改，别留旧的。）
ck("★页面里有提交按钮且绑定 navCommit",
   /id="btn-commit"[^>]*onclick="navCommit\(\)"/.test(src));
ck("★页面里有 #save-status 元素", /id="save-status"/.test(src));

// ⑧ ★判据 vs 被排除的路径：第一个【真实记录】打出来的缺口
console.log("\n  ── 第一个真实记录打出来的缺口：判据对不对题");
ck("★重叠度：真实那一对（核战前奏 vs 互撤导弹）应为 0",
   api.criterionOverlap("危机局势进一步加剧 进入核战前奏", "互撤导弹") === 0,
   String(api.criterionOverlap("危机局势进一步加剧 进入核战前奏", "互撤导弹")));
// ★ 这条是防「把中文剥光」那个坑的：全中文完全相同必须得 1
ck("★重叠度：同一串中文必须得 1（防 JS 的 \\W 把中文剥光）",
   api.criterionOverlap("中国", "中国") === 1,
   String(api.criterionOverlap("中国", "中国")));
ck("★重叠度：含标点/空格的中文也要保住词面",
   api.criterionOverlap("欧盟自主建军，五年内", "欧盟自主建军 五年内") === 1,
   String(api.criterionOverlap("欧盟自主建军，五年内", "欧盟自主建军 五年内")));
ck("★重叠度：对题的一对必须 > 0（不能把对题的也报成不对题）",
   api.criterionOverlap("欧盟自主建军", "欧盟把防务预算主权上交") > 0,
   String(api.criterionOverlap("欧盟自主建军", "欧盟把防务预算主权上交")));

const recMis = api.buildExclusionRecord(
  { id: "t", name: "T", timePoint: "X" },
  { exclusions: [
      { excluded: "危机局势进一步加剧 进入核战前奏", criterion: "互撤导弹", window: "3年" },
      { excluded: "美国空袭古巴", criterion: "出现美军对古巴本土的空中打击", window: "13天" },
  ] }, "now");
ck("★不对题的判据 ⇒ criterion_mismatch=true",
   recMis.exclusions[0].criterion_mismatch === true);
ck("★不对题的判据 ⇒ falsifiable=false（【不】算成可证伪）",
   recMis.exclusions[0].falsifiable === false);
ck("★不对题的判据 ⇒ note 指出「把路径预测填进了判据栏」",
   /路径预测|证伪条件/.test(recMis.exclusions[0].note), recMis.exclusions[0].note);
ck("★summary 单列 criterion_mismatch 计数与 id",
   recMis.summary.criterion_mismatch === 1 &&
   recMis.summary.criterion_mismatch_ids[0] === "t-X01",
   JSON.stringify(recMis.summary));
ck("★对题的那条不受影响（仍 falsifiable）",
   recMis.exclusions[1].criterion_mismatch === false &&
   recMis.exclusions[1].falsifiable === true);

// 界面上要就地提示
api.startBacktest("cuban-missile");
api.getState().exclusions = [
  { excluded: "危机局势进一步加剧 进入核战前奏", criterion: "互撤导弹", window: "3年" }];
const hMis = api.renderExclusions();
ck("★界面就地提示「判据可能不对题」", hMis.includes("判据可能不对题"));
ck("★界面点明原因（含两条真实记录的实例）",
   hMis.includes("互撤导弹") && hMis.includes("条约约束"));
ck("★界面用填空题语框逼出正确写法", hMis.includes("填空题") || hMis.includes("出现 ______"));
ck("★界面给出可忽略的口子（语义等价可零重叠）",
   hMis.includes("语义等价") || hMis.includes("忽略此提示"));
ck("★汇总里单列「判据可能不对题 N 条」", /判据可能不对题\s*1\s*条/.test(hMis.replace(/<[^>]+>/g, "")));

// ⑨ 提交回执里也要报出来
const r2 = api.commitStep();
ck("★commitStep 返回 misExc", typeof r2.misExc === "number", JSON.stringify(r2));
ck("★回执里出现「判据可能不对题」",
   /判据可能不对题/.test((nodes["save-status"] || {}).innerHTML || ""),
   (nodes["save-status"] || {}).innerHTML);

// ⑩ ★导出不许「静默无反应」—— 这是用户报的第二件事（克里米亚那次没产出文件）
console.log("\n  ── 导出不许静默失败");
api.startBacktest("crimea");
ck("★场景切换后 currentBT 是克里米亚", api.getBT().id === "crimea", api.getBT().id);
// 一条排除断言都不写就导出 ⇒ 也必须产文件（空记录本身是信息）
api.getState().exclusions = [];
downloaded.length = 0;
api.exportExclusions();
ck("★★一条都没写时导出【仍然产文件】（原版直接 return，什么都不下载）",
   downloaded.length === 1, "下载次数=" + downloaded.length);
ck("★空记录文件名正确（exclusions-crimea.json）",
   downloaded[0] && downloaded[0].name === "exclusions-crimea.json",
   downloaded[0] && downloaded[0].name);
const emptyRec = JSON.parse(lastBlob ? lastBlob.parts.join("") : "{}");
ck("★空记录 summary.total = 0", emptyRec.summary && emptyRec.summary.total === 0,
   JSON.stringify(emptyRec.summary));
ck("★导出后有状态回执（用户能看到它真的触发了）",
   /已导出/.test((nodes["save-status"] || {}).innerHTML || ""),
   (nodes["save-status"] || {}).innerHTML);
ck("★空导出时回执点明「一条都没写」",
   /一条都没写/.test((nodes["save-status"] || {}).innerHTML || ""));

// 没选场景时导出 ⇒ 必须给出可见反馈，不许静默
api.startBacktest("crimea");
const savedBT = api.getBT();
nodes["save-status"].innerHTML = "";
downloaded.length = 0;
// 把 currentBT 置空（模拟还没选场景）
const nullApi = new Function("document", "Blob", "URL", "alert", "confirm", "window", "localStorage",
  bigScript + "\nreturn {exportExclusions:exportExclusions, setBT:function(v){currentBT=v;}};"
)(document, FakeBlob, URL_, alert, confirm, sandbox, localStorage);
nullApi.setBT(null);
nullApi.exportExclusions();
ck("★★未选场景时导出【不静默】：给出可见回执",
   /还没选场景|没有可导出/.test((nodes["save-status"] || {}).innerHTML || ""),
   (nodes["save-status"] || {}).innerHTML);
ck("★未选场景时不产生下载", downloaded.length === 0, "下载次数=" + downloaded.length);

// ⑦ 界面里真有那个按钮
ck("★页面里有提交按钮且绑定 navCommit（最后一步它会变成「提交本次推演」）",
   /id="btn-commit"[^>]*onclick="navCommit\(\)"/.test(src));
ck("★页面里有 #save-status 元素", /id="save-status"/.test(src));
ck("★页面里有 #history-holder（历史记录挂载点）", /id="history-holder"/.test(src));

// ══════════════════════════════════════════════════════════════
// 用户报的第三件事：提交动作缺失（揭示历史替代了提交）＋ 没有历史推演记录
// ══════════════════════════════════════════════════════════════
console.log("\n  ── 提交与历史记录");

api.startBacktest("crimea");
api.getState().exclusions = [{ excluded: "北约出兵协助乌克兰",
                               criterion: "北约成员国军队出现在乌克兰境内", window: "3年" }];
api.getState().paths = [{ label: "克里米亚被俄罗斯逐步吞并", probability: "high", why: "结构上必然" }];
api.getState().actorNotes = { 0: "俄罗斯会认为这是展示实力的机遇" };
// ★ collectState 会从 DOM 回读 [data-note]，所以桩里的元素值也要同步 ——
//   否则提交时用旧值覆盖 state.pathNotes。（这【不是】代码 bug，
//   正是「边打边存」的正确行为；测试必须模拟「用户真的在框里打了字」。）
registry["[data-note]"] = [{ dataset: { note: "free" }, value: "俄乌战争还未结束，现在判断俄罗斯的成败还太早" }];
api.getState().pathNotes = "俄乌战争还未结束，现在判断俄罗斯的成败还太早";

// 没提交时，最后一步【不许】揭示
// goStep 有防跳步守卫（一次只能进一格）—— 用 nextStep 逐格走到第 4 步
api.nextStep(); api.nextStep(); api.nextStep(); api.nextStep();
ck("★连走四步到达第 4 步（下一步的按钮应变成揭示）", /揭示历史/.test(nodes["btn-next"].textContent || ""),
   nodes["btn-next"].textContent);
ck("★到第 4 步时 state.committed=false（还没提交）", api.getState().committed === false);
api.render();
ck("★未提交时揭示按钮标 🔒 且写明「需先提交」",
   /揭示历史.*🔒.*需先提交/.test(nodes["btn-next"].textContent || ""),
   nodes["btn-next"].textContent);
api.nextStep();                       // 未提交 ⇒ 应被挡下
ck("★★未提交时 nextStep 被挡下（不会揭示历史）",
   (nodes["save-status"].innerHTML || "").includes("还不能揭示历史"),
   nodes["save-status"].innerHTML);
ck("★挡下时给出明确指令", (nodes["save-status"].innerHTML || "").includes("提交本次推演"));

// 提交
const run = api.commitBacktest();
ck("★提交成功并返回记录", !!run && run.schema === "construct-run-v1", JSON.stringify(run && run.schema));
ck("★记录带 run_id", !!(run && run.run_id && run.run_id.indexOf("crimea-") === 0), run && run.run_id);
ck("★记录含推演路径（不是空壳）",
   run && run.paths.length === 1 && run.paths[0].label.indexOf("吞并") >= 0,
   JSON.stringify(run && run.paths));
ck("★记录含自由笔记（原版会丢）",
   run && run.free_notes.indexOf("俄乌战争还未结束") >= 0, run && run.free_notes);
ck("★记录含排除断言", run && run.exclusions.length === 1, String(run && run.exclusions.length));
ck("★记录带 readout 读数（历史列表要用）",
   run && run.readout && run.readout.exclusions === 1 && run.readout.unfalsifiable === 0,
   JSON.stringify(run && run.readout));
ck("★提交后 state.committed=true", api.getState().committed === true);
ck("★提交写入了历史（localStorage）", Object.keys(lsStore).length > 0, JSON.stringify(Object.keys(lsStore)));
ck("★提交回执写明「已进历史（第 N 次）」",
   /已进历史/.test(nodes["save-status"].innerHTML || ""), nodes["save-status"].innerHTML);

// 提交后可以揭示
api.render();
ck("★提交后揭示按钮解锁（🔓）", /揭示历史.*🔓/.test(nodes["btn-next"].textContent || ""),
   nodes["btn-next"].textContent);
api.nextStep();
ck("★提交后 nextStep 放行",
   !/还不能揭示/.test(nodes["save-status"].innerHTML || ""),
   "save-status=" + (nodes["save-status"].innerHTML || ""));

// 历史列表
const histHtml = api.renderHistoryList();
ck("★历史列表渲染出这条记录", histHtml.indexOf("克里米亚危机") >= 0, histHtml.slice(0, 80));
ck("★历史列表标出排除断言条数", /排除断言\s*1\s*条/.test(histHtml.replace(/<[^>]+>/g, "")));
ck("★历史列表有导出全部按钮", histHtml.indexOf("导出全部历史") >= 0);
ck("★历史列表有删除按钮", histHtml.indexOf("deleteHistoryRun") >= 0);

// 历史挂到场景页
api.renderScenarioGrid();
ck("★场景页的 #history-holder 被填充（用户报「没有历史记录」）",
   /📚 历史推演记录/.test(nodes["history-holder"].innerHTML || ""),
   (nodes["history-holder"].innerHTML || "").slice(0, 80));

// 导出全部历史
downloaded.length = 0;
api.exportHistory();
ck("★导出全部历史产生下载", downloaded.length === 1, "次数=" + downloaded.length);
ck("★历史文件名正确", downloaded[0] && downloaded[0].name === "construct-history.json",
   downloaded[0] && downloaded[0].name);
const histRec = JSON.parse(lastBlob ? lastBlob.parts.join("") : "{}");
ck("★导出内容 schema/条数正确",
   histRec.schema === "construct-history-v1" && histRec.count === 1,
   JSON.stringify({ s: histRec.schema, c: histRec.count }));

// 第二次提交 ⇒ 追加，不覆盖
api.startBacktest("crimea");
api.getState().exclusions = [{ excluded: "北约出兵协助乌克兰",
                               criterion: "北约成员国军队出现在乌克兰境内", window: "3年" }];
api.commitBacktest();
ck("★再次提交是【追加】不是覆盖（预测坟场要累积）", api.loadHistory().length === 2,
   String(api.loadHistory().length));

console.log(`\n  通过 ${nPass}，失败 ${nFail}`);
console.log("  ⚠️ 覆盖范围：脚本加载/状态机/渲染/导出内容。**不含** CSS 与实际浏览器事件。");
process.exit(nFail === 0 ? 0 : 1);