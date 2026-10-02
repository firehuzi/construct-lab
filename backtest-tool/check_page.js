// 整页脚本语法检查：抽出 <script> 内容，用 new Function 解析（不执行）。
// 目的是确认我加的东西没把页面弄坏 —— 单文件工具没有构建步骤，语法错会整页白屏。
const fs = require("fs");
const path = require("path");
const src = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

const scripts = [...src.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);
console.log("  内联 <script> 块数 = " + scripts.length);

let ok = true;
scripts.forEach((s, i) => {
  try {
    new Function(s);          // 只解析，不执行
    console.log(`  ✅ 第 ${i + 1} 块语法正确（${s.split("\n").length} 行）`);
  } catch (e) {
    ok = false;
    console.log(`  ❌ 第 ${i + 1} 块语法错误：${e.message}`);
  }
});

// 接线检查：新函数必须【有定义且被引用】
const need = [
  ["buildExclusionRecord", 2],   // 定义 1 次 + 被 exportBacktest/exportExclusions 引用
  ["renderExclusions", 2],       // 定义 + 被 renderStep4 引用
  ["addExclusion", 2],
  ["removeExclusion", 2],
  ["exportExclusions", 2],
  ["selfTestExclusion", 1],
];
console.log("\n  接线检查：");
need.forEach(([name, min]) => {
  const def = new RegExp("function\\s+" + name + "\\s*\\(").test(src);
  const refs = (src.match(new RegExp(name, "g")) || []).length;
  const good = def && refs >= min;
  if (!good) ok = false;
  console.log(`    ${good ? "✅" : "❌"} ${name}  定义=${def}  出现次数=${refs}（需 ≥${min}）`);
});

// 关键 UI 元素必须在
const ui = ["data-exc=", "data-excfield=", "导出排除断言", "我排除的路径"];
console.log("\n  UI 元素：");
ui.forEach(u => {
  const has = src.includes(u);
  if (!has) ok = false;
  console.log(`    ${has ? "✅" : "❌"} ${u}`);
});

console.log("\n  " + (ok ? "全部通过 ✅" : "有失败 ❌"));
process.exit(ok ? 0 : 1);
