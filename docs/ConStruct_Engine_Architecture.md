# ConStruct Engine · 技术架构设计

> 版本：v0.1（概念设计）
> 日期：2026-06-19
> 基于：ConStruct v2.0因果链模型 + 全球主体档案库 + Diagnostic #001/#002实战经验

---

## 〇、核心洞察

**ConStruct的规则是显式的，不是统计式的。**

这意味着：
- 不需要ML/AI训练——规则是人写出来的，不是数据喂出来的
- Identity解释规则=IF-THEN映射（老龄化→中国解释为产业升级）
- 信号检测规则=异常性判断（违背正常行为逻辑的事件）
- Strategy Selection一致性=方向匹配（5个行动是否指向同一方向）
- Response Elasticity=历史响应记录（过去3-5次危机的弹性数据）

**引擎的本质：** 不是"AI学会分析"，是**"把已有的分析判断形式化为可执行规则，然后用代码运行这些规则"**。

---

## 一、架构总览

```
ConStruct Engine

┌─────────────────────────────────────────────────────┐
│                   Output Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│  │ 诊断报告  │ │ Radar UI │ │ 档案更新  │ │ 信号推送 ││
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘│
├─────────────────────────────────────────────────────┤
│                 Processing Layer                     │
│  ┌──────────────┐ ┌────────────┐ ┌───────────────┐ │
│  │ Identity      │ │ Signal     │ │ Consistency   │ │
│  │ Interpreter   │ │ Detector   │ │ Checker       │ │
│  │ (DEL翻译)     │ │ (异常判断) │ │ (↑↓→方向)    │ │
│  └──────────────┘ └────────────┘ └───────────────┘ │
│  ┌──────────────┐                                   │
│  │ Elasticity   │                                   │
│  │ Tracker      │                                   │
│  └──────────────┘                                   │
├─────────────────────────────────────────────────────┤
│                   Storage Layer                     │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ SQLite DB    │ │ MD Files │ │ Rule JSONs      │ │
│  │ (结构化元数据)│ │ (人可读) │ │ (可执行规则)   │ │
│  └──────────────┘ └──────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────┤
│                 Data Collection Layer                │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ DEL-1        │ │ DEL-2    │ │ DEL-3           │ │
│  │ (年级数据)   │ │ (月级)   │ │ (日级事件)      │ │
│  │ WB/IMF API   │ │ RSS+API  │ │ News API+手动   │ │
│  └──────────────┘ └──────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 二、存储层

### 2.1 双轨存储：SQLite + Markdown

**为什么双轨？**
- SQLite：机器可读、可查询、可比较、可自动化
- Markdown：人可读、可写作、可直接复制到公众号/Substack
- 两者必须同步——SQLite是主存储，Markdown是从SQLite生成的

**关键原则：SQLite是唯一的数据真相源。Markdown永远是从SQLite生成的，不是手动编辑的。修改SQLite→自动重新生成Markdown。**

### 2.2 SQLite Schema（核心表）

| 表名 | 用途 | 每主体行数 |
|------|------|----------|
| subjects | 主体基础信息+方向+版本 | 1 |
| identity_layers | L2-L8定位 | 8 |
| del_baseline | DEL-1/2/3数据+Identity解释 | 20-30 |
| del_translation_rules | DEL翻译规则（可执行） | 5-8 |
| strategy_space | 策略空间路径+可用性 | 4-6 |
| strategy_selection | Strategy Selection操作机制 | 4 |
| response_elasticity | 弹性三维度 | 1 |
| elasticity_history | 历史弹性记录 | 3-5 |
| signal_rules | 信号检测规则（可执行） | 5-8 |
| event_chain | 关键事件链 | 5-10 |
| actions | 行动记录（一致性检测用） | 持续累积 |
| cross_references | 档案间对照关系 | N |

### 2.3 Rule JSONs（可执行规则文件）

每个主体的信号检测规则+DEL翻译规则，以JSON格式单独存储：

```
ConStruct_Archive/
├── rules/
│   ├── US_signals.json      -- 美国信号检测规则
│   ├── US_del_rules.json    -- 美国DEL翻译规则
│   ├── EU_signals.json
│   ├── EU_del_rules.json
│   ├── Israel_signals.json
│   ├── Israel_del_rules.json
│   ├── Japan_signals.json
│   ├── Japan_del_rules.json
│   ├── Iran_signals.json
│   ├── Iran_del_rules.json
│   └── ...
```

**信号规则示例（US）：**

```json
{
  "subject_id": "US",
  "rules": [
    {
      "rule_id": "US-SIG-01",
      "trigger": "exit_agreement",
      "normal_behavior": "交易式Identity允许退出=重新交易",
      "abnormal_condition": "exit_then_cannot_return",
      "direction": "↓",
      "causal_chain": "退出→回来=信誉受损→策略空间被锁",
      "priority": 1
    },
    {
      "rule_id": "US-SIG-02",
      "trigger": "dollar_reserve_decline",
      "normal_behavior": "储备占比缓慢下降=长期趋势",
      "abnormal_condition": "储备占比+SWIFT占比同时下降",
      "direction": "↓↓",
      "causal_chain": "美元使用+信心双降=体系受损=Identity危机",
      "priority": 2
    }
  ]
}
```

**DEL翻译规则示例（US）：**

```json
{
  "subject_id": "US",
  "rules": [
    {
      "rule_id": "US-DEL-01",
      "variable_type": "oil_price_drop",
      "interpretation": "低油价=叙事窗口打开→肯定性锚点强化",
      "strategy_effect": "↑ 交易叙事更容易成功",
      "exceptions": [
        {"condition": "oil_drop_caused_by_US_weakness", "effect": "↓"}
      ]
    },
    {
      "rule_id": "US-DEL-02",
      "variable_type": "allies_burden_sharing",
      "interpretation": "交易式Identity允许=盟友付费是正常交易",
      "strategy_effect": "→ 正常操作",
      "exceptions": [
        {"condition": "allies_refuse_and_leave", "effect": "↓ 交易网络受损"}
      ]
    }
  ]
}
```

---

## 三、数据采集层

### 3.1 DEL-1 基础条件（年级）

**数据源：**

| 变量 | 来源 | API | 频率 |
|------|------|-----|------|
| GDP | World Bank | WB API v2 | 年级 |
| 人口 | World Bank | WB API v2 | 年级 |
| 军费 | SIPRI | SIPRI API | 年级 |
| 贸易结构 | UN COMTRADE | COMTRADE API | 年级 |
| 能源依赖 | IEA | IEA API | 年级 |
| 外汇储备 | IMF | IMF API | 月→年聚合 |
| 美元储备占比 | IMF COFER | IMF API | 季→年聚合 |
| 债务/GDP | IMF WEO | IMF API | 年级 |

**MVP阶段：手动输入**。API采集是Phase 2任务。

### 3.2 DEL-2 策略变量（月级）

**数据源：**

| 变量 | 来源 | 方法 |
|------|------|------|
| 油价 | EIA | API |
| 利率 | BIS | API |
| 选举日程 | 各国公开 | 手动标注 |
| 制裁变化 | OFAC/EU | RSS |
| 军演部署 | 公开 | RSS+手动 |
| 外交动向 | 新闻 | RSS+关键词 |

**MVP阶段：手动标注**。RSS采集是Phase 2任务。

### 3.3 DEL-3 事件脉冲（日级）

**来源：**

| 来源 | 方法 | 用途 |
|------|------|------|
| Reuters/BBC/AP RSS | 关键词过滤 | 重大事件自动检测 |
| GDELT事件数据库 | GDELT API | 全球事件量化 |
| ACLED | ACLED API | 军事/政治事件 |
| 手动标注 | CLI工具 | 人工判断的事件 |

**MVP阶段：手动标注（CLI工具）**

### 3.4 事件标注CLI（MVP核心工具）

```python
# construct annotate
# 手动标注事件

> 事件描述: 美国宣布与伊朗签署备忘录
> 主体: US (从列表选择)
> 方向: ↑ (从 ↑↓→↓↓↑↑ 选择)
> Identity指令: "达成新交易=肯定性锚点强化"
> 与Identity一致? Y

→ 写入actions表
→ 触发一致性检测
→ 如果方向变化持续→触发档案更新
```

---

## 四、处理层

### 4.1 Identity Interpreter（DEL翻译引擎）

**输入：** DEL数据 + Identity翻译规则
**输出：** Identity解释 + 策略空间约束变化

**运行逻辑：**
```
新DEL数据 → 查匹配的翻译规则 → 输出解释 → 输出策略空间变化
```

**关键：翻译规则不是ML推出来的，是人写出来存进JSON的。引擎只做"查匹配+输出"，不做"推理"。**

### 4.2 Signal Detector（信号检测引擎）

**输入：** 事件 + 信号规则
**输出：** 异常性判断 + 方向判断 + 因果链

**运行逻辑：**
```
事件输入 → 匹配相关主体的信号规则
  → 判断是否违背正常行为逻辑
    → 异常 → 方向+因果链
    → 正常 → 不触发更新
  → 跨主体异常对比（多主体同方向=结构性信号）
  → 输出信号报告
```

### 4.3 Consistency Checker（一致性检测引擎）

**输入：** 最近N个行动 + Identity核心指令
**输出：** 方向一致性判断 + ↑↓→箭头

**运行逻辑：**
```
读取最近5-8个行动 →
  每个行动标注方向 →
  检查与Identity核心指令一致性 →
  统计方向分布：
    全部同方向 = 系统性调整
    多方向矛盾 = 内部矛盾投影
    不明确 = 摇摆中
  → 输出↑↓→
```

**日本案例：5↑=冻结局适应性微调 ✓**
**EU案例：3↑+3↓=整合式悖论 ✓**

### 4.4 Elasticity Tracker

**手动标注+趋势追踪。每次重大事件后记录：响应时间/调整成本/是否过冲。追踪弹性变化趋势。**

---

## 五、输出层

### 5.1 档案自动更新

```
方向变化持续3天 → 确认 → 更新SQLite → 重新生成Markdown → 更新索引
```

### 5.2 诊断报告生成

**MVP阶段：手动写作。** 模板辅助（Jinja2填充DEL数据+方向判断+一致性数据），但核心诊断仍由人写。

**Phase 3：半自动。** 信号→检测→定位→判断自动运行，条件性判断人工确认，报告自动生成。

### 5.3 Radar Dashboard

**初期：静态HTML，每日Python脚本更新**

```
Radar HTML页面（仅美国MVP版）：

├── 事件雷达：最新5个标注事件
├── 方向箭头：US →（维持）
├── 一致性图表：最近5个行动方向柱状图
├── DEL快照：DEL-2关键变量最新值
├── 信号列表：异常信号+方向+因果链
└── 弹性追踪：反馈速度/调整成本/过冲风险趋势图
```

**技术：HTML + Chart.js + Tailwind CSS。零依赖、本地可运行、可部署CloudStudio。**

---

## 六、技术栈

| 层 | 技术 | 选型理由 |
|------|------|---------|
| 存储 | SQLite + Markdown | 轻量、无依赖、人机双轨 |
| 数据采集 | Python + requests | 公开数据源有Python库 |
| 规则引擎 | Python + JSON | 规则显式，不需要框架级引擎 |
| 输出 | Jinja2模板 | MD/HTML报告生成 |
| Radar UI | HTML + Chart.js + Tailwind | 零依赖、本地可运行 |
| 定时执行 | cron/Task Scheduler | 数据采集+引擎运行 |
| 版本管理 | Git | 档案版本追踪 |
| CLI工具 | Python + argparse | 事件标注+查询+更新 |

**不选什么：**
- 不选Django/Flask（MVP不需要Web服务器）
- 不选MongoDB（数据结构明确，关系型更合适）
- 不选ML/AI（规则是显式的）
- 不选React/Vue（Radar初期是静态页面）

---

## 七、技术解决什么 / 不能解决什么

### 技术能解决的（7个问题）

| # | 问题 | 技术方案 | 效果 |
|---|------|---------|------|
| 1 | 档案格式不统一 | SQLite schema强制标准化 | 每份档案格式完全一致 |
| 2 | DEL数据采集耗时 | API/RSS自动采集 | 每月自动更新 |
| 3 | 事件遗漏 | 新闻RSS+关键词过滤 | 自动捕获重大事件 |
| 4 | 一致性检测靠直觉 | 行动方向记录+规则匹配 | 可量化、可回溯 |
| 5 | 档案更新不及时 | 自动触发更新机制 | 方向变化3天→自动更新 |
| 6 | 跨主体比较困难 | SQLite查询 | 一条SQL出对照表 |
| 7 | 诊断报告格式不统一 | Jinja2模板 | 格式完全一致 |

### 技术不能解决的（4个问题）

| # | 问题 | 为什么 | 需要什么 |
|---|------|--------|---------|
| 1 | Identity定位判断 | "美国是交易式"不是从数据推出来的 | 人做判断→写入数据库 |
| 2 | DEL翻译规则首次编写 | 同一数据×不同Identity=不同解释 | 人写规则→录入JSON |
| 3 | 信号异常性首次判断 | "什么是正常行为"需要分析 | 人写规则→录入JSON |
| 4 | 条件性判断的质量 | "逻辑上只能这样"需要因果推理 | 人写诊断→引擎辅助 |

**总结：技术解决的是"执行/存储/采集/格式化"层面的问题。核心的"判断/定位/推理"层面仍需要人做——引擎把人的判断形式化、存储、自动化运行、持续追踪。**

---

## 八、开发路线图

### Phase 0（当前）：手动建档

- 手动写Markdown档案
- 手动标注事件
- 手动写作诊断报告
- 已完成：5份种子档案+模板+索引

### Phase 1（1-2周）：SQLite+CLI+同步

```
目标：把现有档案从MD迁移到SQLite，建立CLI工具

├── 创建SQLite schema + 导入5份已有档案数据
├── 从档案中提取规则→生成Rule JSONs
├── MD→SQLite双向同步（SQLite为主存储，MD自动生成）
├── 事件标注CLI（construct annotate）
├── 档案查询CLI（construct query US --layer=L2）
├── 一致性检测CLI（construct check US）
└── 继续手动建档剩余主体（SQLite格式直接写入）

→ 产出：可运行的CLI工具 + SQLite数据库 + 5份档案已迁移
```

### Phase 2（2-4周）：引擎核心+美国30天实验

```
目标：引擎核心模块运行 + 美国30天实验技术支撑

├── Identity Interpreter运行（DEL翻译规则匹配）
├── Signal Detector运行（信号规则匹配）
├── Consistency Checker运行（行动方向一致性检测）
├── Elasticity Tracker运行（弹性历史记录）
├── DEL-2手动采集30天（每天标注1-2个事件/数据点）
├── 方向变化确认→档案自动更新30天
├── 静态Radar HTML（美国单主体版）

→ 产出：引擎核心模块可运行 + 美国30天数据 + Radar MVP版
```

### Phase 3（4-8周）：数据管道+多主体扩展

```
目标：DEL数据半自动采集 + 扩展到所有Tier 1主体

├── DEL-1 API采集脚本（World Bank + IMF）
├── DEL-2 RSS采集脚本（新闻关键词过滤）
├── 信号检测半自动化（RSS事件→规则匹配→人工确认）
├── 所有Tier 1档案完成（8份）
├── 所有Tier 2档案完成（7份）
├── Radar多主体版（方向箭头+对照表）

→ 产出：半自动数据管道 + 15份完整档案 + 多主体Radar
```

### Phase 4（8-12周）：半自动诊断+持续运行

```
目标：诊断报告半自动生成 + 系统持续运行

├── 诊断报告模板（Jinja2填充+人工确认）
├── 档案季度扫描机制
├── Radar实时更新（每日脚本）
├── 信号推送机制（异常信号→通知）
├── Elasticity趋势追踪可视化

→ 产出：半自动运行的分析系统
```

---

## 九、MVP开发清单

**MVP=美国30天实验的技术支撑，约8-10天开发量**

| # | 任务 | 预估 | 说明 |
|---|------|------|------|
| 1 | SQLite schema创建 | 1天 | 按上文设计建表 |
| 2 | 美国档案数据导入 | 1天 | 从MD提取→写入SQLite |
| 3 | 美国Rule JSONs提取 | 1天 | 从档案信号检测规则+DEL翻译规则→JSON |
| 4 | 事件标注CLI | 1天 | construct annotate命令 |
| 5 | 档案查询CLI | 0.5天 | construct query命令 |
| 6 | 一致性检测脚本 | 1天 | 读取actions→方向统计→输出↑↓→ |
| 7 | SQLite→MD同步脚本 | 0.5天 | 从SQLite生成Markdown档案 |
| 8 | DEL翻译引擎(v0.1) | 2天 | 读取DEL数据+规则→输出解释 |
| 9 | 信号检测引擎(v0.1) | 1天 | 事件+规则→异常判断+方向 |
| 10 | 静态Radar HTML | 2天 | 美国单主体版 |

**总计：约10天**

---

## 十、文件结构

```
construct-engine/
├── db/
│   ├── construct.db          -- SQLite主数据库
│   └── schema.sql            -- Schema定义
├── rules/
│   ├── US_signals.json
│   ├── US_del_rules.json
│   ├── EU_signals.json
│   ├── EU_del_rules.json
│   ├── Israel_signals.json
│   ├── Israel_del_rules.json
│   ├── Japan_signals.json
│   ├── Japan_del_rules.json
│   └── Iran_signals.json
│   └── Iran_del_rules.json
├── archives/
│   ├── Tier1/
│   │   ├── US.md             -- 从SQLite自动生成
│   │   ├── EU.md
│   │   ├── Israel.md
│   │   ├── Japan.md
│   │   ├── Iran.md
│   │   ├── China.md
│   │   ├── Russia.md
│   │   └── India.md
│   ├── Tier2/
│   │   ├── Singapore.md
│   │   ├── Serbia.md
│   │   ├── UK.md
│   │   ├── Germany.md
│   │   ├── France.md
│   │   ├── Turkey.md
│   │   ├── Saudi.md
│   │   └── SouthKorea.md
│   ├── Index.md              -- 从SQLite自动生成
│   ├── Template.md           -- 手动维护
│   └── StrategicPlan.md      -- 手动维护
├── engine/
│   ├── identity_interpreter.py   -- DEL翻译引擎
│   ├── signal_detector.py        -- 信号检测引擎
│   ├── consistency_checker.py    -- 一致性检测引擎
│   ├── elasticity_tracker.py     -- 弹性追踪引擎
│   └── archive_updater.py        -- 档案更新引擎
├── collectors/
│   ├── del1_collector.py         -- DEL-1年级数据采集
│   ├── del2_collector.py         -- DEL-2月级数据采集
│   └── del3_annotator.py         -- DEL-3事件标注
├── generators/
│   ├── archive_md_generator.py   -- SQLite→MD生成器
│   ├── diagnostic_generator.py   -- 诊断报告生成器
│   └── radar_generator.py        -- Radar HTML生成器
├── cli/
│   ├── construct.py              -- CLI入口
│   ├── annotate.py               -- 事件标注
│   ├── query.py                  -- 档案查询
│   ├── check.py                  -- 一致性检测
│   └── update.py                 -- 手动更新档案
├── radar/
│   ├── index.html                -- Radar静态页面
│   ├── data.json                 -- Radar数据（从SQLite导出）
│   └── assets/
│       ├── chart.js
│       └── tailwind.css
├── templates/
│   ├── archive_template.md       -- 档案Markdown模板
│   └── diagnostic_template.md    -- 诊断报告模板
├── config/
│   ├── subjects.json             -- 主体列表+Tier分类
│   ├── del_sources.json          -- DEL数据源配置
│   └── rss_keywords.json         -- RSS关键词过滤配置
└── run.py                        -- 每日运行脚本
```

---

*ConStruct Engine · 技术架构设计 v0.1 | 2026-06-19 | 下一步：Phase 1 SQLite+CLI开发*