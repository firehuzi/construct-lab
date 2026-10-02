# ConStruct Lab 版本演进全景

> 整理于 2026-07-25。目的：理清项目里**三条并行版本号轨道**（编号互不连续）的真实演进，避免混淆。
> 核心结论：**你真正在用的东西 = 方法论 v5.x 概念 + HTML 工具 v2.2（深）做前端 + Python 引擎 v4.1（JSON）做后台/回退**；V5 是把 v4.1 这条引擎轨重做成图谱化世界模型。

---

## 轨道一：方法论 / 框架内核（纯概念，无软件）

驱动"诊断逻辑"本身的演进，和任何工具无关。当前方法论实质停在 **v5.x**，是 11 层诊断 schema 背后的概念底座。

| 版本 | 核心变化 |
|---|---|
| v1.0 | 初始构型分类（10 种国家构型） |
| v2.0 | 方法 ≠ Identity 修正（JP 冻结局 = 方法⑤，Identity = 国体） |
| v3.0 | Identity 分层（Identity ≠ 表达 ≠ 方法） |
| v4.0 | ICC（身份—能力耦合度） |
| v5.0 | DNA 矩阵（四维剖面拆解旧标签） |
| v5.x | 数据流统一（frontmatter + 桥接脚本） |

---

## 轨道二：HTML 诊断工具（实际在用的交互工具）

以下为磁盘文件 + 内部 `<title>` 标签核对结果。

| 文件 | 内部标题 | 时间 | 状态 |
|---|---|---|---|
| `content/published/地缘政治分析框架v1.1.html` | v1.1 交互式知识图谱 | Jun16 | 早期 |
| `content/published/地缘政治分析框架v1.2.html`（+ `框架v1.2.html` 副本） | v1.2 | Jun16 | 早期（有两份） |
| `content/published/地缘政治分析框架v2.0.html` | v2.0 交互式诊断（11层 + L2 瀑布） | Jul11 | 备份保留 |
| `content/published/地缘政治分析框架.html` | v2.1 | Jun22 | 浅色，后被重皮肤 |
| **`content/published/地缘政治分析框架v2.1.html`** | **v2.2 结构诊断 + SUL + 构型** | Jul24 | **当前 canonical（嵌网站）** |
| `content/published/ConStruct Lab v3.0.html` | v3.0 + SUL 层 | Jun26 | 实验版（换皮 + 删模块） |
| `theory-dice/release/construct.html` | v2.0 深色 | — | 线上 `theory-dice.pages.dev/construct`，**本地源码不在此树** |

> ⚠️ 文件名叫 `v2.1.html`，但内部已标 **v2.2**（重皮肤成深底 + 加构型下拉后没另存文件）。这就是"v2.1 实为 v2.2"的由来。

---

## 轨道三：Python 工程引擎（自动化 / 后端，编号独立于 HTML）

位于 `construct-engine/`，存储用 **JSON 文件**（非 SQLite）。

| 版本 | 文件 | 时间 | 内容 |
|---|---|---|---|
| v4.0 | `engine.py` | Jun26 | 四引擎（Identity / Signal / Consistency / SUL）+ `radar.html`，JSON 存储 |
| v4.1 | `pipeline.py` | Jun26 | + GDELT / FRED 采集 + `rules/`（CN / JP / RU / US） |

> ⚠️ **v4.0 / v4.1 是 Python 引擎，不是 HTML 工具的"下一代"**。"v4" 与工具轨的 "v2.2" 是两套独立计数。

---

## 轨道四 & 五：网站 + V5 规划

- **网站轨**：`construct-lab-site/`（Jul24，React + Vite + react-i18next，嵌 v2.2 工具，47 主体档案，Firebase 部署）。
- **V5 规划轨**：重引擎（Neo4j / PG / n8n 等），**文档级、未落地**；是从 **v4.1 引擎**升级，不是从 v2.2 工具升级。

---

## 命名上的 4 个坑

1. **"v2.0" 出现两次**：方法论轨的 v2.0（方法 ≠ Identity）≠ HTML 工具轨的 v2.0（11 层诊断），含义完全不同。
2. **磁盘上 v1.2 有两份**（`框架v1.2.html` / `地缘政治分析框架v1.2.html`）。
3. **`v2.1.html` 内部标 v2.2** —— 看文件名会低估它的实际能力。
4. **theory-dice 线上 v2.0 深色版本地源码缺失** —— 若以后要改线上版，得先找回 / 重建源。

---

## V5 切入决策（待定）

V5 文档已成熟且经评审收敛（服务 8→5、分阶段、旧系统保留作回退）。待用户拍板从哪切入：

- **A 知识图谱脊梁**（Neo4j 入 47 主体 + 关系 + 场景）
- **B 写作 RAG 引擎**（LlamaIndex）
- **C 自动信号管线**（n8n 包装现有 pipeline.py GDELT 模块）
- **D 控制室可视化**（radar.html 升级）

> 对齐点：V5 文档写"导入 46 主体"，但当前 canonical 已是 `actors/` **47** 树（多了 Taiwan）——导入源必须改对齐，否则图谱漏主体。
