# ConStruct Engine v5.0 — 开放集成技术架构

> **设计哲学**: 世界模型自己建，基础设施全部借。  
> **核心原则**: 10% 原创 + 90% 成熟开源项目整合，每一层只借鉴一个成熟项目  
> **时间分配**: 全部花在 World Model（世界模型）上  
> **日期**: 2026-06-26（v2: 新增 Resource Layer）

---

## 一、总览：四层架构

```
                        ConStruct Engine v5.0
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         AI Layer        Knowledge Layer    Data Layer
              │                │                │
     ⑨ LLM Pool         ③ Neo4j           ① Airbyte
        (GPT/Claude/       (知识图谱)         (数据采集)
         Gemini/DS)         │                │
              │          ④ LlamaIndex       ② n8n
     ⑩ 4 Engines           (文档RAG)         (工作流编排)
        (Identity/        ⑤ Meilisearch
         Signal/            (全文搜索)
         Consistency/     ⑥ Dify
         SUL)               (Workflow/RAG/
              │              Agent管理)
              │           ⑦ PostgreSQL
              │              + TimescaleDB
              │              (事件时序DB)
              │           ⑧ MinIO
              │              (对象存储)
              │                │
              └────────┬───────┘
                       │
                  Resource Layer
                       │
        ┌──────┬───────┼───────┬──────┐
        │      │       │       │      │
      地图   图表   网络图   时间轴  特殊数据
    Natural  ECharts Cytoscape vis-  GDELT/
     Earth   Plotly  Sigma.js  timeline ACLED
    OSM/QGIS                   Mermaid Submarine
    MapLibre                           Cable Map
                   ┌─────────────────┐
                   │ 参考项目:        │
                   │ OpenBB/Haystack  │
                   │ LangGraph/CrewAI │
                   └─────────────────┘
```

**四层职责**:

| 层 | 定位 | 原则 |
|----|------|------|
| **AI Layer** | 诊断引擎 + 模型池 | 不绑定单一模型，即插即换 |
| **Knowledge Layer** | 知识存储/检索/管理 | 数据库都不自己造 |
| **Data Layer** | 数据采集 + 工作流 | ETL全部借Airbyte |
| **Resource Layer** | 公共基础设施 | 地图/图表/事件源——可用不可控，可替换 |

---

## 二、逐层详解

### 第一层：数据采集 — Airbyte

| 维度 | 详情 |
|------|------|
| **项目** | [Airbyte](https://airbyte.com) — 开源数据集成平台 |
| **GitHub** | airbytehq/airbyte (17k+ stars) |
| **核心能力** | 500+ 预建 Connector，低代码/无代码构建新连接器 |
| **ConStruct 映射** | 替代当前手工 pipeline.py 的数据采集部分 |

**Connector 矩阵**:

| 数据源 | Airbyte Connector | 数据用途 |
|--------|-------------------|----------|
| GDELT | HTTP API / Custom | 全球事件实时流 |
| FRED | 现有社区 Connector | 宏观经济指标 |
| IMF SDMX | 现有 Connector | 国际金融数据 |
| World Bank | 社区 Connector | 发展指标 |
| RSS Feeds | RSS Connector | 媒体信号采集 |
| GitHub | GitHub Connector | 开源情报（Palantir/DeepSeek等） |
| Reuters | HTTP API Connector | 新闻事件流 |
| CSV 档案 | File Connector | 自有主体档案同步 |

**为什么是 Airbyte 不是 Meltano**:  
- Airbyte连接器生态500+，Meltano更偏数据工程团队  
- Airbyte UI 友好，单人即可运维  
- Airbyte 的 Connector Builder 支持低代码建新源  
- Meltano 作为备选，适合日后需要更轻量部署时切换

**当前状态映射**:  
```
旧: pipeline.py → GDELT API / FRED CSV / 本地缓存
新: Airbyte → GDELT / FRED / IMF / RSS / File Connectors
```

---

### 第二层：工作流编排 — n8n

| 维度 | 详情 |
|------|------|
| **项目** | [n8n](https://n8n.io) — 开源工作流自动化平台 |
| **GitHub** | n8n-io/n8n (55k+ stars) |
| **核心能力** | 可视化工作流编排，1000+ 集成节点，内置 AI Agent |

**ConStruct 工作流设计**:

```
触发: Cron 每小时
  ↓
[Airbyte: 拉取最新事件] → [GPT: 识别涉及主体] → [Neo4j: 查询已知关联]
  ↓                                                    ↓
[Signal Detector: 规则触发] ← [GPT: 评估信号严重性] ←┘
  ↓
[SUL Scorer: 更新不确定性] → [写入 PostgreSQL]
  ↓
[Radar 仪表盘推送更新]
```

**关键节点**:
- **Cron Trigger**: 每小时/每天定时触发
- **HTTP Request**: 调用外部 API
- **OpenAI / Claude**: AI 分析节点
- **PostgreSQL / Neo4j**: 数据库写入
- **Webhook**: 推送到 Radar 前端

**为什么是 n8n**:  
- 可视化编排，替代当前手工 Python 脚本  
- 内置 AI Agent 节点，天然支持 LLM 调用  
- 以后 AI Agent 很好接（本身就是 AI-native 设计）  
- 一个人运维完全够用

**当前状态映射**:
```
旧: run.py 手动执行 → pipeline.py → engine.py → 写 JSON
新: n8n workflow 自动编排 → Airbyte触发 → Neo4j+PG写入 → Radar推送
```

---

### 第三层：知识图谱 — Neo4j

| 维度 | 详情 |
|------|------|
| **项目** | [Neo4j](https://neo4j.com) — 全球最成熟的图数据库 |
| **核心能力** | Cypher 查询语言，原生图存储，Graph Data Science 库 |

**ConStruct 图谱模型**:

```cypher
// 节点类型
(:Country {code, name, config, dna_profile})
(:Organization {code, name, type})
(:Enterprise {code, name, sector})
(:Scenario {code, name, coupling_level})
(:Event {id, date, gdelt_id, severity, summary})
(:Signal {id, type, direction, confidence})
(:Method {name, phase})  // 方法/阶段

// 关系类型
(:Country)-[:INFLUENCES {weight}]->(:Country)
(:Country)-[:PARTICIPATES_IN]->(:Scenario)
(:Country)-[:HOSTS]->(:Enterprise)
(:Event)-[:INVOLVES]->(:Country)
(:Event)-[:BELONGS_TO]->(:Scenario)
(:Event)-[:TRIGGERS {lag_days}]->(:Event)
(:Country)-[:ADOPTS]->(:Method)
(:Signal)-[:DETECTED_IN]->(:Event)
(:Country)-[:IDENTIFIES_AS]->(:Identity)
```

**核心查询示例**:
```cypher
// 台海事件链：谁影响谁
MATCH (e1:Event)-[:TRIGGERS*1..3]->(e2:Event)
WHERE e1.scenario = 'TaiwanStrait'
RETURN e1, e2

// 中国的信号图谱
MATCH (c:Country {code:'CN'})<-[:INVOLVES]-(e:Event)-[:BELONGS_TO]->(s:Scenario)
RETURN c, e, s

// ICC 缺口监控
MATCH (c:Country)-[:HAS_SIGNAL]->(sig:Signal)
WHERE sig.type = 'ICC_gap'
RETURN c.code, sig.direction, sig.confidence
```

**为什么是 Neo4j**:  
- 地缘政治天然是图结构（主体→影响→主体→场景→事件）  
- Cypher 查询比 SQL JOIN 直观 10 倍  
- Interaction Layer 以后直接建立在图上  
- Graph Data Science 库可以做中心性分析、社区检测

**当前状态映射**:
```
旧: SQLite → 关系表 → 手动 JOIN 查询
新: Neo4j → 原生图 → Cypher 图谱查询
```

---

### 第四层：文档知识库 — LlamaIndex

| 维度 | 详情 |
|------|------|
| **项目** | [LlamaIndex](https://llamaindex.ai) — RAG 框架 |
| **核心能力** | 文档索引、自动分块、向量检索、图谱增强 RAG |

**ConStruct 档案索引架构**:

```
主体档案 (77 Markdown)
    ↓
LlamaIndex Document Loader
    ↓
自动分块 (按 DNA维度、ICC分析、历史事件)
    ↓
向量索引 + 知识图谱索引（双路）
    ↓
查询: "日本的经济能力与Identity期望是否正在脱钩？"
    ↓
RAG → 检索相关档案片段 → GPT 生成分析
```

**关键特性**:
- **自动索引**: 每次档案更新自动重建索引
- **事件关联**: 新事件进来，自动匹配相关主体档案
- **多跳推理**: "中国→影响俄罗斯→能源→影响欧盟"
- **图谱增强 RAG**: LlamaIndex 原生支持 Neo4j 集成

**为什么是 LlamaIndex 不是 LangChain**:  
- LlamaIndex 专注数据和检索，LangChain 更偏 Agent 编排  
- 文档索引是 LlamaIndex 的核心优势  
- 与 Neo4j 的原生集成更好

**当前状态映射**:
```
旧: Markdown 文件 → construct_bridge.py → JSON → 手工查询
新: Markdown → LlamaIndex 索引 → 自动 RAG → AI 辅助分析
```

---

### 第五层：全文搜索 — Meilisearch

| 维度 | 详情 |
|------|------|
| **项目** | [Meilisearch](https://meilisearch.com) — 闪电般快速的搜索引擎 |
| **核心能力** | 毫秒级搜索、中文分词原生支持、容错搜索 |

**vs OpenSearch 的选择**:

| 维度 | Meilisearch | OpenSearch |
|------|-------------|------------|
| 部署复杂度 | 单二进制，零配置 | 需要 Java + 集群配置 |
| 中文支持 | 原生 jieba 分词 | 需要 IK 插件 |
| 资源占用 | ~50MB | ~1GB+ |
| 搜索速度 | 毫秒级 | 毫秒级（需要调优） |
| 适合场景 | 中小规模，快速迭代 | 大规模，数据分析 |

**ConStruct 选择 Meilisearch 的理由**:  
- 单人项目，不需要集群  
- 中文分词原生支持（地缘政治大量中文文献）  
- 容错搜索（用户输入"冻结局"笔误时仍能找到）

**索引设计**:
```
索引: actors (主体)
索引: events (事件)
索引: scenarios (场景)
索引: analyses (分析报告)
索引: publications (公众号文章)
```

**典型查询**:
```
"日本 经济"     → 所有涉日经济事件/分析/档案
"台海 芯片"     → 台海场景 + AI芯片场景交叉
"冻结局"        → 所有冻结局主体
```

---

### 第六层：知识库管理 — Dify

| 维度 | 详情 |
|------|------|
| **项目** | [Dify](https://dify.ai) — LLM 应用开发平台 |
| **GitHub** | langgenius/dify (80k+ stars) |
| **核心能力** | 可视化 Workflow、RAG 管道、Agent、模型管理 |

**ConStruct 使用 Dify 的方式**（不是你想象的那种）:

```
❌ 不是：做个聊天机器人问"台湾会打仗吗"
✅ 而是：用 Dify Workflow 构建分析流水线

Dify Workflow 设计:
  [输入: 触发事件]
      ↓
  [节点1: LlamaIndex RAG 检索相关档案]
      ↓
  [节点2: GPT-4 做 Identity 解释]
      ↓
  [节点3: 规则引擎做 Signal Detection]
      ↓
  [节点4: GPT-4 做 SUL 评估]
      ↓
  [输出: 诊断报告 → 推送 Radar]
```

**为什么是 Dify**:  
- 可视化编排 LLM 调用，替代硬编码 Python  
- 内置 RAG + Agent + 模型管理  
- 以后 Radar 前端可以通过 API 接 Dify workflow  
- 模型切换（GPT→Claude→DeepSeek）零代码

**Dify 的角色**:  
Dify 不是面向终端用户的聊天工具，而是 **ConStruct 诊断引擎的操作系统**。

---

### 第七层：事件数据库 — PostgreSQL + TimescaleDB

| 维度 | 详情 |
|------|------|
| **项目** | [PostgreSQL](https://postgresql.org) + [TimescaleDB](https://timescale.com) |
| **核心能力** | 关系型存储 + 时序数据超表（Hypertable） |

**为什么不要自己设计数据库**:

```
旧方案问题:
- SQLite 单文件 → 并发差、无时序优化
- 手工设计 Schema → 每次迭代都要 migrate
- 无时序查询优化 → 查询"过去30天信号趋势"很慢

PostgreSQL + TimescaleDB 方案:
- PostgreSQL: 存储主体档案、事件、信号、规则
- TimescaleDB Hypertable: 存储时序数据（GDELT事件流、经济指标）
- 自动分区、自动压缩、时序查询毫秒级
```

**表设计（核心）**:
```sql
-- 时序表 (TimescaleDB Hypertable)
CREATE TABLE events (
    time TIMESTAMPTZ NOT NULL,
    gdelt_id TEXT,
    source_actor TEXT,
    target_actor TEXT,
    event_code TEXT,
    goldstein_scale FLOAT,
    avg_tone FLOAT,
    summary TEXT,
    metadata JSONB
);
SELECT create_hypertable('events', 'time');

-- 信号时序表
CREATE TABLE signals (
    time TIMESTAMPTZ NOT NULL,
    actor_code TEXT,
    signal_type TEXT,     -- ICC_gap | identity_drift | capability_decay
    direction TEXT,        -- widening | narrowing | stable
    confidence FLOAT,
    source_event_id TEXT
);
SELECT create_hypertable('signals', 'time');
```

**时序查询优势**:
```sql
-- 过去30天中国 ICC 缺口趋势
SELECT time_bucket('1 day', time) AS day,
       direction,
       AVG(confidence) as avg_confidence
FROM signals
WHERE actor_code = 'CN'
  AND signal_type = 'ICC_gap'
  AND time > NOW() - INTERVAL '30 days'
GROUP BY day, direction
ORDER BY day;
```

---

### 第八层：对象存储 — MinIO

| 维度 | 详情 |
|------|------|
| **项目** | [MinIO](https://min.io) — S3 兼容对象存储 |
| **核心能力** | 私有部署、S3 API 兼容、高性能 |

**ConStruct 存储对象**:
```
minio-bucket/
├── pdf/           # 研究报告PDF
├── images/        # 图表截图、可视化输出
├── reports/       # 生成的分析报告 (HTML/PDF)
├── exports/       # 数据导出 (CSV/JSON)
├── backups/       # PostgreSQL + Neo4j 备份
└── models/        # 后续可能需要的模型文件
```

**为什么不是直接存文件系统**:  
- S3 API 标准，以后任何工具都能读  
- 备份/恢复方便  
- 版本控制  
- 日后迁移到云 S3 零改动

---

### 第九层：AI 模型池

| 维度 | 详情 |
|------|------|
| **设计** | 不绑定任何单一模型 |
| **策略** | 按任务类型路由到最优模型 |

**任务路由矩阵**:

| 任务 | 推荐模型 | 原因 |
|------|---------|------|
| Identity 解释 | Claude Opus | 长上下文、结构化推理强 |
| 信号检测 | GPT-4o | 速度快、规则提取稳定 |
| 多语言翻译 | DeepSeek | 中文母语优势、成本低 |
| RAG 检索 | 嵌入模型 (text-embedding) | 检索精度 |
| 批量摘要 | GPT-4o-mini | 成本低、速度快 |
| 深度分析报告 | Claude Opus / GPT-5 | 推理深度 |

**为什么最后考虑 AI**:  
- 模型迭代太快，现在绑定=三个月后过时  
- 所有 AI 层通过 API 抽象，随时可换  
- Dify / n8n 已经提供了模型切换机制

---

### 第十层：可视化前端 — ECharts + MapLibre + Cytoscape.js

| 维度 | 详情 |
|------|------|
| **图表** | [Apache ECharts](https://echarts.apache.org) — 雷达图/桑基图/力导图/热力图/时间轴/世界地图全覆盖 |
| **Web地图** | [MapLibre](https://maplibre.org) — Mapbox 开源替代，国家热度/事件/雷达全部可渲染 |
| **网络图** | [Cytoscape.js](https://js.cytoscape.org) — 关系网络可视化，知识图谱展示首选 |
| **备选网络图** | [Sigma.js](https://sigmajs.org) — 网页端大图渲染，速度快 |
| **时间轴** | [vis-timeline](https://visjs.github.io/vis-timeline) — 事件自动排列，交互式时间线 |
| **流程图** | [Mermaid](https://mermaid.js.org) — Markdown 原生，所有文档统一用 |
| **Python图表** | [Plotly](https://plotly.com) — Notebook/分析场景使用 |

**为什么是 ECharts 而不是 D3**:  
- ECharts 声明式配置，D3 命令式——前者更适合诊断工具输出标准图表  
- ECharts 内置雷达图（DNA）、桑基图（事件流）、力导图（关系网）——恰好是 ConStruct 的核心可视化需求  
- 中文文档质量极高，社区活跃

**ConStruct 可视化矩阵**:

| ConStruct 概念 | ECharts 图表类型 | 说明 |
|---------------|-----------------|------|
| DNA 四维剖面 | 雷达图 (radar) | D1-D4 四轴雷达 |
| ICC 缺口趋势 | 双轴折线图 + 面积图 | Capability vs Identity_expectation |
| 事件传播链 | 桑基图 (sankey) | 场景→主体→事件 流向 |
| 主体关系网 | 力导图 (force) | 影响权重可视化 |
| SUL 五维评分 | 雷达图 (radar) | 意图/能力/执行/反应/不透明 |
| 信号时间线 | 时间轴 + 热力图 | GDELT 事件流热度 |
| 场景耦合矩阵 | 热力图 | 场景×场景 连锁等级 |
| 全球事件分布 | MapLibre 世界地图 | 事件地点 + 严重性气泡 |

**当前状态映射**:
```
旧: Chart.js 静态雷达图
新: ECharts 雷达图 + MapLibre 地图 + Cytoscape 网络图 + vis-timeline 时间轴
```

---

## 三、Resource Layer（资源层）— 公共基础设施

> **定位**: 不是 ConStruct 的数据，而是 ConStruct 长期依赖的"公共基础设施"。  
> **原则**: 可用不可控，可替换。任何资源停止维护或收费，只替换资源层，不重写上层世界模型。

### 3.1 世界底图

| 资源 | 用途 | 许可 |
|------|------|------|
| **[Natural Earth](https://www.naturalearthdata.com)** | GIS 默认世界地图数据：国家边界/河流/港口/海洋/地形 | 免费开源 |
| **[OpenStreetMap](https://www.openstreetmap.org)** | 港口/铁路/机场/海峡/管道等精细地理数据 | 开放数据 |
| **[QGIS](https://qgis.org)** | GIS 界的 Photoshop，台湾海峡/北极/南海等专题地图制作 | 免费开源 |

**ConStruct 使用场景**:  
- Natural Earth → 世界底图数据源  
- OpenStreetMap → 关键地缘节点详细数据（港口/海峡/军事基地）  
- QGIS → 专题地图制作（台海/南海/北极航线）

### 3.2 统计数据

| 资源 | 用途 | 推荐度 |
|------|------|--------|
| **[Our World in Data](https://ourworldindata.org)** | GDP/人口/教育/能源/AI 等全领域高质量数据 | ★★★★★ |
| **[World Bank Open Data](https://data.worldbank.org)** | 全球发展指标 | ★★★★ |
| **[IMF Data](https://www.imf.org/en/Data)** | 国际金融/贸易/宏观数据 | ★★★★ |
| **[UN Data](https://data.un.org)** | 联合国统计数据库 | ★★★ |

**ConStruct 使用场景**:  
- Our World in Data → ICC 公式中的 Capability 数据（GDP/人口/教育）  
- IMF → 金融场景数据  
- World Bank → 发展指标、基础设施数据

### 3.3 全球事件数据库

| 资源 | 用途 | 说明 |
|------|------|------|
| **[GDELT Project](https://www.gdeltproject.org)** | 全球最大事件数据库，每日数百万新闻自动事件提取 | 已集成 pipieline.py，作为 Airbyte 数据源 |
| **[ACLED](https://acleddata.com)** | 冲突/战争/暴乱数据，全球最权威 | 军事场景专用 |

**ConStruct 使用场景**:  
- GDELT → 事件流驱动 Signal Detector  
- ACLED → 军事冲突场景推演数据源

### 3.4 地缘政治特殊数据源

| 资源 | 用途 | 场景 |
|------|------|------|
| **[Submarine Cable Map](https://www.submarinecablemap.com)** | 海底光缆分布 | AI/金融/互联网基础设施分析 |
| **[MarineTraffic](https://www.marinetraffic.com)** | 实时船舶位置 | 红海/霍尔木兹/马六甲航运监控 |
| **[OpenSky Network](https://opensky-network.org)** | 开源航班跟踪 | 军事/外交/空中走廊分析 |
| **[NASA Earthdata](https://www.earthdata.nasa.gov)** | 免费卫星数据 | 地形变化/资源分布 |
| **[Copernicus Programme](https://www.copernicus.eu)** | 欧盟免费卫星数据 | 环境/农业/灾害监测 |

**ConStruct 使用场景**:  
- Submarine Cable Map → AI芯片场景（光缆断点=全球算力中断）  
- MarineTraffic → 红海/霍尔木兹场景（航运中断信号）  
- OpenSky → 外交危机（专机异常飞行模式）

### 3.5 知识图谱展示

| 资源 | 用途 |
|------|------|
| **[GraphXR](https://graphxr.dev)** | Neo4j 图谱可视化展示，Demo 效果极佳 |
| **[Cytoscape.js](https://js.cytoscape.org)** | 网页端交互式图谱渲染 |

### 3.6 资源层总览：10个核心依赖

| 类型 | 推荐 | 关键理由 |
|------|------|---------|
| 世界地图 | Natural Earth | GIS 默认标准 |
| 街道地图 | OpenStreetMap | 全球覆盖最全 |
| GIS | QGIS | 免费版 ArcGIS |
| 图表 | Apache ECharts | 雷达图/桑基图/力导图全覆盖 |
| 网络图 | Cytoscape.js | 知识图谱展示标准 |
| 时间轴 | vis-timeline | 事件自动排列 |
| 流程图 | Mermaid | Markdown 原生 |
| 宏观数据 | Our World in Data | 质量最高 |
| 全球事件 | GDELT | 已集成，规模最大 |
| 卫星数据 | NASA Earthdata | 免费无限制 |

---

## 四、参考项目详解

### ① OpenBB — 金融数据平台参考

**借鉴价值**: ★★★★★

**为什么参考**:
- OpenBB 解决的核心问题 = ConStruct 的镜像问题：数据源高度碎片化
- 它的 **Provider → Data Model → Extension** 架构可以直接借鉴
- 特别是它的 "数据统一层" 设计模式

**借鉴内容**:
```
OpenBB 模式:
  数据源 → Provider 适配层 → 统一数据模型 → 用户查询

ConStruct 对应:
  GDELT/FRED/RSS → Airbyte Connector → Neo4j图谱模型 → diagnostic query
```

**不照搬**: OpenBB 面向金融市场，ConStruct 面向地缘政治，数据模型完全不同，但架构思想可以复用。

---

### ② Haystack — 知识检索参考

**借鉴价值**: ★★★★

**为什么参考**:
- Haystack 的 Pipeline 架构（检索→排序→生成）可以直接套用
- 特别是它的 **多模态检索**（文本+表格+图像）能力

**借鉴场景**:
```
ConStruct 诊断检索流:
  [查询: "日本经济衰退对安全政策的影响"]
      ↓
  [Retriever: Meilisearch + Neo4j 双路检索]
      ↓
  [Ranker: 按相关性+时效性排序]
      ↓
  [Generator: GPT 生成诊断报告]
```

**与 LlamaIndex 的分工**:  
LlamaIndex 负责档案索引，Haystack 负责多模态检索管道。两者互补不冲突。

---

### ③ LangGraph — Agent 编排参考

**借鉴价值**: ★★★★★

**为什么参考**:
LangGraph 是 ConStruct **Interaction Layer 的理想形态**。

**ConStruct 的 Agent 图谱**:
```python
# 伪代码：未来 ConStruct Agent 编排
graph = StateGraph(ConStructState)

graph.add_node("event_receiver", receive_event)
graph.add_node("identity_interpreter", interpret_identity)
graph.add_node("signal_detector", detect_signals)
graph.add_node("consistency_checker", check_consistency)
graph.add_node("sul_scorer", score_sul)
graph.add_node("report_generator", generate_report)

graph.add_edge("event_receiver", "identity_interpreter")
graph.add_conditional_edges(
    "signal_detector",
    route_by_severity,
    {"critical": "alert", "high": "sul_scorer", "low": "report_generator"}
)
```

**关键优势**:  
- 状态图天然匹配 ConStruct 的 4 引擎流程  
- 条件路由（critical→alert / low→report）  
- 可插拔 Agent（以后可以引入军事Agent、金融Agent）

---

### ④ CrewAI — 多 Agent 协作参考

**借鉴价值**: ★★★★

**未来场景**:
```
ConStruct Multi-Agent Crew:

[军事 Agent]        [金融 Agent]        [AI Agent]
   ↓                    ↓                   ↓
   └────────────────────┼───────────────────┘
                        ↓
              [外交 Agent: 综合诊断]
                        ↓
              [主编 Agent: 生成报告]
```

**为什么是未来**:  
- 当前 ConStruct 规模不需要多 Agent  
- Beta 阶段以后，当场景推演需要多领域专家协同时启用  
- CrewAI 的 role-based Agent 设计很适合

---

## 五、不要碰的东西

| 项目 | 为什么不碰 | 以后什么时候考虑 |
|------|----------|-----------------|
| **Kubernetes** | 一个人运维找死。Docker Compose 足够 | 有团队后 |
| **Spark** | 数据量不到 TB 级别完全没必要 | 处理全球全量 GDELT 时 |
| **Kafka** | Airbyte + n8n 的事件驱动已够用 | 需要亚秒级实时流时 |
| **Hadoop** | 过时且重 | 永远不需要 |

---

## 六、迁移路线图

### Phase 0: 基础设施搭建（2周）

```
目标: 把所有开源项目装好，能跑通
├── Docker Compose 一键启动
│   ├── PostgreSQL + TimescaleDB
│   ├── Neo4j
│   ├── Meilisearch
│   ├── MinIO
│   ├── Airbyte
│   └── n8n
├── Neo4j 导入现有 46 主体节点 + 关系
├── Meilisearch 索引全部 77 档案
├── LlamaIndex 为档案建立向量索引
└── Resource Layer: 下载 Natural Earth 地图数据 → MinIO
```

### Phase 1: 数据管道切换（2周）

```
目标: pipeline.py → Airbyte + n8n
├── Airbyte 配置 GDELT / FRED / RSS 连接器
├── n8n 构建事件采集 → 识别 → 写库流水线
├── 验证：一周数据与旧 pipeline.py 对比
└── 切换：关闭 pipeline.py，启用 n8n workflow
```

### Phase 2: 知识图谱迁移（2周）

```
目标: SQLite → Neo4j + PostgreSQL
├── 主体档案 → Neo4j 节点 + 关系
├── 事件流 → PostgreSQL + TimescaleDB 时序表
├── 场景耦合 → Neo4j 图谱关系
├── 写 Cypher 查询替代 JSON 遍历
└── 验证：查询结果与旧系统一致
```

### Phase 3: 引擎重塑（3周）

```
目标: 4 引擎 Python 脚本 → Dify Workflow + LlamaIndex RAG
├── Identity Interpreter → Dify Workflow + LlamaIndex RAG
├── Signal Detector → Dify Workflow + 规则引擎
├── Consistency Checker → Neo4j 图谱查询
├── SUL Scorer → Dify Workflow + GPT
├── Radar 可视化 → ECharts 雷达图 + MapLibre 地图 + Cytoscape 网络图
└── 仪表盘 → 接 PostgreSQL 实时数据
```

### Phase 4: AI 增强（持续）

```
目标: 模型池接入，任务智能路由
├── Dify 配置多模型
├── 任务路由规则
├── RAG 精度调优
└── Agent 协作原型（CrewAI）
```

### Phase 5: World Model（长期）

```
目标: 真正花时间在这里
├── 事件传播网络（LangGraph）
├── 场景推演引擎
├── 多 Agent 协作诊断
└── World Model Engine
```

---

## 七、当前状态 → 目标状态对照

| 层 | 当前 (v4.1) | 目标 (v5.0) | 迁移成本 |
|----|------------|-------------|---------|
| 数据采集 | pipeline.py 手工 | Airbyte 500+ Connector | 低 |
| 工作流 | run.py 手动 | n8n 自动编排 | 低 |
| 知识图谱 | SQLite + JSON | Neo4j | 中 |
| 文档索引 | 文件系统 grep | LlamaIndex RAG | 中 |
| 全文搜索 | 无 | Meilisearch | 低（新增） |
| 知识管理 | Python 脚本 | Dify Workflow | 高 |
| 事件数据库 | SQLite | PostgreSQL+TimescaleDB | 中 |
| 对象存储 | 本地文件 | MinIO S3 | 低 |
| AI | 硬编码 GPT 调用 | Dify 模型池路由 | 中 |
| Radar | 静态 HTML | 接 n8n webhook 实时 | 低 |
| 可视化 | Chart.js 静态 | ECharts+MapLibre+Cytoscape | 低 |
| 世界底图 | 无 | Natural Earth + OSM + QGIS | 低（新增） |
| 宏观数据 | 手工CSV | Our World in Data + IMF | 低 |
| 地缘空间数据 | 无 | SubmarineCableMap/OpenSky/MarineTraffic | 低（新增） |

---

## 八、关键决策记录

| 决策 | 选择 | 替代方案 | 原因 |
|------|------|---------|------|
| 数据采集 | Airbyte | Meltano | 连接器生态更大 |
| 工作流 | n8n | Temporal | 轻量、AI原生、单人友好 |
| 知识图谱 | Neo4j | ArangoDB | 生态最成熟、Cypher最直观 |
| 文档索引 | LlamaIndex | LangChain | 专注数据检索 |
| 全文搜索 | Meilisearch | OpenSearch | 轻量、中文原生 |
| 知识管理 | Dify | 自建 | Workflow+RAG+Agent三位一体 |
| 数据库 | PostgreSQL+TSDB | SQLite | 时序优化、生态完善 |
| 对象存储 | MinIO | 本地文件 | S3兼容、备份方便 |
| 图表 | ECharts | D3.js | 声明式、雷达/桑基/力导内置 |
| Web地图 | MapLibre | Leaflet | Mapbox兼容、矢量瓦片 |
| 网络图 | Cytoscape.js | vis-network | 知识图谱展示标准 |
| 世界底图 | Natural Earth | 自绘 | GIS行业标准 |
| 宏观数据 | Our World in Data | 自采 | 质量最高、覆盖最广 |
| 全球事件 | GDELT | 自采新闻 | 已集成、规模最大 |

---

## 附录：Docker Compose 参考

```yaml
# construct-stack/docker-compose.yml (Phase 0 起步)
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: construct
      POSTGRES_USER: construct
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["./data/pg:/var/lib/postgresql/data"]

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    ports: ["7474:7474", "7687:7687"]
    volumes: ["./data/neo4j:/data"]

  meilisearch:
    image: getmeili/meilisearch:latest
    environment:
      MEILI_MASTER_KEY: ${MEILI_KEY}
    ports: ["7700:7700"]
    volumes: ["./data/meili:/meili_data"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes: ["./data/minio:/data"]

  airbyte:
    image: airbyte/airbyte:latest
    ports: ["8000:8000", "8006:8006"]
    volumes: ["./data/airbyte:/data"]

  n8n:
    image: n8nio/n8n:latest
    ports: ["5678:5678"]
    environment:
      N8N_AI_ENABLED: "true"
    volumes: ["./data/n8n:/home/node/.n8n"]
```

---

*ConStruct Lab — Structural diagnosis. Not structural talk.*
