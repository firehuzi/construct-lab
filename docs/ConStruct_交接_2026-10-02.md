# ConStruct Lab · 交接 · 2026-10-02

> **给下一个会话 / 下一个 agent。** 读完这份就知道在哪、有什么、下一步做什么、
> **以及哪些纪律不能丢**（最后那节是本文件最值钱的部分 —— 它们是用整个会话换来的）。

---

## 一、一句话现状

**S1 基础设施已完整（六项全绿）；13 个工具 310 条自证全绿；10 份设计文档在 `vault` 分支。**
**⇒ 缺的仍然是那一样：`paths`（路径空间）要人来填 —— 工具代替不了，也不该代替。**

---

## 二、两个仓（同一个 remote，两个分支）

```
https://github.com/firehuzi/construct-lab.git
  main   ← 引擎与工具（本地：D:\Projects\地缘推演台\construct-engine）
  vault  ← 项目资产（本地：D:\Projects\地缘推演台\ 这个根仓，含 docs/ actors/ ConStruct_Archive/ CWKB_Vault/ content/）
```

**★ 两条历史互不相干，刻意不合并。** 根目录 `.git` 是根仓；`construct-engine` 是独立仓。
**⚠️ 根目录下还住着十几个别的项目，`.gitignore` 用的是白名单**（先忽略一切，再放行该纳入的 5 个目录）。

---

## 三、工具怎么跑（都在 `construct-engine/`）

```bash
# S1 入口：一个双边对 + 年份 → 一份形状正确的 construct-run-v1
python -B s1.py --dyad CN,IN --year 2020 --check
python -B s1.py --dyad IQ,KW --year 1991 --same      # S1.3 同一性验证

# 一个案例的全流程
python -B case_check.py data/cases/filled/XX.json    # 判定 + 读数（含 G4/G6）
python -B case_check.py --all                        # 跑全部（自动跳过空壳、拒绝重复 run_id）
python -B query_gen.py <案例.json>                    # 为核不了的判断出【时间锁定的查询】
python -B archive_source.py <url>                     # 取证并存档（判 tier 与 witness_type）
python -B archive_source.py --audit                   # 依据档案审计（孤儿/缺失/付费墙）

# CWKB 空目录审计
python -B cwkb_audit.py

# 每个工具都有 --selftest
```

**工具清单**（13 个，310 条自证）：`s1` · `case_skeleton` · `case_check` · `archive_source` ·
`query_gen` · `judgment_ledger` · `ucdp_readout` · `exclusion_ledger` · `claims_ledger` ·
`eightdim` · `readout` · `audit_layers` · `audit_holes` · `cwkb_audit` · `build_tool`

---

## 四、10 份设计文档（都在 `docs/`，`vault` 分支）

| 文档 | 它管什么 |
|---|---|
| `ConStruct_重构设计_V1.md` | 总纲：为什么要重构、六段管道 S1–S6、B0–B7 分期 |
| `ConStruct_S1基础设施计划_V1.md` | **S1 的定义与分期（六项）** |
| `ConStruct_S0′重栈触发条件_V1.md` | 三条可核的线：什么时候必须换 PG/Neo4j |
| `ConStruct_路径空间写法指南_V1.md` | **★ 填 `paths` 的人看这份**（含产物形状 ＋ 27 条缺口） |
| `ConStruct_B4_规格_V1.md` | S4 判断登记：三条检查 ＋ G5 ＋ G6 |
| `ConStruct_读数口径登记表_V1.md` | **★ 引用任何读数前先看这份** |
| `ConStruct_L2L8_判据与反例_V1.md` | L2 连续性类型 ／ L8 核心恐惧的判据与反例 |
| `ConStruct_主体类型分析框架_V1.md` | 国家/组织/企业/武装行为体 各自适用哪些维度 |
| `ConStruct_路径空间试写_克里米亚.md` / `_海湾.md` | 两次真跑（G5 与 G6 是从这里出来的） |

---

## 五、下一件事

**给 `data/cases/filled/IN-PK@2026-scenario5.json` 的 4 条路径补 `observable` ＋ `window`。**

**为什么是它**：它来自 `content/scenarios/` 的**成品场景文件**（不是我写的），有**区间概率**，
**但原文没有「什么算它发生了」也没有窗口** —— **补它的过程就是《写法指南》要教的那件事的第一次真实使用。**

**它现在的读数**：
```
G4 概率空间：4 条路径 区间 0.90 ~ 1.15  ✅ 自洽     ← 真的
可判判断总数：0  →  工具会说「这不是做完了，是这份案例还不可判」
```

---

## 六、★ 不能丢的纪律（本文件最要紧的一节）

**这些全是整个会话里被真实错误逼出来的。丢了任何一条，都会重演。**

1. **★ 错的读数与对的读数长得一样。** 本项目最怕的不是报错，是**看起来正常的错读数**。
   已实测到的实例：接口不一致 ⇒ 空报告 ／ 别名错判 ⇒ 死亡数 7（真值 25）／
   `② 依据` 恒等于 0 ／ `③ 待人工 0` 看着像做完了。
2. **★ 自己测自己，测不出「不知道的人会怎么错」。** 310 条自证，**四个盲测者找到的 6 个
   bug 一个都没抓到** —— 因为它们全是我按自己已知的坑写的。
   **⇒ 定期开不知情的 subagent，只给它文档和工具。**
3. **★ 不许编。** 拿不到的东西留空并标 `needs_human`；**`event.text`（F1 原文）到现在
   七个案例全是 `null`** —— 那不是遗漏，是纪律。
4. **★ 一个读数的成因有两种解释且都成立时，⛔ 不许只挑一条写。**
   要写「两条都成立，现在分不清」，并给出能把它们分开的那次测量。
5. **★ 「断言写了但没跑」是最危险的状态。** 每次都实测；自证必须能【反面】亮。
6. **★ 口径不对题是默认状态，不是例外。** 本轮我犯了至少 8 次（变量遮蔽 ／ 拿字节比字符 ／
   归一器与正则不一致 ／ 插入锚没匹配 4 次…）。**跑一下才发现，想是想不出来的。**
7. **★ 声明与产物必须对照。** 「规划写了、目录建了、内容没有」已实测三次
   （SQLite 真相源 ／ CWKB 七个目录 ／ Indexes）。**⇒ 空目录要【声明为空】并可机器查（`cwkb_audit.py`）。**
8. **★ 示例恰好覆盖的实现，会掩盖不在示例里的缺陷。** 别名表那次就是：
   指南示例全用 RU/UA/IQ/KW，**恰好都在表里**。

---

## 七、给新会话的开场白（可以直接用）

> 读 `docs/ConStruct_交接_2026-10-02.md`，然后按它第五节做下一件事。
> 过程中遵守第六节那八条纪律。
