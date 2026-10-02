# ConStruct Stack v5.0 — Phase 0 验证指南

> 验证目标：数据流（GDELT 采集）→ 真相源（PostgreSQL + TimescaleDB）→ 图谱（Neo4j 溯源边）核心链条跑通。
> 攻克硬伤①「数据层不保真」的底座：每条事件带 `source_ref` + `confidence` + `verification_status=pending`，绝不静默当作事实。

日期：2026-07-25（修复版）
栈：PostgreSQL 16 + TimescaleDB / Neo4j 5 / n8n（Docker Compose）

---

## 0. 前置条件

1. **Docker Desktop 已安装并正在运行**（系统托盘鲸鱼图标稳定，不是动画）。
2. **关闭 Resource Saver**：Settings → General → 取消 "Resource Saver"。否则 daemon 休眠，容器起不来。
3. `docker --version` 能看到版本；`docker compose version` 正常。
4. 本机有 Python（`python --version` 可见），用于跑 GDELT 采集器 dry-run。

---

## 1. 两种运行方式

### A. 首次 / 遇到「database does not exist」或图导入报「Node already exists」→ 先 reset

`./data/pg`、`./data/neo4j-v2`、`./data/n8n` 是绑定挂载（bind mount），只在**第一次** `docker compose up` 时初始化。
早期多次调试可能在数据目录里留下旧库 / 旧图，导致：
- PostgreSQL 报 `database "construct" does not exist`
- Neo4j 导入报 `Node already exists with label ...`

`reset` 命令会停容器 + 清空这三个本地数据目录 + 重新拉起，得到干净可重复的环境：

```
phase0.bat reset
phase0.bat verify
```

### B. 正常验证（环境已干净）

```
phase0.bat verify
```

---

## 2. verify 六步说明

| 步 | 动作 | 关键修正 |
|---|---|---|
| [1/6] | `docker compose up -d` 起三容器 | — |
| [2/6] | 等待 60s 让 PG/Neo4j 完成首启 | — |
| [3/6] | 确保 `construct` 库存在（不存在则 `CREATE DATABASE`），再幂等跑 `init-pg.sql` | 旧版缺 `CREATE EXTENSION timescaledb`，`create_hypertable` 会失败 → 已补 |
| [4/6] | Neo4j 导入：先 `MATCH (n) DETACH DELETE n` 清空再重建种子图（幂等） | 旧版用 `CREATE` 导致重复导入报「Node already exists」→ 已改幂等 |
| [5/6] | GDELT 采集器 dry-run（`--sample scripts/gdelt_events_sample.json`） | 已改用 gdelt-py 取 GDELT Events 数据库（DOC API 无 actor 对），样例按脚本目录解析 |
| [6/6] | 溯源查询：PG events 样例 / 按来源分组 / Neo4j `HAS_SOURCE` 边数 | 旧版 `cypher-shell -c` 语法错误（cypher-shell 不接受 `-c`）→ 已改位置参数 |

---

## 3. 预期输出

- **[3/6]** 无 `FATAL: database "construct" does not exist`。
- **[4/6]** 不再报 `Node already exists`；末尾输出 `actors / configs / scenarios / 关系数`。
- **[5/6]** `关联到的 ConStruct 主体事件: 3 / 原始 4`（canonical 码 `CHN→RUS`、`USA→TWN`、`ISR→IRN` 命中；`ARG→CHL` 两端都不在 47 主体被跳过），并写出 `gdelt_linked_sample.json`。
- **[6/6]**
  - PG events 样例：空表返回 0 行（尚未写真实事件），**不报错**即过关。
  - PG 按来源分组：空表 0 行。
  - Neo4j `HAS_SOURCE` 边数：**当前种子图 47**（= cypher 里 47 个 Actor 各挂一条 `ConStruct_Lab` 溯源边）。
    - ✅ **Phase 0.5 已统一 canonical 码表**（`scripts/canonical_actors.py`，47 主体，ISO3/标准缩写码如 `CHN`/`USA`）。collector 写库、Neo4j 节点、importer 全部用同一套码，事件↔图谱 JOIN 不再断裂。`init-neo4j.cypher` 由 `export_to_neo4j.py` 从码表自动生成，**勿手改**。

---

## 4. 写真实 GDELT 事件（Phase 0 之后）

```
pip install gdelt-py psycopg2-binary
python scripts/collect_gdelt.py --days 1
python scripts/collect_gdelt.py --days 2 --query russia --limit 500
```

- **采集器已改用 `gdelt-py`（py-gdelt）** 取 GDELT **Events 数据库**（raw 文件 + 可选 BigQuery 兜底）。
  DOC 2.0 API 只有 ArtList/Timeline 模式、**不含 actor 对事件**，所以不再手搓 `mode=Event`（GDELT 返回 `Invalid mode.`）。
- 依赖：`pip install gdelt-py psycopg2-binary`（Python 3.11+，本机 3.12 满足）。
- 参数：`--days N` 回溯 N 天（默认 1=昨天；Events 日文件通常滞后 1~2 天，若 0 事件试 `--days 2`）；`--query` 是 actor 名子串过滤（如 `russia`）；`--limit` 限制写入条数。
- 自动关联 ConStruct 主体 → 写入 `events` 表，带 `source_ref='GDELT'`、`confidence`（按 NumMentions 归一）、`verification_status='pending'`。
- 未关联到的事件（两端都不在 47 主体库）会被跳过，不污染库。

---

## 5. 故障速查

| 现象 | 处理 |
|---|---|
| `database "construct" does not exist` | `phase0.bat reset`（清旧卷后重初始化） |
| `Node already exists with label ...` | 已通过幂等导入修复；若仍出现，跑 `reset` |
| `cypher-shell: unrecognized arguments: '-c'` | 旧 bug，已改为位置参数，更新脚本即可 |
| `create_hypertable does not exist` | 旧 bug，init-pg.sql 已补 `CREATE EXTENSION timescaledb` |
| 容器起不来 / `docker info` 报错 | 关 Resource Saver，等 daemon 就绪再跑 |
| `FileNotFoundError: gdelt_events_sample.json` | collect_gdelt.py 已改按脚本目录解析路径 |

---

## 6. Phase 0.5: canonical 码表统一 + 已写事件迁移

### 6.1 为什么需要这步（根因）

Phase 0 真实落库后发现一个比「46 vs 47」更深的断裂：

- **collector（collect_gdelt.py）** 当初把 GDELT 主体名写成**展示名码**（`United States` / `United Kingdom` / `Brazil` …）。
- **Neo4j 种子图（init-neo4j.cypher）** 用的是**短码**（`USA` / `GBR` / `BRA` …，且还有 `US`/`EU`/`KOR`/`SAU`/`PRK`/`AL`/`WB` 等不一致写法）。
- 两套词汇导致 **events.actor_code ↔ Actor.code 的 JOIN 全断**：1529 行真实事件里大量 actor_code 在图谱里找不到对应节点 → 悬空边，诊断表接不上图谱。

### 6.2 解决方案：单一真相源（canonical 码表）

新建 `scripts/canonical_actors.py` 作为**唯一码表来源**，47 主体全部用 **ISO3 / 标准缩写短码**：

```
CHN USA RUS EU JPN IND IRN ISR DEU FRA GBR KOR SGP SAU TUR EGY AUS SRB PHL VNM TWN
BRA UKR PAK PRK
NATO UN ASEAN BRICS SCO AL OPEC GCC IMF WB WTO
TSMC ASML NVDA OAI ANTH SPX SMSNG DS BD HW PLTR
```

三处全部改为读这套码：

| 组件 | 改动 |
|---|---|
| `collect_gdelt.py` | 移除内联别名表，改 `import canonical_actors`；`match_actor` 用**子串匹配 + 长别名优先**（`north korea` 先于 `korea`，`ukraine` 先于 `uk`）；写库输出 canonical 短码 |
| `export_to_neo4j.py` | 废弃读旧 `ConStruct_Archive` 路径；从 `canonical_actors` 生成 `init-neo4j.cypher` + `neo4j-import/*.csv`（**勿手改 cypher**） |
| `init-neo4j.cypher` | 47 Actor 节点全 canonical 码；47 ADOPTS_CONFIG / 19 INVOLVED_IN / 13 INFLUENCES；重跑参照完整性校验 **零悬空** |

> 缺失主体（Brazil / NATO / Pakistan / North Korea）在此统一收编进 47 主体集，用 canonical 码补为轻节点（light node），不再走「fallback 兜底」的分叉逻辑。

### 6.3 迁移已写事件（幂等）

Phase 0 已写库的 1529 行事件仍是展示名码，需重映射为 canonical 短码：

```bat
rem 方式 A（推荐，无需改挂载）：stdin 管道喂宿主机文件给容器内 psql
cd /d "D:\Projects\地缘推演台\construct-stack"
docker exec -i construct-postgres psql -U construct -d construct -f - < scripts\migrate_codes.sql

rem 方式 B：本机直连（需 pip install psycopg2-binary 或系统有 psql 客户端）
psql "postgresql://construct:construct_dev_2026@localhost:5432/construct" -f scripts/migrate_codes.sql

rem 方式 C：已把 migrate_codes.sql 加进 docker-compose 挂载后，容器路径才有效
rem   （改完 compose 需先 docker compose up -d 让 PG 重新挂载该文件）
docker exec -i construct-postgres psql -U construct -d construct -f /docker-entrypoint-initdb.d/migrate_codes.sql
```

- `scripts/migrate_codes.sql` 含 47 条 `WHEN '展示名' THEN 'CANONICAL码'` 映射，对 `actor1_code` / `actor2_code` 两个 `UPDATE ... CASE` 块重映射。
- **幂等**：映射后码已是短码，重跑 `CASE` 不再命中，`ELSE actor_code END` 原样保留 → 可反复执行。
- 只动 `actor1_code` / `actor2_code`，其它列（`time` / `confidence` / `source_ref` / `verification_status`）不动。

### 6.4 验证收口

```bat
phase0.bat verify
```

- **[6/6] dangling guard**：`SELECT count(*) FROM events WHERE actor_code NOT IN (47 canonical 码)` → **期望 0**（之前是大量悬空）。
- **[4/6] Neo4j**：47 Actor 节点；`HAS_SOURCE` 边数 = 47（每个 actor 一条 `ConStruct_Lab` 溯源边）。
- **[5/6]** dry-run 输出 canonical 码：`CHN→RUS` / `USA→TWN` / `ISR→IRN`（单边命中如 `ARG→CHL` 两端都不在 47 主体被跳过）。

### 6.5 已知未变（后续 Phase 待办）

1. **Knowledge 层 0 内联引用**：`actors/` 树 64 篇 md 当前无 http 链接，图谱 `ConStruct_Lab` 源 `note` 已标注「待补真实来源」——Phase 0.5 只统一了 Signal 层码表，Knowledge 层溯源仍需补。
2. ✅ **验证环已实现**（详见 §7）：`pending → cross_checked` 自动规则（共现佐证 + 高单置信）+ 人工复核队列导出已落地 `verify_events.py` / `verify_events.sql` / n8n 工作流。
3. **actors/ 树仍有版本重复文件**（EU/US/UA v1+v2、DE v1a/v1b/v2、SG 3 个 `_en` 等），暂不作为自动种子源以免污染。

---

### 7. Phase 1.5 验证环（verification loop）

目标：兑现数据保真承诺的**验证/复核**环节——不让单源低提及事件被静默当作事实。所有事件默认 `pending`，按规则自动提升为 `cross_checked`，其余进人工复核队列；`verified` 只由人或跨源确认（自动环绝不伪造）。

#### 7.1 验证策略

| 规则 | 条件 | 动作 | 含义 |
|---|---|---|---|
| 内部一致性佐证 | 同 `(actor1,actor2,action)` 共现 ≥3 次 **且** 置信度 ≥0.65 | `pending → cross_checked`（自动） | 重复出现 = 强信号，视为内部佐证 |
| 单次高置信 | 单事件置信度 ≥0.90 | `pending → cross_checked`（自动） | 高提及量单事件 |
| 其余 | 不满足上两者 | 保持 `pending` | 导出人工复核队列 `review_queue.json` |
| `verified` | 人工复核通过 **或** ≥2 独立来源印证 | `pending/cross_checked → verified` | **只由人或跨源**，自动环不置位 |

> 置信度来自 `collect_gdelt.py`：`min(0.5 + num_mentions/200, 0.98)`（0.50–0.98）。实际 1529 行多在 0.5–0.65（低提及），故大部分会进人工复核——这是诚实边界，不是 bug。

#### 7.2 文件清单

| 文件 | 作用 |
|---|---|
| `scripts/alter_events_verification.sql` | 给 `events` 加 `verified_at` / `verified_by` / `review_notes` 三列（幂等 DO 块） |
| `scripts/verify_events.py` | 验证环引擎（本机 CLI）：自动 cross_check + 导出复核队列；可调阈值、支持 `--dry-run` |
| `scripts/verify_events.sql` | 同源逻辑的纯 SQL（可直接 `psql -f` 或 n8n Postgres 节点执行） |
| `phase15-verify-workflow.json` | n8n 工作流：每日 06:00 跑两条 UPDATE + 导出复核队列（需自配 PG 凭据） |

#### 7.3 本机运行

```bat
cd /d "D:\Projects\地缘推演台\construct-stack"

rem ① 首次：加验证溯源列（幂等，已加则跳过）
rem   本机若无 psql 客户端（仅容器内有），用 docker exec stdin 管道（免挂载、免重启）
docker exec -i construct-postgres psql -U construct -d construct -f - < scripts\alter_events_verification.sql

rem ② 先 dry-run 看会动多少（不写库）
python scripts/verify_events.py --dry-run

rem ③ 正式跑（写库 + 导出 review_queue.json）
python scripts/verify_events.py
rem   或等价用纯 SQL（同样走容器）：
rem   docker exec -i construct-postgres psql -U construct -d construct -f - < scripts\verify_events.sql
```

#### 7.4 人工复核

引擎跑完后会生成 `scripts/review_queue.json`（仍是 `pending` 的事件）。人工过一遍，确认无误的事件直接置 `verified`：

```sql
UPDATE events
SET verification_status = 'verified',
    verified_at = NOW(),
    verified_by = 'human',
    review_notes = '人工复核通过'
WHERE source_id = '<待确认事件的 source_id>';
```

（n8n 工作流目前只做自动 cross_check + 导出队列；人工置 `verified` 在 PG 侧完成，后续可接复核 UI。）

#### 7.5 n8n 导入（可选自动化）

1. 打开 n8n（已在 `construct-stack` 栈运行）→ **Workflows → Import from File** → 选 `phase15-verify-workflow.json`。
2. 三个 Postgres 节点的 credential `id` 现是占位 `REPLACE_PG_CREDENTIAL_ID`：点节点 → Credentials → 新建/选择连 `construct` 库的 Postgres 凭据（host=`construct-postgres`, user=`construct`, db=`construct`）。
3. 激活工作流（右上 Toggle）。每日 06:00 自动跑验证环。

#### 7.6 状态语义（承接 Phase 0 设计）

`verification_status` 四态：`pending`（待验证）→ `cross_checked`（过自动内部一致性）→ `verified`（人或跨源确认）/ `rejected`（人工否决）。新增 `verified_by` ∈ `auto_internal | human | cross_source`，保证"谁验的"可追责。

#### 7.7 已知边界

- **单源无跨源印证**：当前只有 GDELT，故 `cross_checked` 是"内部一致性"而非"独立来源印证"。接 ACLED/UCDP/FRED 后，`cross_source` 分支才会启用 → 那时可自动置 `verified`。
- **阈值可调**：`--min-occ`（默认 3）/ `--min-conf`（0.65）/ `--high-conf`（0.90）按数据分布微调；`verify_events.sql` 里同值需同步改。
- **不自动 `verified`**：防止"系统自证清白"的保真失信。

---

### 8. Phase 1 无人值守采集环（n8n scheduling）

目标：把 collector 接进已在跑的 n8n，设 cron 自动采集 → 自动重跑验证环，让 Tool Loop 无人值守跑。**事件数据在 PG，Neo4j 是静态参照图**（只由 `canonical_actors.py` 派生，不随每日事件变化），故每日循环只动 PG，不碰 Neo4j。

#### 8.1 架构改动

| 文件 | 改动 |
|---|---|
| `Dockerfile.n8n`（新建） | **关键教训链**：①`n8nio/n8n:stable` 无包管理器（apt/apk 同时缺失，疑似 distroless）无法装 Python → 改 `node:20-bookworm-slim`（Debian，`apt-get` 必在）自装 n8n + Python；②经代理拉 deb.debian.org 偶发 502（尤其 `python3-dev`/`linux-libc-dev` 大包）→ **精简依赖只装 `python3 python3-pip`**（psycopg2-binary 有预编译 wheel 免编译，去掉 gcc/python3-dev/libpq-dev）+ **apt/pip/npm 全加重试循环**抗瞬时 502；③用 `python3 -m pip` 而非裸 `pip3`（避免 pip3 二进制缺失致整层失败） |
| `docker-compose.yml` | n8n 服务改 `build: Dockerfile.n8n`（image 命名 `construct-n8n:phase1`），挂 `./scripts:/data/scripts`；n8n env 加 `NODE_FUNCTION_ALLOW_BUILTIN: child_process`（放行 Code 节点内的 `require('child_process')`）+ `GENERIC_TIMEZONE: Asia/Shanghai`（cron 每日 08:00 北京时跑）；n8n 数据卷用命名卷 `n8n_data`（**首次需 chown**，Docker Desktop 命名卷初始 root-owned，否则 n8n 启动 EACCES 崩溃重启：`docker run --rm -v construct-stack_n8n_data:/data node:20-bookworm-slim chown -R 1000:1000 /data`）|
| `scripts/alter_events_idempotent.sql`（新建） | `events` 加 `(time, source_id)` 复合唯一索引（hypertable 必须含分区列 `time`），配合采集器幂等去重 |
| `scripts/collect_gdelt.py` | INSERT 加 `ON CONFLICT (time, source_id) DO NOTHING`（每日重跑/重试不重复插）；计数改用 `cur.rowcount` 只算实际插入行 |
| `phase1-collector-workflow.json`（新建） | n8n 工作流：Schedule(每日 08:00 CST) → Collect GDELT → Verify Loop，**两节点均为 `n8n-nodes-base.code`**（Code 节点，JS 调 `child_process.execSync` 执行 python3）|

#### 8.2 本机启用步骤

```bat
cd /d "D:\Projects\地缘推演台\construct-stack"

rem ① 重建 n8n 镜像（含 Python），首次会拉 n8n 基础镜像 + 装依赖，较慢
docker compose up -d --build

rem ② 给 events 加 (time, source_id) 复合唯一索引（幂等，仅首次需；hypertable 唯一索引必须含分区列 time）
docker exec -i construct-postgres psql -U construct -d construct -f - < scripts\alter_events_idempotent.sql

rem ③ 导入并激活 n8n 工作流（见 §8.3）；之后每日 08:00 UTC 自动采集 + 验证
```

#### 8.3 n8n 导入与激活

1. n8n 已在栈运行（http://localhost:5678）。**编辑器右上角 `▾` → Import from File** → 选 `phase1-collector-workflow.json`（v2.x 入口不在左侧 Workflows 列表里，在编辑器内）。
2. 两个 Code 节点**不需要凭据**（JS 沙箱内 `require('child_process').execSync(...)` 直接调容器内 python3）。直接 **Publish**（v2 把 v1 的 Save 改名 Publish）→ 右侧面板拨 **Active** ON。
3. 首次建议手动点底部 **Execute workflow** 跑一次（v2.x 按钮在画布底部居中），看 n8n 执行日志确认 `Collect GDELT` / `Verify Loop` 都绿。

> **为什么用 Code 节点 + Task Runner（方案 A）**：n8n v2.0+ 默认禁用 `n8n-nodes-base.executeCommand` 节点（安全考虑），即便设 `N8N_ENABLE_EXECUTE_COMMAND=true` + 调整 `NODES_EXCLUDE`，2.8.4 仍不识别（Issue #23439）。Code 节点是 n8n 内置核心节点，不在禁用名单；但 v2.8 的 Code 节点默认在**独立 Task Runner 容器**里执行 JS，沙箱硬编码禁止 `require('child_process')`。因此本栈启用**外部 Task Runner**（`n8nio/runners:2.8.4` 扩展镜像，自带 python3 + gdelt-py + psycopg2），并在其 launcher 配置（`n8n-task-runners.json`）的 `env-overrides` 里放行 `NODE_FUNCTION_ALLOW_BUILTIN=child_process`——Code 节点即可 `execSync('python3 /data/scripts/*.py')` 调采集/验证脚本。主容器 env 里的 `NODE_FUNCTION_ALLOW_BUILTIN` 无效，必须放在 runner 容器。

> DSN 已硬编码为 docker 网络地址 `postgresql://construct:construct_dev_2026@construct-postgres:5432/construct`（n8n 与 PG 同处 `construct-net` 网络，用服务名 `construct-postgres` 解析）。若改了 PG 密码/库名，需同步改工作流里两处命令。

#### 8.4 时区注意

n8n Schedule 触发器用 **n8n 实例时区**（compose 设 `GENERIC_TIMEZONE: Asia/Shanghai`，故 cron 按北京时间跑）。cron `0 8 * * *` = 每日 **08:00 北京时** = UTC 00:00。GDELT Events 日文件滞后约 1–2 天，08:00 北京时拉"昨天"数据通常已发布。

#### 8.5 幂等与重跑

- 采集器 `ON CONFLICT (source_id) DO NOTHING` + `idx_events_source_id_unique`：同 `global_event_id` 不重复插入。每日拉不同日期 → 自然不重；重试同一天 → 静默跳过已存在事件。
- 验证环 `verify_events.py` 只改 `pending` 行，幂等（重跑 0 变动）。
- 每日循环：新 GDELT 事件落 PG → 验证环把其中满足条件的 `pending → cross_checked` → 更新 `review_queue.json`。

#### 8.6 Neo4j 参照图重建（手动，不在每日循环）

Neo4j 图（47 主体 + 构型 + 场景 + 关系）是静态参照层，只由 `canonical_actors.py` 派生，不随每日事件变化。仅当编辑 `canonical_actors.py` 时才需重建：

```bat
python scripts/export_to_neo4j.py        rem 重新生成 scripts/init-neo4j.cypher (挂载进 neo4j 容器的 /init.cypher)
phase0.bat verify                        rem [4/6] 触发 neo4j wipe+reseed 导入新图
```

（若日后想让 Neo4j 也全自动重建，需给 n8n 挂 docker socket + 装 docker CLI，再由 n8n `docker exec construct-neo4j cypher-shell ...`；当前为安全与简洁未启用。）

#### 8.7 验证清单（启用后）

- [ ] `docker compose up -d --build` 成功，n8n-runner 容器含 python3 与依赖（`docker exec construct-n8n-runner python3 -c "import py_gdelt, psycopg2; print('ok')"`）
- [ ] n8n 主容器日志显示 `n8n Task Broker ready on ... port 5679` 且 runner 容器日志显示已连接到 broker（外部模式生效，不再有 "Failed to start Python task runner in internal mode" 警告）
- [ ] n8n UI → Settings → 确认 Code 节点在外部 runner 上执行成功（手动 Execute workflow 时 Collect GDELT / Verify Loop 两节点绿，无 "Module child_process is disallowed"）
- [ ] `idx_events_source_id_unique` 索引存在
- [ ] n8n 工作流已 Import + Activate
- [ ] 手动 Execute 一次：日志见 `Collect GDELT` 打印"扫描 GDELT 事件 N 条, 命中 M 条"、`Verify Loop` 打印"状态分布"
- [ ] 次日 08:00 北京时后看 n8n 执行历史确认自动触发

---

## §9 Task Runner 外部模式配置（方案 A · 2026-07-25 设计 / 2026-07-26 端到端验证通过 ✅）

n8n v2.8 的 Code 节点在独立 Task Runner 进程/容器内执行，主容器 env 的沙箱开关无效。本栈用官方 `n8nio/runners` 扩展镜像承载 Code 节点执行，并放行 `child_process`。

### 9.1 新增文件

| 文件 | 作用 |
|---|---|
| `Dockerfile.runner` | 基于 `n8nio/runners:2.8.4`（**版本必须与 n8n 主镜像严格一致**；实测该基镜像 = **Alpine + 自带 Python 3.13 + pip**，无 apt/apk），直接 `pip3 install gdelt-py psycopg2-binary`（psycopg2-binary 官方有 musllinux wheel，免编译）；挂载 `/data/scripts` 后 Code 节点 `execSync('python3 /data/scripts/*.py')` 才有依赖。**已验证 build 成功（2026-07-26）。** |
| `n8n-task-runners.json` | runner launcher 配置覆盖。**必须基于基镜像默认文件改**（先 `docker run --rm --entrypoint sh n8nio/runners:2.8.4 -c "cat /etc/n8n-task-runners.json"` dump，勿从零写——缺 `workdir`/`command`/`args` 会逐层报错）。唯一改动：js runner `env-overrides.NODE_FUNCTION_ALLOW_BUILTIN` 由 `"crypto"` 扩为 `"crypto,child_process"`（逗号分隔；**这是放行 child_process 的唯一正确位置**）。**已验证生效（2026-07-26）。** |

### 9.2 docker-compose.yml 改动

**n8n 主服务 environment 新增**（启用外部 runner，broker 监听 0.0.0.0 让 runner 容器能连）：
```yaml
N8N_RUNNERS_ENABLED: "true"
N8N_RUNNERS_MODE: "external"
N8N_RUNNERS_BROKER_LISTEN_ADDRESS: "0.0.0.0"
N8N_RUNNERS_AUTH_TOKEN: ${N8N_RUNNERS_AUTH_TOKEN}
```
> 已移除 Plan B 残留的 `NODE_FUNCTION_ALLOW_BUILTIN`（主容器无效）。

**新增 n8n-runner 服务**：
```yaml
n8n-runner:
  build: { context: ., dockerfile: Dockerfile.runner }
  image: construct-n8n-runner:phase1
  environment:
    N8N_RUNNERS_TASK_BROKER_URI: "http://construct-n8n:5679"
    N8N_RUNNERS_AUTH_TOKEN: ${N8N_RUNNERS_AUTH_TOKEN}
  volumes:
    - ./scripts:/data/scripts
    - ./n8n-task-runners.json:/etc/n8n-task-runners.json:ro
  depends_on: [n8n]
  networks: [construct-net]
```

### 9.3 .env 改动

新增 `N8N_RUNNERS_AUTH_TOKEN=<随机64位hex>`（n8n 主容器与 runner 容器共享认证，已用 `secrets.token_hex(32)` 生成写入）。

### 9.4 启用命令（需联网拉 runners 镜像）

```bat
cd /d "D:\Projects\地缘推演台\construct-stack"
docker compose up -d --build        rem 会新拉 n8nio/runners:2.8.4 并 build 扩展镜像
docker ps --filter name=construct-n8n-runner   rem 状态应为 Up
```

### 9.5 实测踩过的坑（2026-07-26 全部解决）

1. **compose 网络引用**：服务里写 `networks: [construct-net]` 报 `undefined network`——顶层 `networks:` 的键名是 `default`（`name: construct-net` 只是对外名），runner 服务**不写 networks 字段**即可（默认进 default 网络）。
2. **launcher 配置逐层报错**：自写 json 从零写会依次触发 ①多 runner 模式必须声明 `health-check-server-port` ②该字段要**字符串**（Go unmarshal）③不能占 launcher 自身健康检查端口 **5680**（默认 js=5681/py=5682）④缺 `workdir` 报 `chdir : no such file`。**正解 = dump 基镜像默认配置后最小改动**。
3. **`docker compose restart` 必须在 construct-stack 目录跑**（否则 `no configuration file provided`）；config 是 bind mount，重启 runner 即生效，**不用 rebuild**。
4. **Code 节点 Mode 必须 `runOnceForAllItems`**（返回数组）；`runOnceForEachItem` 返回数组会报 `A 'json' property isn't an object`。
5. **runner 闲置自动退出**（idle timeout）后处于"重新等 broker 接单"状态，此时 Execute 会 `Task request timed out after 60 seconds`——双容器重启（`up -d n8n-runner` + `restart n8n`）趁热立即执行即可。
6. **采集脚本要跑几分钟**，runner 默认任务超时 60s 会被杀：compose runner env 加 `N8N_RUNNERS_TASK_TIMEOUT: "600"`（该变量在 launcher config 的 `allowed-env` 白名单内，会透传）。

### 9.6 排错速查

| 现象 | 原因 | 处理 |
|---|---|---|
| runner 容器 Exited | Dockerfile.runner `USER runner` 用户不存在 / apt 装 python 失败 | 看 `docker logs construct-n8n-runner`；若 USER 报错改 root；apt 失败检查代理 |
| Code 节点仍报 `child_process disallowed` | env-overrides 没被 runner 读到（文件路径不对） | 确认 runner 容器 env 含 `NODE_FUNCTION_ALLOW_BUILTIN`；查 9.5-2 的 config 路径 env |
| n8n 日志 `Failed to start Python task runner in internal mode` | 外部 runner 没连上 | 检查 runner 容器 Up + broker URI + AUTH_TOKEN 一致 |
| 采集 0 行 / import error | runner 容器内 python3 缺 gdelt-py | `docker exec construct-n8n-runner python3 -c "import py_gdelt"` 验证 |

### 9.7 首次端到端运行结果（2026-07-26 09:23）

- n8n UI 手动 Execute workflow：三节点全绿（Schedule → Collect GDELT → Verify Loop）。
- 落库：`events` 总量 1529 → 2969（**+1440**，日期分区 `2026-07-25`）。
- 验证环：`cross_checked` 15 → 41（+26），`pending` 2928。
- **遗留疑点**：单日落库为"命中 47 主体"的条数（千级），非扫描总量。需看 Collect GDELT 节点 stdout 的"扫描 N 条"——若 N 也是千级，则 `stream_sync` 对单日只拉了部分 15 分钟更新文件（非全天全集），采集完整性需修（遍历当日全部文件或换 query 模式）；若 N 是几十万，则千级命中率正常。
