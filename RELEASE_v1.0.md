# ConStruct Lab v1.0 — 首次发布

> **2026-07-28** · 结构性诊断引擎正式上线

---

## 概述

ConStruct Lab 是一个结构性分析引擎。它用 200 年战争数据、40 年冲突日志和每日新闻脉冲，枚举结构上可能的路径，排除逻辑上不可能的路径。所有判断锚定在可追溯的数据上。所有假设设计为可被数据反证。

### 核心数字

| 指标 | 数值 |
|---|---|
| 主体覆盖 | 53（Tier1 8国 + Tier2 16区域 + Tier3 29组织） |
| 数据事件 | 42万条 UCDP + ~700条/日 GDELT |
| 自动化节点 | 8 节点全绿日更环 |
| 结构验证项 | 53主体 × 114项 |
| 诊断文章 | 11 份 Tier1 结构诊断 |
| 结构词典 | 22 条概念条目 |
| 部署站点 | construct-lab.web.app |

---

## 新功能

### 结构性分析引擎
- **11 层诊断框架**：从 L0（世界事件）到 L10（生物类比六型），地缘政治的 MRI
- **三层时间尺度数据**：COW 骨架（1816-2014） × UCDP 肌肉（1989-2025） × GDELT 脉冲（每日）
- **可被证伪的设计**：53 主体 × 114 项验证项自动检测行为偏差

### 自动化 Pipeline
- 八节点日更环（采集 → 验证 → 预警 → 反证 → 图谱 → 地图）
- 双轨 GDELT 采集（actor + structural domain）
- 三级验证系统（cross_checked → pending → verified）
- 偏差检测四层体系（多源三角验证 → 覆盖密度 → 编码偏差 → 偏差热力图）

### 可视化
- 交互式世界冲突时间地图（UCDP 1989-2025 + COW 200年 + GDELT 48h）
- 右边栏六领域卡片（金融秩序 / AI技术结构 / 能源 / 产业链 / 社会 / 矿物）
- Canvas 90天趋势折线图
- Leaflet + OSM 底图，Keyless 零认证

### 内容产出
- 11 份 Tier1 结构诊断文章（中美俄日印欧伊以英法德）
- 22 条结构词典条目（冻结局 / 天下体系型 / 打而不占 / 互锁式 / 交易式方法⑤ …）
- 事件快评自动化（GDELT 异常 → DeepSeek → 审计队列）
- 9 种内容形态矩阵（全文见 `content/ConStruct_内容输出形态_v1.md`）

### 偏差处理
- `source_weights` 表 + coverage_density 自动计算
- 地图 tooltip 嵌入密度标注
- 每篇诊断含"我们不知道什么"元层盲区提示
- encoding_bias CAMEO 编码对比框架就位

---

## 技术栈

| 层 | 技术 |
|---|---|
| 数据库 | PostgreSQL + TimescaleDB, Neo4j |
| 编排 | n8n (Docker) |
| 采集 | Python (gdelt-py, psycopg2) |
| 推理 | DeepSeek API |
| 可视化 | Leaflet + OSM + Canvas |
| 部署 | Firebase Hosting + Docker Compose |

---

## 已知限制

- GDELT 数据源存在西方媒体框架偏差（已建立偏差检测系统）
- encoding_bias 等待数据积累满 30 天后数值稳定
- 推演引擎 `project_paths.py` 待落地
- Tier2/Tier3 主体诊断未覆盖

---

## 部署地址

- 品牌站：https://construct-lab.web.app
- 世界地图：https://construct-lab.web.app/map.html
- 诊断工具：https://construct-lab.web.app/tool

---

## 署名

- **系统**：ConStruct Lab — *Structural diagnosis. Not structural talk.*
- **实验室**：刃研社 / SCALPEL LAB — *Cutting Systems, Rebuilding Meaning*
- **公众号**：地缘推演台
- **Substack**：constructlab.substack.com
- **许可证**：MIT

---

*ConStruct Lab v1.0 — July 28, 2026*
