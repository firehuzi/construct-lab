# ConStruct Lab 网站重建计划（construct-lab.ai.studio）

> 状态：规划稿 v1（2026-07-24）
> 定位：集成枢纽 · React/Vite SPA · 中英双语 · 深底琥珀金
> 决策依据：用户已确认「集成枢纽 + 保持 React/Vite SPA + 中英双语 + 构建时拉取(SSG) + iframe 嵌入 v2.1」

---

## 0. 现状盘点与重大发现

| 项目 | 结论 |
|------|------|
| 线上站现态 | 英文 React/Vite 单页落地页，纯琥珀金单色，钩子 "frozen settlement"（此前已抓取样式确认） |
| 本地工作区 `D:/Projects/地缘推演台` 含 | 控制室 `construct-site.zip`、Remotion 视频 `index.tsx`、**品牌 `DESIGN.md`**、`palette.json` + `variables.css`、v2.1 工具 HTML、三渠道内容产物、主体档案 |
| ⚠️ SPA 源码 | **无源码**——现站由 Google AI 自动搭建（无手写源码、无可克隆 repo）。本地仅 Remotion 视频 `index.tsx`、控制室 `construct-site.zip`、品牌 `DESIGN.md`、v2.1 工具 HTML 等资产 |
| 推论 | 无法「基于现有 repo 改造」，重建 = **全新脚手架**（同技术栈 React+Vite+Router+i18next），即 Step 0 降级方案直接执行 |

---

## 0.5 本体定位升级（2026-07-24 晚，重要）

用户给出 ConStruct Lab 的权威定义——**「复杂系统中的知识生产与意义建构框架，通过对主体、结构、关系和叙事的建模，生成对地缘政治的动态解释」**（2026-07-24 晚修正：output/subject = 地缘政治，非泛化"现实世界"）。系统架构 = 5 层知识生产管线：

```
现实世界 → 信息采集层 → 结构建模层(主体/关系/变量/状态) → 意义解释层(叙事/身份/合法性) → 知识产品层(报告/文章/视频/模型)
```

**核心定位澄清**：框架（5 层管线）是通用的方法论系统，但其**唯一核心 subject = 地缘政治**——产出的动态解释都指向地缘政治。geopolitics 不是"众多垂直应用之一"，而是当前聚焦的核心领域；框架具备横向泛化潜力（Explorer 已证方法论可泛化），但网站/内容当前只服务 geopolitics。

**与现有资产的对位**（建站/表述必须据此分层，不可混标）：

| 层 | 对应现有资产 |
|----|----|
| 现实世界 | 被观察的复杂世界（事件/行为/结构） |
| 信息采集层 | L0 世界事件&行为观察；三渠道 RSS 抓取脚本；news/event 输入 |
| 结构建模层 | **11 层诊断 schema 的 L1–L10**（主体=L1，关系=L7 他者系统/关系网，变量=连续性类型权重/存在方式权重，状态=战略选择/行动输出）；actors/ 62 档；Neo4j 知识图谱；construct-site 控制室 |
| 意义解释层 | L2 连续性类型(身份)/L3 存在方式/L6 秩序价值(合法性)；"冻结局"等结构性判断即此层产物；叙事化输出 |
| 知识产品层 | 报告=诊断001-003/EU AC危机；文章=公众号/Substack；视频=Remotion；模型=v2.1工具/Neo4j/construct-site |

**修正后的三层 taxonomy**（取代此前"方法论/框架/观察维度"的旧标法）：
1. **立场/哲学 = 结构性诊断**（diagnose structures, not predict）——贯穿框架的底层姿态
2. **框架 = 5 层知识生产管线**——真正的系统架构
3. **垂直操作化 = 11 层诊断 schema**（geopolitics 在 结构建模层 的具体工具）+ 观察维度（历史印记/自我认知/秩序延续，输入节点）

**对网站的影响**：
- 首页定位 = 「以知识生产框架为方法论、以地缘政治为核心 subject 的动态解释引擎」：geopolitics 是核心而非"众多应用之一"，但用框架视角（5 层管线）呈现，不稀释也不混标。
- /methodology 页：以 5 层管线为框架主体（图解），再下钻 11 层 geopolitics 操作化作 worked example。
- /about：ConStruct Lab = 刃研社 N01 地缘政治垂直；框架具备泛化潜力（方法论已证可横向泛化），但当前核心聚焦 = 地缘政治。
- 网站自身 = 知识产品层 的对外界面（报告/文章/视频/模型 在此汇聚，全部指向地缘政治解释）。

---

## 0.6 现实本体论（World-model ontology，2026-07-24 晚补充）

ConStruct Lab 所建模的「现实世界」本身分 **5 层**（注意：这是与 §0.5「5 层知识生产管线」**正交的两套不同「五层」**——前者是 WHAT 被建模，后者是 HOW 生产知识，表述时不可混）：

| 层 | 内容 |
|----|------|
| 物质层 Material | 地理 / 资源 / 人口 / 经济 / 军事 |
| 主体层 Subject | 国家 / 文明 / 组织 / 领导者 |
| 制度层 Institution | 联盟 / 国际组织 / 法律 / 规则 |
| 叙事层 Narrative | 身份 / 历史记忆 / 创伤 / 合法性 |
| 动态层 Dynamic | 反馈 / 路径依赖 / 风险演化 / 未来路径 |

**三者关系（建站/表述严格分层）**：
- 5 层**现实栈** = 结构建模层所建模的**世界本体（WHAT）**
- 5 层**知识管线** = 知识**生产流程（HOW）**
- 11 层**诊断 schema** = geopolitics 在结构建模层的**具体诊断程序**（遍历这 5 层现实）

本体 ≠ 流程 ≠ 程序。/methodology 页应把「现实本体论 5 层」作为结构建模层的建模对象单独呈现，与「5 层管线（流程）」和「11 层 schema（程序）」三图并列、各自标注维度。

**思想谱系（用户自述）**：现实主义（物资的，初经米尔斯海默单透镜）→ 建构主义（主体）→ 米塞斯（Mises）主体行为分析（从行动学理解国家行为与约束）→ 现「复杂系统中的知识生产与意义建构框架 / 解释系统」。触发点：看江学勤视频发现地缘政治有多种解释透镜。命名：ConStruct = construct（建构/建构主义）+ structure（结构）。

## 0.7 5W1H 使命框架（2026-07-24 17:13 补全 WHY/WHEN/WHERE + 对外文案已优化）

ConStruct Lab 的完整表达 = WHAT（§0.6 现实本体论）+ HOW（§0.5 知识管线）+ WHY/WHEN/WHERE（本小节）。构成一套可对外讲述的「使命叙事」，主要承载于 `/about` 页。

| 维度 | 内容（优化文案） |
|------|------|
| **WHAT** | 现实本体论 5 层（物质/主体/制度/叙事/动态）——被建模的世界 |
| **HOW** | 知识生产管线 5 层（现实→采集→建模→解释→产品）——生产动态解释的流程 |
| **WHY** | 地缘政治极复杂、解释多元；国家/媒体/低质内容各执一词，人极易被带偏、被误导，而对现实的认知错误代价高昂 → 故探索开放知识生产系统，让任何人更理性、更结构地理解世界 |
| **WHEN** | AI 已把人类知识智能汇聚到个人触手可及；一个人凭方法+工具即可搭建不输专业机构的系统 |
| **WHERE** | 全球任何人可用，且完全免费——理解世界的知识不该锁在付费墙或机构壁垒之后 |
| **OPEN** | 做网站+自媒体不为建封闭权威，而是让更多人知道系统、参与优化、或基于它自建——ConStruct Lab 是开放框架，而非结论 |

> 以下为 `/about` 页可直接使用的**优化文案**（中/英，2026-07-24 17:13 打磨）。已做「中立化」处理：原文"自媒体胡言乱语/被洗脑"等口语，中和为"情绪化或低质内容""被带偏、被误导"，保持理性克制品牌调性。

**WHY — 为何存在（中文）**
理解国际地缘政治，是一件极其复杂的事。同一桩事件，会有截然不同的解释：国家主体基于自身利益的叙事，传统媒体基于自身立场的 framing，情绪化或低质内容的喧嚣……大多数人在信息洪流里被带偏、被误导。而对现实的认知错误，往往代价高昂。ConStruct Lab 想做的，是一套开放的知识生产系统——让任何人都能够更理性、更结构地理解世界地缘政治，而不是被动接受某一种解释。

**WHY — Why it exists (English)**
Understanding international geopolitics is extraordinarily complex. The same event invites radically different explanations: states narrate from self-interest, legacy media from their own stance, and a flood of emotional or low-quality content adds noise. Most people get pulled off course, misled by the torrent. And being wrong about reality is costly. ConStruct Lab is an open knowledge-production system — built so anyone can understand world geopolitics more rationally and structurally, rather than passively absorbing a single account.

**WHEN — 时机（中文）**
这套系统之所以在此时可行，是因为 AI 已经把人类积累的知识与智能，汇聚到一个人触手可及的程度。今天，一个人借助一套方法加一组工具，就能搭建出不输专业机构的地缘政治分析系统。

**WHEN — Timing (English)**
What makes this viable now is that AI has aggregated humanity's accumulated knowledge and intelligence within reach of a single person. Today, one person, with a method and a toolkit, can build a geopolitical analysis system that rivals professional institutions.

**WHERE — 范围（中文）**
全世界任何人都可以使用，并且完全免费。我们相信，理解世界的知识，不该被锁在付费墙或机构壁垒之后。

**WHERE — Reach (English)**
Anyone, anywhere in the world, can use it — and it is entirely free. The knowledge to understand the world should not sit behind paywalls or institutional walls.

**OPEN — 开放参与（中文）**
我们做网站和自媒体，不是为了建立一个封闭的权威，而是让更多人知道这套系统存在、能参与优化它，也能基于它搭建属于自己的系统。ConStruct Lab 是一个开放框架，而非一个结论。

**OPEN — Open participation (English)**
We build the website and the channels not to erect a closed authority, but so more people learn this system exists, can help improve it, and can build their own systems on top of it. ConStruct Lab is an open framework, not a conclusion.

**对建站的影响**：
- `/about` = 参与 / OPEN 页（品牌故事全文已前置首页 §0.8）：如何参与优化系统、如何基于系统自建、刃研社 N01 归属说明。不再重复思想谱系+5W1H。
- 首页 Hero 的「方法论姿态」可收一句 WHY（"让所有人更理性地理解世界地缘政治"），与 frozen settlement 钩子形成「问题—方法」呼应。
- **公开文案中和**：WHY 中"自媒体胡言乱语/被洗脑"等口语，对外发布时中和为"低质/情绪化/立场性内容""易被带偏"，避免攻击性措辞、保持理性克制的品牌调性。

---

## 0.8 首页 IA（定稿，2026-07-24 17:25 用户拍板）

用户拍板三点（推翻前稿 17:17 的两处建议）：
1. 品牌故事**首页写全文**（不缩写、不去 /about）
2. 方法论 = **逻辑 主体→结构→约束→叙事**，**不是**"生产引擎横条"（5 层管线是知识生产系统，非方法论）
3. 保留"若干案例"

### 首页骨架（自上而下）
1. **Hero（定位 + 钩子）**：frozen settlement 钩子 + ConStruct Lab 一句定位（"复杂系统中的知识生产与意义建构框架，生成对地缘政治的动态解释"）+ 2 CTA（试用诊断工具 / 读案例）
2. **品牌故事（全文）**：思想谱系 + 5W1H 全叙述（WHY/WHEN/WHERE/OPEN），双语言。即原 /about 内容前置到首页。
3. **方法论（主体→结构→约束→叙事 逻辑）**：以优化后的演进句作引（见下"方法论引言·优化版"），下接 4 步逻辑链图解（每步 1 行释义 + 链 /methodology 深度）。
4. **若干案例（证明）**：2–3 张招牌诊断卡（冻结局系列 / EU AC 危机），链全文。
5. **参与入口（OPEN）**：4 枢纽卡（方法论 / 工具 / 档案 / 内容）—— 枢纽 vs 名片分界。
6. **五渠道入口（活）**：Substack / YouTube / 公众号 / GitHub / X 分区卡片（icon + 外链）；Substack/YouTube/GitHub 卡内附「最新 N 条」预览（content.json），X/公众号 仅外链。
7. **Footer**（刃研社 SCALPEL LAB · N01）。

> 注：品牌故事全文上首页后，`/about` 角色调整——改为「参与 / OPEN」页：如何参与优化系统、如何基于系统自建、刃研社 N01 归属说明。原品牌故事内容已前置首页，/about 不再重复。

### 方法论引言·优化版（用户 17:25 指定优化的那句话）
**中文**：
"我们对地缘政治的理解，起点是现实主义——世界由物资与权力塑造；随后走向建构主义，看见'主体'如何建构意义；再借米塞斯对主体行为的分析，去理解一个国家的行为从何而来、又被什么约束。走到今天，ConStruct Lab 不再是一种地缘理论，而是一个复杂系统中的知识生产与意义建构框架——更准确地说，是一套解释系统，也是一套知识生产系统。"

**English**：
"Our understanding of geopolitics began with realism — a world shaped by material power; moved to constructivism, where 'subjects' construct meaning; and then, through Mises' analysis of actor behavior, to how a state acts and what constrains it. Today, ConStruct Lab is no longer a geopolitical theory but a framework for knowledge production and meaning construction in complex systems — more precisely, an interpretive system and a knowledge-production system."

### 方法论逻辑链 主体→结构→约束→叙事（首页图解用）
- **主体 Subject**：谁在行动——国家 / 文明 / 组织 / 领导者。行为由"我们是谁"驱动。
- **结构 Structure**：主体嵌入其中的结构——物质 / 制度 / 叙事层（现实本体论 5 层）。结构划定可能性边界。
- **约束 Constraint**：主体在结构中受到的行为约束——什么走得通、什么逻辑上不可能（米塞斯：行为受手段与目标约束）。
- **叙事 Narrative**：主体为自身行为建构的意义与合法性——让结构"可被理解"，也反向巩固结构。

> 此 4 步逻辑 ≠ 11 层诊断 schema（那是 geopolitics 在结构建模层的操作化程序）。方法论逻辑是框架内核，11 层是垂直工具；不可混标。完整 11 层在 /methodology 展开。

### 方法论的目的 · Telos（用户 17:33 收口）
逻辑链 主体→结构→约束→叙事 回答"如何诊断"；其**目的**是：
1. **解释主体的行为 —— 为什么行动**（behavior explanation）：诊断不是为描述结构本身，而是解释主体为何如此行为。
2. **在场景 + 现实约束下，推演有哪些未来路径**（path enumeration）：给定结构约束与当前场景，枚举哪些路径逻辑上走得通、哪些不可能 —— 属结构性判断，**不是预测哪条会发生**。直连现实本体论「动态层 · 未来路径」（反馈/路径依赖/风险演化/未来路径）。

> 与"不做预测"立场不冲突：预测=断言未来会发生什么；本系统的未来路径=在约束下枚举可行/不可行集，把"不确定性"还给读者，仍属诊断范畴。

### taxonomy 同步（已更 MEMORY.md）
- **方法论** = 主体→结构→约束→叙事 逻辑（框架内核）
- **框架/系统** = 5 层知识生产管线（知识生产系统，非方法论）
- **垂直操作化** = 11 层 schema；**观察维度** = 历史印记/自我认知/秩序延续
- **立场** = 结构性诊断（diagnose, not predict）

---

## 1. 重建目标

把一张「营销名片」升级为 **ConStruct Lab 集成枢纽**：

1. **框架展示** — 5 层知识生产管线（系统架构，双语图解）+ geopolitics 垂直（11 层诊断 schema）作 worked example
2. **工具试用** — 在线嵌入 v2.1 诊断工具
3. **五渠道内容聚合** — YouTube / 公众号 / Substack / GitHub / X 统一入口
4. **档案浏览** — 诊断 001–003 / EU AC 危机 / 主体档案可检索

约束：中英双语、深底琥珀金、与 v2.1 及《刃研社/SCALPEL LAB DESIGN.md》母规范视觉一致。

---

## 2. 技术决策（已确认）

| 维度 | 选择 | 理由 |
|------|------|------|
| 框架 | React + Vite + React Router | 复用现有 SPA 资产，枢纽需交互 |
| 国际化 | `react-i18next` | 生态成熟，UI 文案双语；内容按原语言带 `lang` 标签 |
| 内容聚合 | 构建时拉取（SSG） | 构建阶段抓 RSS → 生成静态 `content.json`，零运行时成本、最稳 |
| 工具接入 | `iframe` 嵌入现有 `v2.1.html` | 最快上线，单文件可加载；英文态用双语说明桥接 |
| 部署 | Cloudflare Pages | 保留现部署，且可跑 Pages Functions（未来实时代理备用） |
| 视觉 | `@import variables.css` / 读 `palette.json` token | 与 v2.1、母规范严格一致，单一真源 |

---

## 3. 信息架构（路由表）

```
/                Home        Hero(frozen settlement) + 五渠道最新内容预览 + 入口卡
/methodology     框架         5 层知识生产管线图解 + 11 层 geopolitics 操作化(worked example) + 双语说明
/tool            工具         iframe 嵌入 v2.1.html（双语说明桥接）
/content         内容枢纽     五渠道分区卡（Substack/YouTube/GitHub 附最新预览 + 公众号/X 仅外链），来源 badge + 外链
/archive         档案        诊断 001–003 / EU AC 危机 / 主体档案 可浏览检索
/about          关于         刃研社 SCALPEL LAB · N01 定位
```

语言切换器固定在 Header 右上角，记忆用户选择（`localStorage`）。

---

## 4. 内容聚合方案（SSG）

| 渠道 | 源 | 备注 |
|------|----|------|
| Substack | `https://constructlab.substack.com/feed` | 官方 RSS，可直接抓 |
| YouTube | 频道 RSS（`https://www.youtube.com/feeds/videos.xml?channel_id=...`）或 Data API | 需 channel id |
| 公众号 | 无官方 RSS | **仅外链跳转**：内容与其他平台同步同质，不抓全文；链接出去即可（可选：后续接代理源再补自动拉取） |
| GitHub | `https://github.com/firehuzi.atom`（用户公开动态） | 官方 Atom，无需鉴权可抓公开活动；承载「代码/工具更新」类内容（Release / Commit）。**用户 17:44 明确：用账号级 feed 即可**（新工具尚未上传 GitHub，等上传后会自然出现在该 feed 中） |
| X (Twitter) | 无官方 RSS、无免费 API | **仅外链跳转**：不抓全文、不接代理；各平台文章同步同质，链接到 X 主页/推文即可 |

> **设计原则（用户 17:42 明确）**：各平台文章基本同步、内容同质 —— 故内容枢纽**以「外链跳转」为主，不追求全文抓取与跨平台去重合并**。仅对**有免费 feed 的渠道**（Substack / YouTube / GitHub）做轻量「最新」预览（构建期拉取），用于首页/枢纽的"活气"；X 与公众号一律**只放外链卡片**，不做内容抓取。这样省去 RSS 代理/付费 API 的维护债，也避免同质内容重复堆叠。

**构建脚本** `scripts/fetch-content.mjs`（仅针对有免费 feed 的渠道）：
1. `fetch` Substack / YouTube / GitHub atom → 解析 RSS/Atom
2. 归一化为统一结构 `{ id, title, summary, url, source, lang, date, cover? }`
3. 写入 `src/data/content.json`（构建期产物，不入库）
4. X / 公众号 **不进入抓取**，仅在站点配置里登记外链（`channels.json`：名称 + URL + icon）

**`/content` 页**：五渠道分区卡片（每渠道一张卡，含 icon + 简介 + 外链按钮）；Substack/YouTube/GitHub 卡内附「最新 N 条」预览（来自 content.json），X/公众号 卡仅外链。渠道筛选退化为分区锚点，不做跨平台合并流（内容同质，无需去重）。

---

## 5. 工具接入

- 将 `content/published/地缘政治分析框架v2.1.html` 复制为 `public/tool.html`
- `/tool` 路由 `<iframe src="/tool.html">` 全屏加载
- 英文态：工具 UI 仍为中文，页面附英文引导文案（"This diagnostic tool is currently Chinese-only; an English build is on the roadmap"）+ 方法论页作概念桥接
- 长期（v2）：把 v2.1 移植为 React 组件，实现语言切换联动

---

## 6. 视觉与组件

- 严格遵循 `videos/brandkit/construct-lab.ai.studio_DESIGN.md`：深底 `#0f131e` + 琥珀金 `#e8b44c` 双主色，辅色仅语义编码
- 字体：Playfair Display + Notion Serif SC（标题）/ Inter（正文）/ IBM Plex Mono（数据、编号、坐标轴）
- 复用 `variables.css`（`@import`），不另写色值
- 组件草案：
  - `Layout` / `Header`（含语言切换）/ `Footer`
  - `Hero`（衬线大标题 + 一句话定位）
  - `ContentCard`（渠道卡片，来源 badge）
  - `ArchiveCard`（档案卡，锁定模式 badge 复用 palette.badge 九型）
  - `MethodologyDiagram`（11 层结构图解，SVG/交互）
  - `Badge`（锁定模式九型，teal/coral/gold/blue/purple 语义色）

---

## 7. 数据流程

```
构建期:  fetch-content.mjs ──fetch──▶ Substack/YouTube/公众号 RSS + GitHub atom (+ X 手动 JSON)
                             ──normalize──▶ src/data/content.json
运行期:  React SPA ──import content.json──▶ /content 渲染
         iframe ──▶ /tool.html (v2.1)
         i18n ──▶ en/zh 文案切换
```

---

## 8. 文件结构草案（基于现有 repo 改造）

```
construct-lab-site/            # 现有 repo（Step 0 定位/克隆）
├── index.html
├── vite.config.ts
├── package.json
├── src/
│   ├── main.tsx
│   ├── App.tsx                # Router + i18n provider
│   ├── i18n/
│   │   ├── index.ts
│   │   ├── zh.json
│   │   └── en.json
│   ├── styles/
│   │   └── tokens.css         # @import variables.css（或复制 token）
│   ├── data/
│   │   └── content.json       # 构建期生成
│   ├── components/            # Layout/Header/Hero/ContentCard/...
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Methodology.tsx
│   │   ├── Tool.tsx
│   │   ├── Content.tsx
│   │   ├── Archive.tsx
│   │   └── About.tsx
│   └── content/               # 档案 MD/JSON（诊断/危机/主体）
├── public/
│   └── tool.html              # v2.1 复制而来
└── scripts/
    └── fetch-content.mjs      # 构建期 RSS 拉取
```

---

## 9. 分阶段里程碑

### Step 0 — 全新脚手架（无既有源码，已确认）
- [x] 初始化 Vite + React + TypeScript 项目（同技术栈，不依赖旧 repo）→ `D:/Projects/地缘推演台/construct-lab-site/`
- [x] 安装 `react-router-dom` / `react-i18next` / `i18next`
- [x] 接入 `variables.css` / palette token，落实 `DESIGN.md` 规范
- [ ] 本地 `dev` 跑通空壳，确认 Cloudflare Pages 构建 / 部署链路 → **已 build 通过（2026-07-24 17:5x），preview 跑在 :3000**

### P0 — 脚手架 + 规范接入（已完成 2026-07-24 17:5x）
- [x] Vite + React + React Router 多路由（/ /methodology /tool /content /archive /about）
- [x] 接入 `react-i18next`，`zh.ts` / `en.ts` 双语（品牌故事全文 + 方法论逻辑链 + 案例 + 五渠道均双语）
- [x] `src/styles/variables.css`（复制自 brandkit palette v2.2.0）+ `global.css` 落地 token
- [x] Header 语言切换器（localStorage 记忆）
- [x] 首页 6 区块落地：Hero + BrandStory(全文) + Methodology(主体→结构→约束→叙事) + Cases + EntryCards + Channels(五渠道)
- [x] 五渠道已配：微信公众号·地缘推演台 / Substack·Construct Lab / X·@xheiheihei1118 / YouTube·@TheConStructLab / GitHub·@firehuzi（`src/data/channels.ts`）
- [ ] Tool iframe 接真实 v2.1：将 `content/published/地缘政治分析框架v2.1.html` 复制到 `public/tool.html`（当前为占位页）
- [ ] /methodology 三层框架图解深化、/archive 接入 actors/、/content 接 fetch-content.mjs（P2/P3）

### P1 — 静态骨架（可上线）
- [ ] Home（Hero + 三渠道预览卡 + 入口）
- [ ] /methodology（11 层图解 + 双语）
- [ ] /about（刃研社 N01）
- [ ] 响应式 + 布局组件

### P2 — 内容聚合（SSG）
- [ ] `scripts/fetch-content.mjs`：Substack + YouTube + GitHub atom（公众号 / X 不抓，仅 channels.json 登记外链）
- [ ] `/content` 页：筛选 / 语言标签 / 来源 badge / 外链
- [ ] npm `prebuild` 钩子接入构建

### P3 — 工具与档案
- [ ] `public/tool.html` = v2.1 复制；`/tool` iframe + 双语说明
- [ ] `/archive`：诊断 001–003 / EU AC 危机 / 主体档案浏览检索

### P4 — 打磨 + 部署
- [ ] SEO：每页 title/description + Open Graph + 中英文 hreflang
- [ ] 部署 Cloudflare Pages；与母规范视觉对齐巡检
- [ ] 公众号 RSS 源就位后补全 /content

---

## 10. 风险与待确认

1. **现有源码** — 现站由 Google AI 自动搭建，无手写源码 / 可克隆 repo；重建 = 全新脚手架（已定，无阻塞）
2. **公众号 RSS 源** — 无官方 RSS；需代理源或手动 JSON，否则该栏先占位
3. **X (Twitter) 与 公众号** — 均无官方 RSS/免费 API；按用户 17:42 决策**仅外链跳转**（内容跨平台同步同质，不抓全文、不接代理），省去维护债
4. **双语内容策略** — 方法论页需双语撰写；工具英文态暂中文 UI + 说明桥接
4. **与刃研社主站关系** — 本站立独立 React SPA（非 Astro），视觉靠 token 对齐；后续可评估统一部署，本期不并

---

## 11. 验收标准

- [ ] 6 个路由全部可访问，语言切换全站生效
- [ ] /content 五渠道分区卡就位（Substack/YouTube/GitHub 附最新预览 + 公众号/X 仅外链）；GitHub 标注 Release/Commit 类型
- [ ] /tool 可在线试用 v2.1，视觉与站一致
- [ ] /archive 可浏览已跑诊断与主体档案
- [ ] 视觉 100% 遵循 DESIGN.md + palette token（WCAG 体检通过）
- [ ] 部署 Cloudflare Pages，域名 construct-lab.ai.studio 可访问
