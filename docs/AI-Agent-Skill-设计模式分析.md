# AI Agent Skill 设计模式分析

> 基于四个开源 PPT/动画生成仓库的深度对比研究，为 ConStruct 地缘推演台设计专属 AI Agent Skill 架构。
> 研究仓库：`Unclecheng-li/AI_Animation` · `op7418/guizang-ppt-skill` · `crazyykhllc-bit/CyberPPT` · `hugohe3/ppt-master`

---

## 一、四大 Skill 设计模式全景

### 1.1 模式分类矩阵

| 维度 | A: 工具密集模式 | B: 风格中心模式 | C: 证据质量模式 | D: 管线编排模式 |
|---|---|---|---|---|
| **代表** | dynamic-archify | guizang-ppt-skill | CyberPPT | ppt-master |
| **复杂度** | ★☆☆☆ | ★★☆☆ | ★★★☆ | ★★★★ |
| **SKILL.md 大小** | 22KB | 36KB | 79KB | 77KB |
| **参考文献量** | ~50KB（schemas） | ~170KB | ~130KB | ~340KB |
| **工具脚本数** | 5 Node.js | 1 mjs | 14 Python | 40+ Python |
| **确认门数量** | 0 | 1（隐式） | 3（硬门） | 2 + spec_lock |
| **输出格式** | HTML+GIF/WebM | HTML 翻页 PPT | PPTX | PPTX |

### 1.2 执行纪律强度谱

```
宽松 ◄━━━━━━━━━━━━━━━━━━━━━━━━━━━► 严格

dynamic-archify          guizang         CyberPPT           ppt-master
 无纪律                    7问+步骤       3 Hard Gates      10条硬纪律
 一次性生成                步骤可跳过     禁止跨阶段          严格串行
 无确认门                  QC checklist   Reference Gate     spec_lock 逐页重读
```

### 1.3 参考文献组织模式对比

| 仓库 | 文件组织 | 核心创新 |
|---|---|---|
| **dynamic-archify** | schemas/*.json + examples/*.json | JSON Schema 约束 |
| **guizang** | references/*.md（按主题拆分） | 主题隔离 |
| **CyberPPT** | references/*.md（按阶段拆分） | **Reference Gate** — 阶段前强制重读 |
| **ppt-master** | references/*.md + workflows/*.md | **spec_lock** — 每页重读防漂移 |

---

## 二、八个可复用的结构模式

### 2.1 YAML 前置触发系统

**来源：四个仓库共用**

```yaml
---
name: example-skill
description: "Trigger description with domain terms"
triggers:
  - "架构图"
  - "流程图"
  - "system architecture"
  - "cloud diagram"
---
```

核心价值：触发词覆盖中文+英文+领域术语，是 Agent 自动匹配 Skill 的入口机制。

### 2.2 管线-阶段-步骤三层结构

**提取自**：ppt-master + CyberPPT

```
管线 (Pipeline) — 全局执行纪律
  ├── 阶段 1 (Stage) — GATE
  │     ├── 步骤 1.1 — 前提条件 (Prerequisites)
  │     ├── 步骤 1.2 — 强制步骤 (MUST)
  │     └── ⛔ 确认门 — 等待用户明确确认
  ├── 阶段 2 — GATE
  └── 阶段 3 — 最终确认门
```

### 2.3 Reference Gate（阶段前强制重读）

**提取自**：CyberPPT

| 阶段 | 必须产出 | 停止条件 | 必须读取 |
|---|---|---|---|
| 1. 分析 | 证据表、大纲 | ⛔ 用户确认 | refs/evidence.md |
| 2. 蓝图 | 视觉方案 | ⛔ 用户确认 | refs/visual-system.md |
| 3. 生产 | 最终成果 | ⛔ 用户确认 | refs/production.md |

### 2.4 spec_lock 上下文锁

**提取自**：ppt-master

```bash
# 每页/每步生成前必须执行
read_file <project_path>/spec_lock.md
# 所有颜色/字体/图标/图片必须来源于此文件
# 不得凭内存或临时编制
```

解决的问题：长上下文中的内容风格漂移。

### 2.5 规则强度标签

**提取自**：ppt-master

| 标签 | 含义 | 违反后果 |
|---|---|---|
| `MUST` | 必须行为 | 工作流失败 |
| `MUST NOT` | 禁止行为 | 工作流失败 |
| `DEFAULT` | 未指定时的默认值 | — |
| `OPTIONAL` | 仅显式触发时执行 | 跳过 |
| `FALLBACK` | 主路径失败后的回退 | 降级 |
| `GATE` | 进入下一步前的检查点 | 等待条件满足 |
| `BLOCKING` | 硬停止，等待用户响应 | 停在原地 |

### 2.6 自检清单

**提取自**：dynamic-archify（内联）+ guizang（31KB checklist.md）

```bash
# dynamic-archify 的 shell 自检
grep -E 'fill="(#|rgb)' output.html  # 检查无内联颜色
```

```markdown
# guizang 的 31KB checklist
- [ ] 所有图片存在且路径正确
- [ ] 所有外部链接可打开
- [ ] 无大面积空白页
- [ ] 滚动/翻页正常
```

### 2.7 请求路由分流

**提取自**：ppt-master（workflows/routing.md）

```
用户请求 → routing.md 决策
  → 新任务：主管线 7-Step Pipeline
  → 主题研究：topic-research workflow
  → 美化已有：beautify-pptx workflow
  → 音频生成：generate-audio workflow
  → 模板创建：create-template workflow
```

### 2.8 多角色协作

**提取自**：ppt-master + CyberPPT

```
源材料 → Strategist（策略） → Image Generator（配图） → Executor（执行） → 质检
```

---

## 三、为 ConStruct 地缘推演台设计的 Skill 架构

### 3.1 设计原则

1. **领域驱动** — 专为地缘政治分析设计
2. **证据为根** — 所有分析须追溯到 CWKB 或源材料
3. **多态输出** — 同一分析可输出：深度文章/HTML演示/推演动画/视频脚本/公众号
4. **管线可靠** — 吸收 ppt-master 的硬纪律 + CyberPPT 的 Reference Gate

### 3.2 目录结构

```
skills/construct-lab/              [新建] ConStruct Lab Skill
├── SKILL.md                       主指令文件
├── references/                    参考规范
│   ├── evidencing.md              证据收集与溯源
│   ├── geo-analysis.md            地缘政治分析方法论
│   ├── scenario-framework.md      推演框架
│   ├── narrative-design.md        叙事设计规范
│   ├── format-article.md          深度文章格式
│   ├── format-html-deck.md        HTML 演示格式
│   ├── format-video-script.md     视频脚本格式
│   ├── format-publish.md          公众号/Substack 格式
│   └── quality-gate.md            质检清单
├── workflows/                     独立工作流
│   ├── routing.md                 请求路由（唯一入口）
│   ├── topic-research.md          主题研究
│   ├── scenario-simulate.md       推演模拟
│   ├── create-report.md           深度报告
│   ├── create-video-script.md     视频脚本
│   ├── publish-article.md         发布文章
│   ├── analyze-crisis.md          危机追踪
│   └── failure-recovery.md        故障恢复
├── templates/                     输出模板
│   ├── analysis-report.md         分析报告模板
│   ├── scenario-card.md           推演卡片模板
│   └── video-script.md            视频脚本模板
└── scripts/                       工具脚本
    ├── validate_report.py         报告质检
    └── sync_cwkb.py               与 CWKB 同步
```

### 3.3 主管线

| 阶段 | 必须产出 | GATE | 必须读取 |
|---|---|---|---|
| **0. 路由** | 确定输出格式和路径 | — | workflows/routing.md |
| **1. 证据收集** | CWKB 证据底表、冲突记录 | ⛔ 用户确认 | references/evidencing.md |
| **2. 分析框架** | 应用方法论产出框架 | ⛔ 用户确认 | references/geo-analysis.md |
| **3. 输出设计** | 选定格式的详细蓝图 | ⛔ 用户确认 | 对应 format-*.md |
| **4. 生成生产** | 完整输出物 | — | spec_lock 逐节重读 |
| **5. 质量关卡** | 质检通过 | ⛔ 用户批准 | references/quality-gate.md |

### 3.4 执行纪律

```
🚨 全局执行纪律（违反即失败）

1. SERIAL — 阶段按顺序执行，输出是下一步输入
2. ⛔ BLOCKING — 标记为 BLOCKING 的阶段必须等待用户确认
3. NO BUNDLING — 禁止跨阶段捆绑
4. GATE BEFORE — 每个阶段开始前提条件验证
5. NO SPECULATE — 禁止推测执行
6. LOCK RE-READ — 每页/每节生成前重读 spec_lock
7. LANGUAGE RULE — 输出语言与用户一致
8. EVIDENCE RULE — 一切事实/数字必须有来源或标记为缺口
9. NO FABRICATION — 不得捏造地缘政治数据
```

### 3.5 路由系统

```
用户请求 → workflows/routing.md
  → 深度分析文章        → workflows/create-report.md
  → 推演模拟            → workflows/scenario-simulate.md
  → YouTube/B站脚本     → workflows/create-video-script.md
  → 危机追踪/快讯       → workflows/analyze-crisis.md
  → 公众号/Substack发布  → workflows/publish-article.md
  → 主题研究/资料收集    → workflows/topic-research.md
```

### 3.6 7 问澄清（引自 guizang-ppt-skill 的提问模式）

```
动手前用这 7 个问题对齐：

| # | 问题 | 目的 |
|---|---|---|
| 1 | 分析焦点？（事件/趋势/行为体/体系） | 决定分析框架 |
| 2 | 受众和渠道？（内部推演/公众号/YouTube） | 决定输出格式 |
| 3 | 篇幅？（文章字数/视频分钟数） | 决定深度 |
| 4 | 已有素材？（推演数据/CWKB 条目） | 决定证据基础 |
| 5 | 需要可视化？（架构图/流程图/地图） | 决定是否调用 dynamic-archify |
| 6 | 分析方法论？（现实主义/建构主义/地缘经济） | 决定框架方向 |
| 7 | 硬约束？（必须涵盖/不能提及/时间窗口） | 避免返工 |
```

### 3.7 与现有模块集成

```
        ConStruct Lab Skill（AI Agent 入口）
                   │
        ┌──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼
    CWKB Vault   Engine    Content   外部工具库
    ─────────   ─────────  ───────── ─────────
    知识库       推演引擎   文章/HTML   ppt-master
    事实底表      规则引擎   公众号排版   dynamic-archify
    证据溯源      场景模拟   YouTube     guizang-ppt
    概念本体      诊断生成   Substack    CyberPPT
```

### 3.8 质检关卡

```
## 交付前自检清单

### 事实准确性
- [ ] 所有数据/日期/数字有来源标注
- [ ] 冲突性信息已在正文中标记
- [ ] 无来源的信息已标注为"分析推断"

### 分析质量
- [ ] 分析框架在正文开头明确声明
- [ ] 多面性呈现（至少提及反方论证）
- [ ] 推演逻辑链完整（前提→过程→结论）

### 输出格式
- [文章] 段落层次清晰
- [HTML] 所有图片路径正确，翻页正常
- [脚本] 时间轴和画面描述完整
- [排版] 公众号/Substack 格式兼容
```

### 3.9 输出格式矩阵

| 输出类型 | 推荐工具链 | 典型用途 |
|---|---|---|
| 深度分析文章 | 直接生成 Markdown/HTML | 核心分析产出 |
| HTML 演示 PPT | 调用 guizang-ppt-skill | 演讲/分享 |
| 架构图/流程图 | 调用 dynamic-archify | 推演可视化 |
| 可编辑 PPTX | 调用 ppt-master 或 CyberPPT | 正式报告 |
| YouTube/B站脚本 | 时间轴+画面描述格式 | 视频制作 |
| 公众号/Substack | 特定排版模板 | 内容发布 |

### 3.10 实现路线图

| 阶段 | 内容 | 借鉴来源 |
|---|---|---|
| **Phase 1** | 创建 skills/construct-lab/ 骨架 + SKILL.md + routing.md | ppt-master |
| **Phase 2** | 实现 references: evidencing.md + geo-analysis.md + quality-gate.md | CyberPPT |
| **Phase 3** | 实现 spec_lock 上下文锁系统 | ppt-master |
| **Phase 4** | 实现 scripts: validate_report.py + sync_cwkb.py | CyberPPT + ppt-master |
| **Phase 5** | 与 dynamic-archify/guizang/ppt-master/CyberPPT 输出链路集成 | 跨仓库调用 |

---

## 四、总结

### 4.1 Skill 设计 checklist

```
□ 1. 定义 YAML 前置元数据
□ 2. 设计管线结构（阶段/步骤/确认门）
□ 3. 定义规则强度标签（MUST/MUST NOT/GATE/BLOCKING）
□ 4. 编写执行纪律（串行/禁止推测/禁止跨阶段）
□ 5. 设计参考文献系统（按阶段或主题拆分）
□ 6. 实现 Reference Gate（阶段前重读指定文件）
□ 7. 实现 spec_lock（多步骤防漂移）
□ 8. 设计确认门（用户确认点/硬停止/软停止）
□ 9. 编写路由系统（routing.md 分流）
□ 10. 实现质检关卡（自检清单/检查脚本）
□ 11. 编写故障恢复（failure-recovery.md）
□ 12. 设计输出模板（各输出类型的骨架）
```

### 4.2 关键决策点

| 决策 | 选项 |
|---|---|
| 单一 vs 多管线 | 简单用单管线，复杂用 routing.md |
| 硬门 vs 软门 | 重大方向用 BLOCKING，细节用 GATE |
| 大 SKILL.md vs 拆分 | 几十 KB 内合并，超过拆成 workflows/ |
| 自动 vs 手动质检 | 确定性用脚本，主观用 checklist |
| 引用 vs 克隆 | 外部工具用引用，深度集成用克隆 |

### 4.3 核心可迁移资产

| 仓库 | 可直接复用的模式 |
|---|---|
| **AI_Animation** | JSON Schema 验证 + Node.js 渲染器 + 自检清单 |
| **guizang-ppt-skill** | 7 问澄清 + 主题隔离 + checklist.md |
| **CyberPPT** | Reference Gate + 证据链 + 阶段确认门 |
| **ppt-master** | 10 条纪律 + spec_lock + 路由分流 + 故障恢复 |

---

> 研究时间：2026-07-07
> 基于 D:\地缘推演台 本地克隆的四个仓库进行对比分析
