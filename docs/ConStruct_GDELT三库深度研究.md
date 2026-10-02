# GDELT 三库深度研究（gdelt-py / gdeltPyR / get_gdelt_data）

> 研究日期：2026-07-25 · 背景：Phase 0/0.5/1/1.5 已用 `gdelt-py` 跑通真实落库 1529 行。
> 本文回答三个问题：①现役选型是否仍最优 ②另外两库有无互补价值 ③下一步可白嫖什么能力。

---

## 1. gdelt-py（RBozydar/py-gdelt）— 现役主采集器 ✅

**版本**：0.1.11（2026-06-27 发布）· Python 3.11+ · Alpha 但开发活跃（月度发版）

### 能力全景（比我们当前用到的多得多）
| 端点 | 覆盖 | 对 ConStruct 的价值 |
|---|---|---|
| **Events v1/v2**（现用） | 1979+ / 2015+，文件源+BQ 兜底 | 已接入，1529 行落库 |
| **Mentions** ⭐ | 2015+，文件源+BQ 兜底 | **验证环升级关键**：同一 global_event_id 被多少个不同域名提及 = 单源内部佐证强度，可把 cross_checked 规则从"三元组共现"升级为"多域名印证" |
| **GKG v1/v2** ⭐ | 2013+，主题/实体/语调/引文 | 对接**叙事层（L4/L8）**：主题标签+tone 可量化叙事氛围 |
| **GQG 引文图** | 2020+ | 领导人原话引文 → 叙事/话语分析素材 |
| DOC/GEO/Context/TV | REST，滚动窗口 | DOC 仅全文检索（无 actor 对，上次已证伪 mode=Event） |
| NGrams/VGKG/GFG/GEMG… | 文件源 | 暂无需求 |

### 关键机制确认
- **FileSource 优先 + BigQuery 兜底**：`pip install gdelt-py[bigquery]` 才启用 BQ（基础安装不依赖，#104 明确 optional）。不配 GCP 也能跑（我们现状）。
- **限流韧性**：`GDELTSettings(timeout=60, max_retries=5)`，0.1.9 强化了 rate-limit 熔断电路（circuit state），限流后重置瞬时错误。
- **同步包装**：`query_sync/stream_sync` 可用（collector 现用），`stream` 生成器省内存。
- **国家码坑已修**：IRN 报错 → normalize() 自动转 FIPS（IR），#62 修复。

### 风险清单
1. **Alpha + 单维护者 + 低星**：API 可能破坏性变更 → 建议 requirements 锁 `gdelt-py==0.1.11`，升级前先跑 dry-run 回归。
2. **不支持 translingual 翻译源**：README/端点均无 translingual → 采集偏英文媒体视角（对中俄伊等主体的报道有系统性口径偏差）。这是**数据保真的口径盲点**，应记入 sources 表的 bias 备注。
3. CI 忽略了三个传递依赖 CVE（filelock/pyasn1/virtualenv），非直接依赖，风险低。

---

## 2. gdeltPyR（linwoodc3）— 经典但已停更 ❌ 淘汰

- **最后提交 2023-10-31**，此前沉寂多年；BigQuery"coming soon"多年未上线。
- 全内存 pandas（V2 全天 ~500MB，OOM 风险明确写在 Known Issues）；无限流处理。
- 能力被 gdelt-py 完全覆盖（Events/Mentions/GKG 三表 gdelt-py 全有且更强）。
- **结论：出局。** 唯一残值 = 遇到 gdelt-py 文件解析 bug 时作交叉验证参照（`pip install gdelt` 十分钟能跑通 `gd.Search(date, table='events')`）。

---

## 3. get_gdelt_data（gl0bsec）— 不引依赖，抄两个模式 ⭐

- **意外发现：非常活跃**——最新提交 **2026-07-05**（20天前，"json and parquet outputs supported now"），0★ 但是认真维护的个人工具包。
- 定位：Events 表的"采集→过滤→富集→导出"工具链，恰好补我们两个短板：

### 可抄模式 A：YAML 过滤规则 → 降噪预筛
```yaml
filter_rules:
  high_mentions:
    rule: "NumMentions greater than or equal 5"
    enabled: true
```
编译成 pandas `DataFrame.query()` 在采集时逐日应用。
**对我们的意义**：当前 1514 条 pending 大多是单边低置信（conf 0.51-0.53）噪声。在 `collect_gdelt.py` 加一条 `num_mentions >= N` 预筛（N=3~5），可把 pending backlog 压掉大半，且规则外置成 YAML（进 sources 表治理），不写死代码。

### 可抄模式 B：URL 元数据富集 → 复核队列可读化
`extract-urls`（多线程抓 source_url 的 title/author/description）。
**对我们的意义**：review_queue.json 现在只有 actor 码+置信度，人工复核没法看。给待复核事件补抓文章标题（限流+缓存），复核体验质变。

### 附赠情报：FIPS ≠ ISO 陷阱
GDELT 地理字段用 **FIPS 10-4**、actor 字段用 CAMEO/ISO-3，两套码并存（德国 FIPS=GM/ISO=DE，韩国 KS/KR）。我们 canonical 码表是 ISO3 基，**若未来用 ActionGeo_CountryCode 做地理过滤，必须走 FIPS 转换**（gdelt-py 的 Countries lookup 和本库 `iso3_to_fips()` 都有现成表）。

### 不引入依赖的理由
0★ 个人项目、无 PyPI 发布（仅 requirements.txt）、含 .DS_Store/.claude 等杂物 → 供应链不可靠。**抄模式，不抄依赖。**

---

## 4. 结论与行动建议

| 仓库 | 裁决 | 行动 |
|---|---|---|
| gdelt-py | **续任主采集器**（选型再确认 ✅） | 锁版本 0.1.11；记录"无 translingual"口径偏差 |
| gdeltPyR | 淘汰 | 无 |
| get_gdelt_data | 抄模式不引依赖 | 见下 |

**按性价比排序的下一步（均为增量，不动已跑通链路）：**
1. **Mentions 内部佐证**（gdelt-py 现成端点）：verify_events 新增规则——同 global_event_id 的 mentions 来自 ≥K 个不同域名 → cross_checked。诚实边界不变：仍是 GDELT 单源，verified 仍留给人工/跨源。预期把 1% 自动佐证率显著拉高。
2. **NumMentions 预筛**（抄模式 A）：collector 加阈值+YAML 外置，压 pending 噪声。
3. **复核队列富集**（抄模式 B）：给 review_queue 补文章标题。
4. **GKG 叙事层试点**（远期）：themes+tone 喂 L4/L8 叙事建模——这是三库研究里唯一直通"方法论上层"的新通路。

> 与既有待办的关系：本研究不替代「接第二源(ACLED/UCDP)启 cross_source→verified」——Mentions 佐证是单源内更诚实的分层，跨源印证仍是 verified 的唯一自动通路。
