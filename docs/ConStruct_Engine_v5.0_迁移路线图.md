# ConStruct Engine v5.0 — 迁移路线图

> **原则**: 每阶段独立可验证，不搞大爆炸式迁移。旧系统保持运行，新组件逐个替换。  
> **日期**: 2026-06-26  
> **更新**: 2026-06-27（DeepSeek 审查修正——集成成本/三索引一致性/工期修正）

---

## 审查修正（v5.0.1）

### 服务缩减：8→5 核心服务
| 服务 | 决策 | 理由 |
|------|------|------|
| PostgreSQL+TSDB | 保留 | 不可替代 |
| Neo4j | 保留 | 不可替代 |
| n8n | 保留 | 工作流编排 |
| Dify | 保留（只做2个Workflow） | Identity + SUL |
| Airbyte | **延后**（Phase 0 不装） | GDELT 用 pipeline.py + n8n 调用更稳 |
| Meilisearch | **后置**（用 PG tsvector 替代） | 搜索需求不够明确时不加复杂度 |
| MinIO | **后置**（用本地文件系统） | S3 不是刚需 |
| LlamaIndex | **Phase 3 再做** | 不着急 |

### 工期修正
| Phase | 原估计 | 修正 | 关键调整 |
|-------|--------|------|---------|
| Phase 0 | 2周 | **3周** | Docker调试+服务间稳定性 |
| Phase 1 | 2周 | **2周** | GDELT不改Airbyte，保留Python+n8n |
| Phase 2 | 2周 | **3周** | 加对账任务(0.5周)+Cypher写稳(0.5周) |
| Phase 3 | 3周 | **3周** | 只做2个Dify Workflow |
| **总工期** | 9周 | **11周** | |

### 新增关键机制
1. **三索引同步脚本** — 档案更新 → 同时写 Neo4j+PG → 失败重试
2. **PG↔Neo4j 对账任务** — 每小时检查双写一致性，补齐缺失
3. **业务验证日** — Phase 1/2/3 结束时各选3个历史事件，新旧系统诊断结论对比
4. **版本锁定** — docker-compose.yml 不用 `latest` tag

---

## 总览

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
基础设施     数据管道     知识图谱     引擎重塑     AI增强       World Model
 2周         2周         2周         3周         持续         长期

产出:                       产出:                         产出:
Docker Compose              n8n pipeline 自动运行           LangGraph Agent 编排
全部服务 running            数据流与旧系统对账通过            多Agent协作诊断
                                                           World Model Engine
```

---

## Phase 0: 基础设施搭建（预计 3 周）

### 策略：最小可行栈
Phase 0 只启动 **5 个核心服务**（PG + Neo4j + n8n + Dify + MinIO）。
→ Airbyte 延后（GDELT 用 pipeline.py + n8n 调用更稳）
→ Meilisearch 后置（初期用 PostgreSQL tsvector 全文搜索）
→ 提前预留 Docker 内存至 10GB+，扫清端口冲突

### 具体任务

| # | 任务 | 验证方式 |
|---|------|----------|
| 0.1 | Docker Desktop + WSL 安装 | `docker --version` |
| 0.2 | 配置 Docker 镜像加速器 | `docker pull hello-world` |
| 0.3 | 调高 Docker 内存至 10GB | Docker Desktop Settings |
| 0.4 | 端口冲突扫描（5432/7474/5678/3000） | `netstat -an` |
| 0.5 | `docker compose up -d` 启动全部服务 | `docker ps` 5 服务 running |
| 0.6 | PostgreSQL + TimescaleDB 启动 | `SELECT create_hypertable(...)` |
| 0.7 | Neo4j 启动 + Browser 可访问 | `MATCH (n) RETURN n LIMIT 1` |
| 0.8 | n8n 启动 + UI 可访问 | 创建第一个 Workflow |
| 0.9 | Dify 启动 + 配置 LLM 模型 | 跑通第一个 Workflow |
| 0.10 | 写 `healthcheck.sh` — 挨个轮询 `/health` | 所有端点返回 200 |
| 0.11 | Neo4j 导入 46 主体 + 10 场景 + 关系 | MATCH (a:Actor) RETURN count(a) → 46 |
| 0.12 | 写"索引同步脚本"骨架（档案更新→PG+Neo4j） | 手动触发一次，验证双写 |

### 产出
- `docker-compose.yml` 文件
- 6 个服务全部 running
- 首个 n8n workflow（Airbyte HTTP → 写入 PG）
- Neo4j 中有 46 主体节点

---

## Phase 1: 数据管道切换（预计 2 周）

### 策略：Airbyte 不接 GDELT
GDELT 是批量 CSV 下载而非 REST API，Airbyte HTTP Connector 需要自定义开发（成本 >2 周）。
→ GDELT 保留 pipeline.py 拉取逻辑，用 n8n "Execute Command" 节点调度
→ Airbyte 只在 Phase 3 之后尝试接入 FRED/IMF 等有现成 Connector 的数据源

### GDELT 管道设计
```
n8n Cron trigger (每小时)
  ↓
Execute Command: python pipeline.py --gdelt-only
  ↓
GPT 节点: 识别涉及主体 + 行为模式
  ↓
规则节点: Signal Detection
  ↓
PostgreSQL: INSERT INTO events + signals
  ↓
Neo4j: CREATE 事件节点 + 关系
```:
       ↓
  [GPT: 识别涉及主体 + 行为模式]
       ↓
  [规则引擎: Signal Detection]
       ↓
  [写入 PostgreSQL events 表 + signals 表]
```

### 具体任务

| # | 任务 | 验证方式 |
|---|------|----------|
| 1.1 | Airbyte: GDELT HTTP Connector 配置 | 拉取一周事件数据 |
| 1.2 | Airbyte: FRED Connector 配置 | 拉取 US GDP/CPI |
| 1.3 | Airbyte: RSS Connector (Reuters) | 拉取最近新闻 |
| 1.4 | Airbyte: File Connector (主体档案CSV) | 同步 46 主体基础数据 |
| 1.5 | n8n: Cron trigger 每小时 → Airbyte | 到点自动触发 |
| 1.6 | n8n: GPT 节点 → 识别事件涉及主体 | 对比手工标注准确率 |
| 1.7 | n8n: 规则节点 → Signal Detection | 对比 engine.py 输出 |
| 1.8 | n8n: PostgreSQL 节点 → 写入 | 查询确认写入 |
| 1.9 | 并行验证: 一周数据新旧系统对比 | 差异<5%→切换 |

### 停用
- `pipeline.py` 的 GDELT 采集部分（保留作为回退方案）

---

## Phase 2: 知识图谱迁移（预计 3 周）

### 关键新增：对账机制
最大风险是 PostgreSQL 和 Neo4j 的双写不一致。
→ **PG 是唯一真相来源（Source of Truth）**
→ n8n 先写 PG，成功后再写 Neo4j
→ Neo4j 写入失败时记录到 PG `sync_errors` 表
→ 每小时跑"对账任务"：PG 最近 24h 事件 vs Neo4j 对应节点，补齐缺失

### 核心图谱模型

```cypher
// 节点
(:Actor {code, name, type, tier})          — 46个主体
(:Scenario {code, name, coupling_level})    — 10个场景
(:Event {gdelt_id, date, goldstein, tone})  — 事件流
(:Signal {type, direction, confidence})     — 信号
(:Config {name})                            — 10种构型

// 关系
(:Actor)-[:ADOPTS_CONFIG]->(:Config)
(:Actor)-[:INFLUENCES {weight}]->(:Actor)
(:Actor)-[:INVOLVED_IN]->(:Scenario)
(:Actor)-[:HOSTS]->(:Enterprise)
(:Event)-[:INVOLVES]->(:Actor)
(:Event)-[:BELONGS_TO]->(:Scenario)
(:Event)-[:TRIGGERS {lag}]->(:Event)
(:Signal)-[:DETECTED_IN]->(:Event)
```

### 具体任务

| # | 任务 | 验证方式 |
|---|------|----------|
| 2.1 | 编写导入脚本: 46 主体 → Neo4j 节点 | MATCH (a:Actor) RETURN count(a) → 46 |
| 2.2 | 导入 10 种构型节点 + 关系 | MATCH (a)-[:ADOPTS_CONFIG]->(c) RETURN c.name |
| 2.3 | 导入 10 场景节点 + 主体-场景关系 | MATCH (a)-[:INVOLVED_IN]->(s) 返回关系数 |
| 2.4 | 导入场景耦合关系 (台海→AI芯片→金融) | MATCH p=(:Scenario)-[:TRIGGERS]->(:Scenario) |
| 2.5 | 导入已知国家间影响关系 (v1.0 手工标注) | MATCH (a1)-[:INFLUENCES]->(a2) RETURN count |
| 2.6 | 导入事件流 (从 PG 实时同步到 Neo4j) | n8n workflow: PG INSERT → Neo4j CREATE |
| 2.7 | 写核心 Cypher 查询封装 | 事件链查询/信号图谱查询/ICC监控查询 |
| 2.8 | 验证: 台海事件链查询 | 台海事件 3跳传播 结果与旧系统一致 |

### 关键 Cypher 查询（验证用）

```cypher
-- 台海事件传播链（3跳）
MATCH path = (e1:Event)-[:TRIGGERS*1..3]->(e2:Event)
WHERE e1.scenario = 'TaiwanStrait'
RETURN path LIMIT 10

-- 中国信号图谱
MATCH (c:Actor {code:'CN'})<-[r:INVOLVES]-(e:Event)-[:HAS_SIGNAL]->(s:Signal)
RETURN c, r, e, s

-- ICC 缺口趋势监控（从信号反向查事件）
MATCH (s:Signal {type:'ICC_gap'})-[:DETECTED_IN]->(e:Event)-[:INVOLVES]->(a:Actor)
WHERE e.date > date() - duration({days: 30})
RETURN a.code, s.direction, count(*) as cnt
ORDER BY cnt DESC
```

---

## Phase 3: 引擎重塑（预计 3 周）

### 策略：只做 2 个 Dify Workflow（不是 4 个）
Dify Workflow 超过 5 个节点后调试体验急剧下降。
→ Identity Interpreter → **Dify Workflow**（RAG + GPT，确实适合）
→ Signal Detector → **保留 Python 规则引擎 + n8n 调用**（规则比 LLM 更稳定）
→ Consistency Checker → **纯 Neo4j Cypher 查询**（不需要 LLM）
→ SUL Scorer → **Dify Workflow**（5 维评估，需要 LLM 综合判断）

### 旧 → 新映射

| 旧引擎 | 当前实现 | 新实现 |
|--------|---------|--------|
| Identity Interpreter | `rules/*.json` + `engine.py` | **Dify Workflow** ← 唯一的 LLM 引擎 |
| Signal Detector | `rules/*.json` + `engine.py` | **Python 规则引擎 + n8n 调用**（规则更稳定） |
| Consistency Checker | `engine.py` | **纯 Neo4j Cypher 查询**（不需要 LLM） |
| SUL Scorer | `engine.py` | **Dify Workflow** ← 第二个 LLM 引擎 |

### 具体任务

| # | 任务 | 验证方式 |
|---|------|----------|
| 3.1 | Dify: Identity Interpreter Workflow（RAG+GPT） | 输入事件→输出 Identity 解读 |
| 3.2 | Dify: SUL Scorer Workflow（5维评估+LLM） | 输入事件→输出5维 SU分数 |
| 3.3 | n8n: Python规则引擎 → Signal Detector | 输入事件→输出信号列表+严重性 |
| 3.4 | Neo4j: Consistency Checker 查询封装 | 跨主体一致性检查通过 |
| 3.5 | n8n: 编排上述 4 步诊断流水线 | 端到端流程跑通 |
| 3.6 | Dify: 诊断报告生成 Workflow | 输出完整诊断报告（Markdown） |
| 3.7 | **业务验证日**：3事件新旧对比 | 诊断结论一致性检验 |

### 停用
- `engine.py` 的 4 个核心函数（保留 rules/ 目录作为 Dify 规则节点数据源）

---

## Phase 4: AI 增强（6 个月后）

**当前不要碰**。Phase 0-3 跑稳 3 个月，积累真实诊断案例后，再决定要不要多模型路由和 Agent 协作。

| # | 任务 |
|---|------|
| 4.1 | Dify 配置多模型（GPT-4o, Claude, DeepSeek, Gemini） |
| 4.2 | 任务路由规则：Identity 推理→Claude / 信号检测→GPT-4o / 翻译→DeepSeek |
| 4.3 | RAG 精度调优：分块策略、检索权重、重排序 |
| 4.4 | Radar 仪表盘改为接 Dify API（替代静态 JSON） |
| 4.5 | CrewAI 多 Agent 原型：军事+金融+AI Agent 协作诊断 |

---

## Phase 5: World Model（1 年后）

不急。

---

## 不可碰清单（重申）

| 项目 | 原因 |
|------|------|
| Kubernetes | 单人运维找死 |
| Spark | 数据量不够 TB 级 |
| Kafka | Airbyte+n8n 已够用 |
| 自建数据库 | PostgreSQL 是一切的基础 |
| 自建知识图谱 | Neo4j 碾压任何自建方案 |
| 自建 ETL | Airbyte 500+ Connector 已覆盖 |

---

## 风险与回退策略

| 风险 | 应对 |
|------|------|
| Airbyte Connector 不支持某数据源 | 用 n8n HTTP 节点直接调 API，走 Airbyte Custom Connector |
| Neo4j 查询性能不足 | 先小批量（每月事件），逐步扩大 |
| Dify Workflow 推理不如 engine.py | 保留 engine.py 作为对照，Dify 逐步替换 |
| Docker 资源不足 | 当前单机 6 服务完全够，不够时 MinIO/Meilisearch 可用 SaaS 版 |

**核心策略**: 每一步都有旧系统在旁边跑着，任何新组件出问题——关掉，旧系统继续。

---

*ConStruct Lab — Structural diagnosis. Not structural talk.*
