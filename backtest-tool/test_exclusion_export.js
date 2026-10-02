// 抽出 HTML 里的 buildExclusionRecord / selfTestExclusion / esc，在 node 里跑自证。
// 为什么这样测：工具是单文件 HTML，整体加载需要 DOM；而【这两段是纯函数】，
// 抽出来就能独立验证 —— 纯函数化本身就是为了可测。
const fs = require("fs");
const path = require("path");

const HTML = path.join(__dirname, "index.html");
const src = fs.readFileSync(HTML, "utf8");

function grab(name) {
  const i = src.indexOf("function " + name + "(");
  if (i < 0) throw new Error("找不到函数 " + name);
  let d = 0, started = false;
  for (let j = i; j < src.length; j++) {
    if (src[j] === "{") { d++; started = true; }
    else if (src[j] === "}") { d--; if (started && d === 0) return src.slice(i, j + 1); }
  }
  throw new Error("函数 " + name + " 括号不闭合");
}

const parts = ["criterionOverlap", "buildExclusionRecord", "selfTestExclusion", "esc"].map(grab).join("\n\n");
const consts = 'const EXCLUSION_SCHEMA = ' +
  JSON.stringify(src.match(/const EXCLUSION_SCHEMA = '([^']+)'/)[1]) + ';';

const mod = new Function(consts + "\n" + parts +
  "\nreturn { buildExclusionRecord, selfTestExclusion, EXCLUSION_SCHEMA };")();

console.log("# backtest-tool · 排除断言导出 —— node 侧自证");
console.log("  schema = " + mod.EXCLUSION_SCHEMA);
const ok = mod.selfTestExclusion();
console.log("\n  结果：" + (ok ? "全部通过 ✅" : "有失败 ❌"));

// 额外：跑一条真实形状的记录，看导出长什么样
const rec = mod.buildExclusionRecord(
  { id: "cuban-missile", name: "古巴导弹危机", timePoint: "1962年10月22日" },
  { exclusions: [
      { excluded: "美国对古巴实施空袭", criterion: "出现美军对古巴本土的空中打击行动", window: "13天" },
      { excluded: "苏联公开拒绝撤走导弹", criterion: "", window: "13天" }
  ] }, new Date().toISOString());
console.log("\n  样例导出：");
console.log(JSON.stringify(rec, null, 2).split("\n").map(l => "    " + l).join("\n"));
process.exit(ok ? 0 : 1);
