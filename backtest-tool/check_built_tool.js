// 检查构建产物 tool/index.html（新工具：结构诊断做壳 + 四个板块）
// 组装是最容易悄悄坏的一步 —— 这里测「拼完还对不对」，不重复测基座内部逻辑。
const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "..", "tool");
const OUT = path.join(DIR, "index.html");
const src = fs.readFileSync(OUT, "utf8");
let ok = true;
const ck = (n, c, d) => {
  if (c) console.log("  ✅ " + n);
  else { ok = false; console.log("  ❌ " + n + "   " + (d || "")); }
};

console.log("# 构建产物检查：tool/index.html（" + src.length + " 字节）");

// 语法
const scripts = [...src.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
ck("内联 <script> 块 = 3（内联数据 + 基座诊断 + 运行层）", scripts.length === 3, String(scripts.length));
scripts.forEach((s, i) => {
  try { new Function(s); console.log(`     ✅ 第 ${i + 1} 块语法正确（${s.split("\n").length} 行）`); }
  catch (e) { ok = false; console.log(`     ❌ 第 ${i + 1} 块语法错误：${e.message}`); }
});

// 内联数据
const dm = src.match(/window\.CONSTRUCT_DATA=(\{[\s\S]*?\});<\/script>/);
ck("★内联数据可解析", !!dm);
let D = null;
if (dm) { try { D = JSON.parse(dm[1]); } catch (e) { ok = false; } }
ck("★账 3 条（引擎口径）", D && D.ledger.total === 3, D ? String(D.ledger.total) : "无");
ck("★预登记阈值 1000", D && D.ledger.thresholds.war_deaths === 1000);
ck("★档案 >100 份", D && D.archive.count > 100, D ? String(D.archive.count) : "无");
ck("★海湾那条带两个问题（多问题一起报）",
   D && D.ledger.rows.some(r => r.flags.length === 2),
   D ? JSON.stringify(D.ledger.rows.map(r => [r.id, r.flags.length])) : "");
ck("★基座路径写进数据（可追溯）", D && /diagnostic-tool\.html$/.test(D.base), D && D.base);

// 板块结构
["diag", "backtest", "ledger", "archive"].forEach(m => {
  ck("板块容器 mod-" + m + " 存在", src.indexOf('id="mod-' + m + '"') >= 0);
  ck("标签按钮 data-mod=" + m + " 存在", src.indexOf('data-mod="' + m + '"') >= 0);
});
ck("★switchModule 有定义", /window\.switchModule\s*=/.test(src));
ck("★三个渲染函数都有定义",
   /window\.renderLedgerModule\s*=/.test(src) &&
   /window\.renderArchiveModule\s*=/.test(src) &&
   /window\.renderBuildStamp\s*=/.test(src));
ck("★构建戳元素与渲染都在", src.indexOf('id="build-stamp"') >= 0 && /renderBuildStamp\(\)/.test(src));
ck("★支持 #hash 直达板块", /location\.hash/.test(src));

// 板块① 必须真的是诊断工具（不是空壳）
["diagnose", "renderDiagnosis", "updateSUL", "cascadeL2", "loadArchive",
 "renderFearRadar", "renderOrderBars", "exportReport", "genVisPrompt"].forEach(fn => {
  ck("板块① 诊断功能仍在：" + fn, new RegExp("function\\s+" + fn + "\\s*\\(").test(src));
});
ck("★板块① 的档案导入通道还在（F20 修复没丢）",
   src.indexOf('id="archivePick"') >= 0 && src.indexOf("审计发现 F20") >= 0);

// 板块② 必须是完整的历史回溯工具
const bt = path.join(DIR, "modules", "backtest.html");
ck("★板块② 文件存在", fs.existsSync(bt));
if (fs.existsSync(bt)) {
  const b = fs.readFileSync(bt, "utf8");
  ["commitBacktest", "renderExclusions", "criterionOverlap", "renderHistoryList",
   "exportExclusions", "renderBuildStamp"].forEach(fn => {
    ck("板块② 功能仍在：" + fn, new RegExp("function\\s+" + fn + "\\s*\\(").test(b));
  });
  ck("★板块② 是独立完整页面（有自己的 <html> 与 dark 主题）",
     /<html/i.test(b) && /--bg\s*:/.test(b));
  ck("★板块② 自己也是单文件（无外部 script src）", !/<script[^>]*\bsrc=/.test(b));
}
ck("★板块② 用 iframe 指向它",
   src.indexOf('id="bt-frame"') >= 0 && src.indexOf('src="modules/backtest.html"') >= 0);

// 冲突隔离：两个工具都定义 state（诊断是 `const state =`，回溯是 `let state =`）
// ⇒ 所以必须靠 iframe 隔离，不能把两段 JS 合进同一个作用域
ck("★诊断声明了 state（const）", /const\s+state\s*=/.test(src));
if (fs.existsSync(bt)) {
  const b2 = fs.readFileSync(bt, "utf8");
  ck("★回溯也声明了 state（let）—— 两者同名 ⇒ iframe 隔离是必需的",
     /let\s+state\s*=/.test(b2));
}

// 标题
ck("★标题标明构建产物", src.indexOf("构建产物") >= 0);

console.log("\n  " + (ok ? "全部通过 ✅" : "有失败 ❌"));
process.exit(ok ? 0 : 1);
