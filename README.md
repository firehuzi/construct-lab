# ConStruct Lab

> **结构驱动的知识与意义建构系统。**
> 
> 地缘政治的分析被叙事锁定了。智库在推销立场，媒体在放大恐惧。没有一个工具能回答最简单的问题：**"这个判断从哪里来的？能不能推翻它？"**
>
> ConStruct Lab 用 200 年战争数据、40 年冲突日志和每日新闻脉冲，**枚举结构上可能的路径，排除逻辑上不可能的路径**。所有判断锚定在可追溯的数据上。所有假设设计为可被数据反证。
>
> *"Diagnose structures, not predict futures."*

---

## 核心能力

- **三层时间尺度数据底座**：COW 骨架（1816-2014）× UCDP 肌肉（1989-2025）× GDELT 脉冲（每日）
- **11 层诊断框架**：从地表事件（L0）钻到地幔构型（L10）——地缘政治的 MRI
- **53 个主体覆盖**：8 个大国 + 16 个区域强国 + 29 个企业/组织
- **八节点全自动日更环**：每天 CST 08:00，采集→验证→预警→反证→入库→生成地图
- **可被证伪的设计**：53 主体 × 114 项验证项，行为偏离假设 → 自动降低置信度 → 触发人工复核
- **反洗脑内容标准**：数据锚定 + 结构驱动 + 叙事识别 + 不确定性标注

## 快速开始

```bash
# 世界冲突时间地图 —— 立即查看
open https://construct-lab.site/map

# 运行诊断（需要 DeepSeek API key）
export DEEPSEEK_API_KEY=sk-xxx
python publish_article.py CHN

# 启动数据栈
cd construct-stack && docker compose up -d
```

## 项目结构

```
construct-engine/        # 主引擎
├── engine_v5.py         # 诊断引擎（Identity→Method→Fear）
├── publish_article.py   # 结构诊断文章生成器（DeepSeek）
├── generate_world_map.py# 交互式世界冲突地图
├── collect_gdelt.py     # GDELT 双轨采集（actor + structural）
├── verify_events.py     # 三级验证系统
├── detect_anomaly.py    # 异常预警
├── detect_structure_contradictions.py  # 结构反证检测
├── quick_take_autopilot.py  # 事件快评自动生成
├── feedback_rules.json  # 53主体×114验证项
├── content/
│   ├── articles/        # 结构诊断文章
│   └── lexicon/         # 结构词典
└── visuals/             # 地图 HTML

construct-stack/         # Docker 栈
├── docker-compose.yml   # PG+Neo4j+n8n+runner
├── init-pg.sql          # 数据库架构
└── scripts/             # n8n runner 脚本

actors/                  # 53 个主体档案（Markdown）
```

## 数据源

| 数据源 | 规模 | 时间跨度 | 用途 |
|---|---|---|---|
| UCDP GED | 42 万条 | 1989–2025 | 全球冲突事件 |
| GDELT 2.0 | ~700 条/天 | 实时 | 新闻情绪脉冲 |
| COW | MID+War+Alliance | 1816–2014 | 战争/同盟骨��� |
| FRED | 10 标的 | 实时 | 金融/价格信号 |
| Kaggle War Records | 10,684 条 | 1800+ | 近代战争补缺 |

## 贡献

ConStruct Lab 欢迎**用数据而非立场说话**的贡献者。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解角色（实体对齐/内容审订/词典编纂/代码）和流程。

**Good First Issues**（适合新贡献者）：
- 补充 `country_coords` 中缺失的国家坐标
- 为未完成的 Tier2/Tier3 主体撰写 actor_timelines JSON
- 审阅 `content/audit_queue/review/` 中的事件快评草稿
- 为结构词典撰写新条目（模板见 `content/lexicon/`）

## 反洗脑四标准

所有内容产出必须满足：

1. **数据锚定** — 每个判断追溯到 GDELT/COW/UCDP
2. **结构驱动** — 能看到"身份→方法→行为"的逻辑链
3. **叙事识别** — 每份报告有"别被哪种叙事忽悠"
4. **不确定性标注** — [高/中/低，依据: …]

## 许可

MIT License — 见 [LICENSE](LICENSE)

## 署名

- **系统**: ConStruct Lab — *Structural diagnosis. Not structural talk.*
- **实验室**: 刃研社 / SCALPEL LAB — *Cutting Systems, Rebuilding Meaning*
- **公众号**: 地缘推演台
- **Substack**: [constructlab.substack.com](https://constructlab.substack.com)
- **站点**: [construct-lab.site](https://construct-lab.site)
