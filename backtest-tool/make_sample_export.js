// 用工具自己的纯函数产出一条真实形状的导出记录，作为「摄入」环节的输入。
// 这样验证的是【同一段代码路径】，而不是我手写一个 JSON 去骗摄入器。
const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
function grab(name) {
  const i = src.indexOf("function " + name + "(");
  if (i < 0) throw new Error("找不到 " + name);
  let d = 0, started = false;
  for (let j = i; j < src.length; j++) {
    if (src[j] === "{") { d++; started = true; }
    else if (src[j] === "}") { d--; if (started && d === 0) return src.slice(i, j + 1); }
  }
}
const schema = src.match(/const EXCLUSION_SCHEMA = '([^']+)'/)[1];
const build = new Function(
  "const EXCLUSION_SCHEMA = " + JSON.stringify(schema) + ";\n" +
  grab("buildExclusionRecord") + "\nreturn buildExclusionRecord;")();

// 一份【混有缺判据】的样例 —— 有意如此：摄入器必须把它挑出来。
const rec = build(
  { id: "cuban-missile", name: "古巴导弹危机",
    timePoint: "1962年10月22日——肯尼迪宣布对古巴实施海上封锁" },
  { exclusions: [
      { excluded: "美国对古巴实施空袭",
        criterion: "出现美军对古巴本土的空中打击行动", window: "13天" },
      { excluded: "苏联公开拒绝撤走导弹",
        criterion: "", window: "13天" },                       // ← 缺判据
      { excluded: "美国从土耳其撤走朱庇特导弹被公开披露",
        criterion: "1962-1963 年有公开报道证实此秘密交易", window: "6个月" },
      { excluded: "古巴主动请求苏联撤走导弹",
        criterion: "", window: "" },                            // ← 缺判据且缺窗口
  ] },
  new Date().toISOString());

const out = path.join(__dirname, "exclusions-cuban-missile.json");
fs.writeFileSync(out, JSON.stringify(rec, null, 2), "utf8");
console.log("  写出 " + path.basename(out) +
            "：共 " + rec.summary.total + " 条，" +
            "可证伪 " + rec.summary.falsifiable + " 条，" +
            "不可证伪 " + rec.summary.unfalsifiable + " 条");
console.log("  不可证伪的 id：" + rec.summary.unfalsifiable_ids.join("、"));
