# -*- coding: utf-8 -*-
"""第二遍：收紧到【真正的排除断言】，并给每条打可核性评分。

第一遍 498 条里大量是假阳性，两类：
  ① 模板占位行：[一句话：什么会导致该主体"无法维持自身"]
  ② 把「锁死」当【类型名】用：「结构锁死型」是场景分类，不是"不可能"的断言
真正的排除断言要满足：有【主体】＋有【被排除的动作／状态】＋（最好）有【理由】。

排除断言 vs 预测：
  预测「X 会发生」—— 需要未来数据
  排除「X 不可能」—— 单向可证伪：X 发生了就证伪；没发生只说明尚未被证伪
"""
import glob
import os
import re

WORKSPACE = r"D:\Projects\地缘推演台"
WB = r"C:\Users\xheih\WorkBuddy"
ROOTS = [
    os.path.join(WORKSPACE, "ConStruct_Archive"),
    os.path.join(WORKSPACE, "construct-engine"),
    os.path.join(WORKSPACE, "content"),
    os.path.join(WORKSPACE, "docs"),
    os.path.join(WB, "20260327221200", "out"),
    os.path.join(WB, "2026-06-09-17-25-25"),
]

# 47 主体的名称（含中英）
ACTORS = ["美国", "中国", "日本", "俄罗斯", "欧盟", "印度", "伊朗", "以色列", "乌克兰",
          "德国", "法国", "英国", "韩国", "土耳其", "沙特", "新加坡", "塞尔维亚",
          "巴基斯坦", "越南", "台湾", "澳大利亚", "埃及", "朝鲜", "北约", "东盟",
          "金砖", "OPEC", "G7", "US", "CN", "EU", "RU", "JP", "IN", "IL", "IR",
          "UA", "DE", "FR", "GB", "KR", "TR", "SA", "SG", "RS", "PK", "VN", "TW",
          "特朗普", "欧洲", "海湾", "中东"]

IMPOSSIBLE = r"不可能|走不通|做不到|无法|注定|必然失败|绝不会|永远不会|堵死|封死|死路"
REASON = r"因为|由于|原因是|源于|其根源|所以|因而|导致"
# 明显是【类型名/标题/模板】的，排除
NOISE = re.compile(r"\[|\]|锁死型|冻结型|结构锁死\s*[|＋+]|^#|^\||\*\*[^：]{1,12}\*\*\s*\|")

SPLIT = re.compile(r"[。！？\n]")


def score(s: str):
    sc = 0
    if re.search(IMPOSSIBLE, s):
        sc += 2
    if re.search(REASON, s):
        sc += 2
    if any(a in s for a in ACTORS):
        sc += 2
    if 20 <= len(s) <= 120:
        sc += 1
    if "——" in s or "→" in s:
        sc -= 1          # 多为图示行
    return sc


def run():
    files = []
    for root in ROOTS:
        if os.path.isdir(root):
            files += [p for p in glob.glob(os.path.join(root, "**", "*.md"), recursive=True)
                      if "node_modules" not in p]
    seen = set()
    out = []
    for p in files:
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for sent in SPLIT.split(txt):
            s = sent.strip()
            if not (10 <= len(s) <= 160):
                continue
            if not re.search(IMPOSSIBLE, s):
                continue
            if NOISE.search(s):
                continue
            if not any(a in s for a in ACTORS):
                continue
            key = s[:60]
            if key in seen:          # 同一句在多份副本里重复（WorkBuddy/workspace 各一份）
                continue
            seen.add(key)
            out.append({"score": score(s), "file": p.replace(WORKSPACE + "\\", "")
                        .replace(WB + "\\", "WB\\"), "text": s})
    out.sort(key=lambda x: -x["score"])
    return len(files), out


if __name__ == "__main__":
    n, out = run()
    print("扫了 %d 个 .md，去重后候选 %d 条" % (n, len(out)))
    print("分数分布：", {k: sum(1 for o in out if o["score"] == k) for k in sorted({o["score"] for o in out}, reverse=True)})
    print("\n=== 前 45 条（按可核性评分）===")
    for o in out[:45]:
        print("  [%d] %s" % (o["score"], o["text"][:130]))
        print("       ← %s" % o["file"][:100])
