// 检查【构建产物】tool/index.html：语法 + 板块接线 + 内联数据可用。
// 基座有自己的测试；这里测的是「组装完还对不对」—— 组装是最容易悄悄坏的一步。
const fs = require("fs");
const path = require("path");

const OUT = path.join(__dirname, "..", "tool", "index.html");
const src = fs.readFileSync(OUT, "utf8");
let ok = true;
const ck = (name, cond, detail) => {
  if (cond) console.log("  ✅ " + name);
  else { ok = false; console.log("  ❌ " + name + "   " + (detail || "")); }
};

console.log("# 构建产物检查：tool/index.html（" + src.length + " 字节）");

const scripts = [...src.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
ck("有内联 <script> 块（" + scripts.length + " 个）", scripts.length >= 3);
scripts.forEach((s, i) => {
  try { new Function(s); console.log(`     ✅ 第 ${i + 1} 块语法正确（${s.split("\n").length} 行）`); }
  catch (e) { ok = false; console.log(`     ❌ 第 ${i + 1} 块语法错误：${e.message}`); }
});

// 内联数据必须能被解析，且与引擎口径一致
const dm = src.match(/window\.CONSTRUCT_DATA=(\{[\s\S]*?\});<\/script>/);
ck("★内联数据可解析", !!dm);
let D = null;
if (dm) { try { D = JSON.parse(dm[1]); } catch (e) { ok = false; } }
ck("★内联数据里账的条数 = 3（与引擎一致）", D && D.ledger.total === 3,
   D ? String(D.ledger.total) : "无");
ck("★内联数据里带预登记阈值 1000",
   D && D.ledger.thresholds && D.ledger.thresholds.war_deaths === 1000);
ck("★内联数据里有档案索引（>100 份）", D && D.archive.count > 100,
   D ? String(D.archive.count) : "无");
ck("★账里每条的 flags 是数组（多问题一起报）",
   D && D.ledger.rows.every(r => Array.isArray(r.flags)),
   D ? JSON.stringify(D.ledger.rows.map(r => r.flags)) : "");
ck("★海湾那条同时带两个问题（判据不对题 + 无窗口）",
   D && D.ledger.rows.some(r => r.flags.length === 2),
   D ? JSON.stringify(D.ledger.rows.map(r => [r.id, r.flags.length])) : "");

// 板块与接线
["mod-backtest", "mod-ledger", "mod-archive", "mod-tabs"].forEach(id => {
  ck("板块容器 " + id + " 存在", src.indexOf('id="' + id + '"') >= 0);
});
ck("★三个标签按钮都在", ["backtest", "ledger", "archive"].every(m => src.indexOf('data-mod="' + m + '"') >= 0));
ck("★switchModule 有定义", /window\.switchModule\s*=/.test(src));
ck("★renderLedgerModule / renderArchiveModule 都有定义",
   /window\.renderLedgerModule\s*=/.test(src) && /window\.renderArchiveModule\s*=/.test(src));

// 基座的功能不能被组装弄丢
["renderExclusions", "commitBacktest", "renderHistoryList", "exportExclusions",
 "criterionOverlap", "renderBuildStamp"].forEach(fn => {
  ck("基座功能仍在：" + fn, new RegExp("function\\s+" + fn + "\\s*\\(").test(src));
});
ck("★基座的 #history-holder 还在", src.indexOf('id="history-holder"') >= 0);
ck("★单文件：无外部 script src", !/<script[^>]*\bsrc=/.test(src));
ck("★单文件：无外部 link href（除内联样式）", !/<link[^>]*\bhref=["'](?!data:)/i.test(src) ||
   !/<link[^>]*rel=["']stylesheet/i.test(src));

console.log("\n  " + (ok ? "全部通过 ✅" : "有失败 ❌"));
process.exit(ok ? 0 : 1);
