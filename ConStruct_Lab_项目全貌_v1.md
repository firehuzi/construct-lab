# ConStruct Lab — 项目全貌 v1.0

> 地缘政治的分析被叙事锁定了。
> 
> 智库报告在推销立场，媒体标题在放大恐惧，学术论文在自我引用。没有一个工具能回答最简单的问题：**"这个判断从哪里来的？能不能推翻它？"**
>
> ConStruct Lab 用 200 年战争数据、40 年冲突日志和每日新闻脉冲做一件事——**枚举结构上可能的路径，排除逻辑上不可能的路径**。不做概率预测。所有判断锚定在可追溯的数据上，所有假设设计为可被数据反证。
>
> *"Diagnose structures, not predict futures."*
>
> 全球免费开放。

---

## 一、什么是 ConStruct Lab

一个**结构性分析引擎**。输入三层时间尺度的数据：

## 二、分析架构

ConStruct Lab 的分析系统由三个相互独立的维度构成：

### 第一维：本体层（WHAT 被建模）
五种分析对象，由浅入深：

```
物质层 → 主体层 → 制度层 → 叙事层 → 动态层
```

### 第二维：知识生产管线（HOW 知识被生产）
五步管线：

```
现实世界 → 数据采集 → 结构建模 → 分析解释 → 知识产品
```

### 第三维：11层诊断框架（地缘政治的垂直操作化）
从观察到判断的11个层次：

```
L0  世界事件 & 行为观察
L1  行为主体识别
L2  连续性类型（核心Identity — 主体型/秩序型/混合型）
L2b 方法阶段（scope: 0-7，描述身份的表达方式）
L3  存在方式
L4  建构来源（历史印记、创伤锚点、建国神话、制度遗产、文化传统、集体记忆）
L5  维持机制
L6  秩序价值
L7  他者系统
L8  创伤系统
L9  战略选择 → 行动输出
L10 生物类比（六型：保守型-冻结局 / 平衡型 / 创新型 / 意识形态型 / 扩张型 / 共生型）
```

**三层正交意味着**: 同一个主体在不同层上是不同的分析对象。美国在L2上是"交易式Identity"，在L10上是"扩张型"，在L8上有"珍珠港创伤"——这些是正交的，不能混为一谈。

---

## 三、数据基础设施

### 数据栈
```
PostgreSQL + TimescaleDB (system of truth)
    ↑
Neo4j (knowledge graph — 53主体, 8领域, 3数据源)
    ↑
GDELT (daily pulse) + UCDP GED (1989-2025) + COW (1816-2014)
    + FRED (10 economic indicators) + Kaggle War Records + chinatimeline
```

### 核心数据集

| 数据集 | 规模 | 时间跨度 | 用途 |
|---|---|---|---|
| UCDP GED | 41.8万条 | 1989-2025 | 全球冲突事件（致命暴力） |
| GDELT 2.0 | 日更~700条 | 2026.07起 | 新闻情绪实时脉冲 |
| COW | MID+War+Alliance+Territorial | 1816-2014 | 战争/同盟/领土变更骨架 |
| FRED | 10标的 | 日更 | 金融/价格结构化信号 |
| Kaggle War Records | 10,684条 | 1800+ | 1840-1949近代战争补缺 |
| chinatimeline | 101条 | 2018+ | 中国政治事件精标注 |

### 53 主体覆盖

| 层级 | 数量 | 代表 |
|---|---|---|
| Tier1 大国 | 8 | 中美俄日印欧伊以 |
| Tier2 区域强国 | 16 | 澳德法英韩菲沙新等 |
| Tier3 企业+组织 | 29 | HW/TSMC/NVIDIA + UN/NATO/IMF/WTO/BRICS/SCO |

### 双轨采集系统

GDELT每日采集采用双轨架构：
- **actor track**: 47/53 主体关联，按CAMEO国家码匹配 + 别名辅助
- **structural track**: 8 领域事件（金融/AI/产业链/能源/社会/大宗商品/矿产/气候），不要求有主体关联

所有事件入PG时附带：
- `source_id`（溯源链）
- `confidence`（置信度）
- `verification_status`（pending/cross_checked/verified/rejected）
- `source_ref`（数据源标注）

---

## 四、自动化pipeline：八节点日更环

每天 CST 08:00 自动触发，无需人工干预：

```
Schedule (CST 08:00)
    ↓
Collect GDELT ──→ 双轨采集写入PG
    ↓
Verify Loop ──→ 主动学习分桶 → review_queue.json
    ↓
Detect Anomalies ──→ tone暴跌/事件脉冲/结构异常
    ↓
Check Structure ──→ 53主体114验证项 → feedback_rules.json
    ↓
Ingest Events ──→ PG增量 → Neo4j
    ↓
Ingest Prices ──→ FRED 10标的 → Neo4j
    ↓
Generate Map ──→ world_map.html + world_map_data.js
```

### 验证系统

三级验证路径：
1. **cross_checked** (自动): ≥3数据源共现 且 置信度≥0.65
2. **pending** (自动): 进入 review_queue 人工复核
3. **verified/rejected** (人工): 最终状态

**绝不自动标verified** — 这是数据保真的底线。

### 反馈环

如果某个主体的行为持续偏离其结构假设的预测，系统自动：
1. 检测矛盾信号
2. 降低该假设的置信度
3. 累积达阈值 → 推入人工复核队列
4. 人工确认 → 更新结构假设 → 推演重新校准

这是 ConStruct Lab 与所有分析平台的根本区别：**结构诊断被设计为可被证伪**。

---

## 五、分析引擎

### 诊断引擎 (engine_v5.py)

输入: PG数据 + Neo4j图谱 + COW骨架 + actors档案
输出: 11层诊断报告

已实现:
- 53主体 actor_timelines JSON（每份200-400条事件，五类来源标注）
- DeepSeek驱动的11层诊断 (diagnose_actor.py)
- Knowledge层交叉引用 + Wikipedia URL溯源

### 推演引擎（设计就位，待落地）

推演不是预测，是**枚举结构上可能的路径并消除逻辑上不可能的路径**。

核心逻辑:
```
事件 → 打哪层结构 → 加速/阻塞哪些路径 → SUL变化 → 下一步观察点
```

每个推演输出都带**结构性前提标注**：如果Identity诊断错误，则推演在P处失效。

### 结构反证系统 (feedback_rules.json)

53主体的114项验证项，每项都有：
- 预期行为
- GDELT检验查询
- 相反信号定义
- 观察窗口

当行为反证累计超阈值，置信度自动下降，触发人工复核。

---

## 六、可视化与地图

### 世界冲突时间地图

交互式 Leaflet 应用（https://construct-lab.site/map）:
- **UCDP 冲突热点**：126国年度死亡数，比例尺圆，年份滑块(1989-2025)
- **COW 领土变更流**：200年虚线骨架，真实领土坐标
- **GDELT 情绪脉冲**：48h绿/红点
- **结构领域面板**：金融/AI/能源/产业链切换，90天趋势折线图
- **图层独立开关**：右上角三复选框
- **关键缺漏补足**：80+非canonical国家坐标，无数据黑洞
- **Keyless**：Leaflet + OSM底图，零认证零付费

### 与项目站集成

地图作为 `/map` 路由挂入 `construct-lab-site`，与 `/tool`(v2.1诊断工具) 并列。顶部导航工具→地图直接可达。

---

## 七、内容输出体系（九种形态）

```
数据卡片（极简）
    ↓
事件快评（日常）
    ↓
构型迁移预警（自动化内审）
    ↓
时序报告（周期性）
    ↓
构型对比（深度）
    ↓
国别结构诊断（年度锚点）
    ↓
情景推演（高级）
    ↓
叙事考古（长期差异化）

结构词典（独立工具，边跑边建）
```

### P0（已启动）

| 形态 | 状态 |
|---|---|
| 国别结构诊断 | ✅ Tier1 8国已生成 |
| 结构词典 | ✅ 模板已定，首批10条目待写 |
| 事件快评 | 模板已设计，80%自动化待开发 |

### 核心原则（反洗脑四标准）

1. **数据锚定**：每个判断都能追溯到GDELT/COW/UCDP
2. **结构驱动**：结论从Identity→Method→Fear框架推导
3. **叙事识别**：每份报告有"别被哪种叙事忽悠"
4. **不确定性标注**：[高/中/低，依据:…]

---

## 八、技术栈

| 层 | 技术 |
|---|---|
| 数据库 | PostgreSQL + TimescaleDB (SoT), Neo4j (graph) |
| 编排 | n8n (8-node pipeline, Docker) |
| 采集 | Python (gdelt-py, psycopg2, fredapi) |
| 验证 | Python (cross_source + 主动学习分桶) |
| 推理 | DeepSeek API (diagnosis + article generation) |
| 可视化 | Leaflet + OSM + matplotlib + vis.js |
| 站点 | React + Vite + Router + i18next (Firebase Hosting) |
| 容器 | Docker Compose (PG + Neo4j + n8n + runner) |

---

## 九、文件树（核心文件）

```
地缘推演台/
├── construct-engine/          # 主引擎
│   ├── engine_v5.py           # 诊断引擎
│   ├── diagnose_actor.py      # DeepSeek 11层诊断
│   ├── publish_article.py     # 结构诊断文章生成器
│   ├── generate_world_map.py  # 世界地图生成器
│   ├── collect_gdelt.py       # GDELT双轨采集
│   ├── verify_events.py       # 三级验证引擎
│   ├── detect_anomaly.py      # 异常预警
│   ├── detect_structure_contradictions.py  # 结构反证检测
│   ├── war_records_collector.py  # COW+Kaggle+chinatimeline合并导入
│   ├── acled_collector.py     # ACLED采集（账号未通过）
│   ├── cow_collector.py       # COW骨架
│   ├── crosslink_actors.py    # Knowledge层交叉引用
│   ├── ingest_to_archive.py   # PG→Neo4j
│   ├── visualize_three_layers.py  # matplotlib三图
│   ├── visualize_interactive.py   # vis.js时间轴
│   ├── generate_verification_items.py  # 结构验证项生成
│   ├── feedback_rules.json    # 53主体114验证项
│   ├── actor_timelines/       # 53份骨架JSON
│   ├── diagnostics/           # 诊断报告Markdown
│   ├── content/articles/      # 结构诊断文章
│   ├── content/lexicon/       # 结构词典
│   └── visuals/               # 地图HTML+数据JS
├── construct-stack/           # Docker栈
│   ├── docker-compose.yml     # PG+Neo4j+n8n+runner
│   ├── init-pg.sql            # 表结构+种子数据
│   └── scripts/               # n8n runner脚本
├── construct-lab-site/        # 品牌站
│   └── public/map.html        # 地图路由
└── actors/                    # 53主体档案（MD）
```

---

## 十、当前状态（2026-07-28）

| 模块 | 状态 | 备注 |
|---|---|---|
| 数据采集 | ✅ | GDELT日更 + UCDP+COW+FRED全量 |
| 验证环 | ✅ | 三级分桶自动运行 |
| 异常预警 | ✅ | tone/事件/结构三元检测 |
| 结构反证 | ✅ | 53主体114验证项就位 |
| Neo4j图谱 | ✅ | 42万Event + 53Actor + 8Domain |
| 世界地图 | ✅ | 交互式，Tier1 8国诊断已生成 |
| 结构诊断文章 | ✅ | prompt 11轮迭代 |
| 内容形态规划 | ✅ | 九种形态文档落地 |
| 自动化pipeline | ✅ | 八节点全绿日更 |
| ACLED | ❌ | 个人邮箱被拒 |
| 部署 | ⏳ | 地图文件已就位，待推Firebase |
| 推演引擎代码 | ⏳ | 逻辑已通，待写project_paths.py |
| 事件快评自动化 | ⏳ | 模板已设计 |
| 结构词典条目 | ⏳ | 模板已定，首批10条待写 |

---

## 十一、团队与署名

- **系统**: ConStruct Lab — Structural diagnosis. Not structural talk.
- **实验室**: 刃研社 / SCALPEL LAB — Cutting Systems, Rebuilding Meaning
- **Operator**: 没胡子土匪
- **公众号**: 地缘推演台
- **Substack**: constructlab.substack.com
- **站点**: construct-lab.site

---

*ConStruct Lab v1.0 — July 2026*
