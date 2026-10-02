# ConStruct 数据层框架与技术方案（V5 数据保真基座）

> 目的：攻克硬伤①「数据层不保真（来源主观 / 不充分 / 错误）」。
> 原则：**保真 = 可追责（traceable），不是声称客观**。结构性诊断本就带解释立场，客观是伪命题；能做的，是让每条数据可溯源、可交叉印证、可审计。
> 日期：2026-07-25
> 关联：V2.2 硬伤诊断、V5 迁移路线图（P0–P2）、V4.1 engine.py / pipeline.py

---

## 0. 设计原则（从 V4.1 病灶反推）

| V4.1 的病 | 本方案的对策 |
|---|---|
| `pipeline.py` 有 `manual_input()` 静默手动回退 | **自动优先，手动兜底但强制降权 + 标注**（confidence=low，打 `manual` 标），绝不填默认值 |
| API 失败直接填 `oil_price:82` 等默认值 | 源失败 → 标 `source_failed`，**不回退默认值**，留空等补采 |
| JSON 存储、无溯源 | **显式 `(:Source)` 节点 + `:HAS_SOURCE` 边**，每条记录挂来源/时间/置信度 |
| 写死 46 主体 | 导入读 `actors/` 树（**47**），不写死 |
| 档案无引用（实测 `actors/` 64 篇 md 0 处 http 链接） | **Knowledge 层也要内联引用**：每条 claim → source |

---

## 1. 数据分类：两层分离

数据层必须切成**慢/快**两层，保真手段不同，不能混。

### 1.1 Knowledge 层（静态 / 策展 · 慢）
- **内容**：47 主体档案、构型映射、场景定义、关系标注。
- **来源**：`actors/` 树（md）+ `ConStructLab_ConfigMapping.md`（已策展、权威）。
- **保真手段**：git 版本控制 + **档案内联引用**（每条 claim → source 链接/文献）+ 人工策展。
- **当前缺口（实测）**：`actors/` 64 篇 md **无任何 http 链接 / 来源标注** → Knowledge 层目前也不可溯源。→ 待办：策展补引（可作为 Phase 0 轻量任务）。

### 1.2 Signal 层（动态 / 采集 · 快）
- **内容**：事件（GDELT）、经济指标（FRED）、新闻叙事（RSS/Reuters/AP/X）、信号词。
- **特征**：高量、时序、易噪、需持续采集。
- **保真手段**：来源注册 → 采集 → 筛选 → 验证 → 溯源（见 2–7）。

---

## 2. 来源体系（来源问题）

**来源注册表（Source Registry）**——每源一条记录：
`{ id, type, reliability(0–1), cadence, access(API|scrape|RSS), status(active|failed) }`

来源分级：
| 级 | 类型 | 示例 | 默认 reliability |
|---|---|---|---|
| P0 主源 | 自动 / 结构化 | GDELT（事件/语调）、FRED（宏观）、官方统计 | 0.8–0.9 |
| P1 次源 | RSS / API | Reuters / AP / 新闻聚合 / X | 0.6–0.8 |
| P2 策源 | 已策展 | `actors/` 树、ConStructLab_ConfigMapping | 0.9（但需定期复核） |
| P3 用户输入 | 手动 | 人工补录 | **0.3（强制 low + 标注）** |

reliability 直接进入 §5 的置信度模型。

---

## 3. 采集（规模问题）

- **编排**：n8n（Cron 触发）→ `Execute Command` 调 Python 采集器（扩展现有 `pipeline.py`）。
- **原始层 / 处理层分离**：原始响应落 `raw` 表；清洗/抽取后才进 `processed`。便于重跑、审计、不丢原貌。
- **采集器清单**：GDELT（已有）、FRED（已有）、RSS（新增）、新闻/X（新增）。
- **失败策略**：源失败 → 标 `source_failed`，跳过该源，**不回退默认值**（修复 V4.1 病灶）。

---

## 4. 筛选（信噪比）

把「海量」压成「相关信号」：
1. **去重**：同事件多源合并（按 url / 标题哈希 / 时间窗）。
2. **相关性**：实体抽取 → 匹配已跟踪 actor / scenario（命中才保留）。
3. **噪声阈值**：tone 极值、signal_words 命中、事件量脉冲。
4. **输出**：候选 Signal 列表（带「涉及主体」「方向」「原始来源引用」）。

---

## 5. 验证（保真核心）

1. **溯源（显式）**：每个 `Event` / `Signal` → `(:Source {url, retrieved_at, confidence})`，经 `:HAS_SOURCE` 边。→ **V5 原 schema 缺的这一笔，本方案补上**。
2. **交叉印证**：同事实 ≥ 2 独立源 → confidence↑；源间矛盾 → 标 `contradiction`。
3. **置信度模型**：`conf = f(source_reliability, corroboration, recency)`，落在 0–1。
4. **人工复核队列**：低置信 / 矛盾 → 入队（非静默默认）；人工处置后回流验证。

---

## 6. 存储

- **PostgreSQL + TimescaleDB = Source of Truth**：`events` / `signals` / `sources` 时序表（含 `source_id` 外键）。
- **Neo4j = 知识图谱**：`(:Actor)` / `(:Scenario)` / `(:Event)` / `(:Signal)` / `(:Source)`；关系含 `:HAS_SOURCE`、`(:Actor)-[:INFLUENCES]->(:Actor)`、`(:Actor)-[:INVOLVED_IN]->(:Scenario)`。
- **双写（沿用 V5 迁移路线图机制）**：先写 PG → 成功再写 Neo4j → 失败记 `sync_errors` → 每小时对账补齐。

---

## 7. 溯源 / 可追责（保真的真正含义）

- 引擎**任何诊断结论** → 可回溯到支撑它的 events / sources（置信度、来源、时间）。
- 读者 / 用户可审计：「这条判断来自哪几条新闻、哪个源、置信度多少」。

---

## 8. 治理

- **47 主体对齐**：导入读 `actors/` 树，非写死 46。
- Schema 版本化；**台湾合规**（Taiwan, China）。
- 兜底策略：**无静默默认值**，失败留空等补采。

---

## 9. 技术方案与里程碑（Phase 映射）

| 阶段 | 内容 | 关键产物 |
|---|---|---|
| **Phase 0** | 最小栈 PG+Neo4j+n8n + **Source Registry schema** + 双写骨架 + 47 对齐导入 | `docker-compose.yml`、`sources` 表、`(:Source)` 节点 |
| **Phase 1** | 采集：n8n 包 `pipeline.py` GDELT + 新增 RSS；raw/processed 分离 | 自动采集跑通，失败不回退默认 |
| **Phase 1.5（新增）** | 筛选 + 验证模块 + 人工复核队列 + `:HAS_SOURCE` 落地 | 置信度模型、contradiction 标、复核队列 |
| **Phase 2** | 图谱迁移：47 主体 + 关系 + 场景 + Event/Signal 入 Neo4j | 关系网可查、可溯源 |

> 复用 V5 P0–P2 的 PG/Neo4j/n8n 与对账机制；**本方案相对 V5 原 schema 新增两块**：`(:Source)` 节点 + 验证/复核模块。

---

## 10. 与 V4.1 的关键差异（为什么这次能治硬伤①）

| 维度 | V4.1 | 本方案 |
|---|---|---|
| 存储 | JSON，无溯源 | PG/TSDB + Neo4j + 显式 `(:Source)` |
| 手动数据 | `manual_input` 静默回退 + 默认值 | 强制 low + 标注，入复核队列，不填默认 |
| 来源管理 | 无 | Source Registry + reliability 评级 |
| 验证 | 无（只算分数） | 溯源 + 交叉印证 + 置信度 + 复核 |
| 主体数 | 隐式 46 | 显式读 `actors/` 47 |
| Knowledge 层 | 无引用 | 要求内联引用 |

**一句话**：V4.1 是硬伤①的具象；本方案从「来源→采集→筛选→验证→溯源→治理」六环把它结构化解掉，且手动兜底从「静默默认」改为「强制降权 + 人工复核」。
