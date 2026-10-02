---
type: architecture
tags: [architecture, cwkb, engine, overview]
---

# ConStruct 项目架构总览

> 人脑界面 × 引擎界面 × 文档界面 = 三层认知基础设施

---

## 三层系统关系

```
┌──────────────────────────────────────────────────────────┐
│  人脑界面 · CWKB_Vault（Obsidian）                        │
│  · 人写、人读、人思考                                      │
│  · YAML frontmatter + 双链 + 图谱                         │
│  · 11层知识库 + Special + Templates                       │
│  · ima知识库 = 文档层（存+搜+RAG）                        │
├──────────────────────────────────────────────────────────┤
│  同步层 · construct sync                                  │
│  · Obsidian编辑 → 解析 → 写入SQLite                       │
│  · SQLite变更 → 生成 → 更新Obsidian MD                    │
├──────────────────────────────────────────────────────────┤
│  引擎界面 · construct-engine                              │
│  · 引擎写、引擎读、引擎运行                                │
│  · SQLite DB + Rule JSONs + Python引擎                    │
│  · 4引擎 + CLI + Radar + 采集器                          │
└──────────────────────────────────────────────────────────┤
```

---

## 目录结构对照

### CWKB_Vault（人脑界面）

```
CWKB_Vault/
├── Home.md                    -- 总索引+愿景+推理链
├── 00_Concepts/               -- L0 概念词典（11个）
├── 01_Theory/                 -- L1 理论基础
│   └── ConStruct_Framework_v2_Upgrade_Proposal.md
├── 02_History/                -- L2 历史事件链
├── 03_Data/                   -- L3 数据与事件
├── 04_ThinkTanks/             -- L4 智库研究
├── 05_Academic/               -- L5 学术研究
├── 06_Identity_Archive/       -- L6 主体档案（7份）
├── 07_Relationship_Graph/     -- L7 关系图谱（2份）
├── 08_Constraint/             -- L8 约束层（1份：日本）
├── 09_Incentive/              -- L9 激励层（1份：日本）
├── 10_Objectives/             -- L10 目标层（1份：日本）
├── Special/
│   ├── Event_Chains/          -- 事件链库
│   ├── Strategy_Timeline/     -- 策略空间时间轴
│   ├── Prediction_Graveyard/  -- 预测坟场（1条）
│   ├── Counterexamples/       -- 反例库（1条）
│   ├── Playbooks/             -- 剧本库（1份）
│   ├── Diagnostic_001/        -- 诊断报告#001
│   └── Diagnostic_002/        -- 诊断报告#002
├── Indexes/                   -- 索引文件
├── Templates/                 -- 12个YAML模板
└── ima上传指南.md             -- ima知识库操作指南
```

### construct-engine（引擎界面）

```
construct-engine/
├── db/
│   ├── construct.db           -- SQLite主数据库
│   └── schema.sql             -- Schema定义
├── rules/
│   ├── US_signals.json        -- 美国信号检测规则
│   ├── US_del_rules.json      -- 美国DEL翻译规则
│   ├── Japan_signals.json
│   ├── Japan_del_rules.json
│   └── ...
├── engine/
│   ├── identity_interpreter.py
│   ├── signal_detector.py
│   ├── consistency_checker.py
│   ├── elasticity_tracker.py
│   └── archive_updater.py
├── collectors/
│   ├── del1_collector.py
│   ├── del2_collector.py
│   └── del3_annotator.py
├── generators/
│   ├── archive_md_generator.py
│   ├── diagnostic_generator.py
│   └── radar_generator.py
├── cli/
│   ├── construct.py
│   ├── annotate.py
│   ├── query.py
│   └── check.py
├── radar/
│   ├── index.html
│   └── data.json
├── templates/
│   ├── archive_template.md
│   └── diagnostic_template.md
├── config/
│   ├── subjects.json
│   ├── del_sources.json
│   └── rss_keywords.json
└── docs/
│   ├── ConStruct_Engine_System_Design_v1.0.txt
│   ├── ConStruct_Engine_Architecture.md
│   └── CWKB_v3.0_source.txt
```

---

## 数据流

```
人写Obsidian MD
  ↓
construct sync（解析frontmatter+正文 → 写入SQLite）
  ↓
SQLite DB（引擎真相源）
  ↓
4引擎运行（Identity Interpreter / Signal Detector / Consistency Checker / Elasticity Tracker）
  ↓
输出层
  ├── 诊断报告（Jinja2 → Markdown）
  ├── Radar HTML（静态页面）
  ├── 档案更新（写入SQLite → sync → 更新Obsidian MD）
  └── 信号推送（CLI输出）
```

---

## 文件归属规则

| 内容 | 存在哪里 | 谁读写 |
|------|---------|--------|
| 概念卡/理论卡/智库卡/学术卡 | CWKB_Vault/00~05 | 人写，引擎读 |
| 主体档案 | CWKB_Vault/06 + SQLite | 人写初版，引擎更新 |
| 约束/激励/目标 | CWKB_Vault/08~10 + SQLite | 人写初版，引擎计算更新 |
| 关系图谱 | CWKB_Vault/07 + SQLite | 人写，引擎读 |
| 企业主体档案 | CWKB_Vault/06 + SQLite | 人写初版，引擎更新（同国家主体，但Identity核心不同） |
| DEL翻译规则 | rules/*.json + CWKB_Vault档案内 | 人写JSON，引擎执行 |
| 信号检测规则 | rules/*.json + CWKB_Vault档案内 | 人写JSON，引擎执行 |
| DEL-1/2/3数据 | SQLite del_baseline表 | 引擎写，人通过CLI查看 |
| 行动记录 | SQLite actions表 | 人标注(CLI) + 引擎分析 |
| 弹性历史 | SQLite elasticity_history表 | 引擎计算，人确认 |
| 诊断报告 | CWKB_Vault/Special/ + templates/ | 引擎生成初版，人确认 |
| Radar | construct-engine/radar/ | 引擎生成 |
| ima文档 | ima app | 人手动上传 |

---

## ConStruct_Archive（过渡态）

ConStruct_Archive是v2.x时代的产物，内容已在CWKB_Vault中有更好版本（YAML frontmatter + 双链）。
保留作为历史参考，不再更新。所有新内容写入CWKB_Vault。

---

## workspace根目录散文件

以下文件已归入CWKB_Vault或construct-engine对应目录，根目录保留原文件作为历史备份：

| 原文件 | 归入位置 |
|--------|---------|
| ConStruct_Diagnostic_001_InterestRates.md | CWKB_Vault/Special/Diagnostic_001_InterestRates.md |
| ConStruct_Diagnostic_002_EU_Strategic_Autonomy.md | CWKB_Vault/Special/Diagnostic_002_EU_Strategic_Autonomy.md |
| ConStruct_Framework_v2_Upgrade_Proposal.md | CWKB_Vault/01_Theory/ |
| ConStruct_Engine_System_Design_v1.0.txt | construct-engine/docs/ |
| ConStruct_Identity_Archive_001_USA.md | （已在CWKB_Vault/06_Identity_Archive/美国.md 中有更新版） |
| CWKB_v3.0_source.txt | construct-engine/docs/ |
| ConStruct_Roadmap_v2.0.txt | construct-engine/docs/ |
| ConStruct_Roadmap_and_AI_Strategy.txt | construct-engine/docs/ |

---

*ConStruct Lab · 认知基础设施 — 人脑 × 引擎 × 文档*
