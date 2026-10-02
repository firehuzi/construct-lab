# ConStruct Lab · 资产库

> 这个仓库承载的是**项目资产**：47 份主体档案、CWKB 知识库、全部立项与设计文档、内容产出。
> 它的历史与 `construct-engine`（引擎代码）独立 —— 两者都推到同一个 GitHub 仓库的不同分支。

---

## 为什么有这么一个仓库

2026-10 实测（`git ls-files` 逐目录比对）：

| 目录 | 文件数 | 被 git 跟踪（重构前） |
|---|---|---|
| `docs` | 73 | **0** |
| `actors` | 84 | **0** |
| `content` | 143 | **0** |
| `ConStruct_Archive` | 79 | **0** |
| `CWKB_Vault` | 43 | **0** |
| `construct-stack` | 3166 | **0** |
| **合计** | **3588** | **0** |

根目录当时有一个**空的 `.git` 目录**，所以根不是仓库（`git` 直接报
`fatal: not a git repository`）。

**⇒ 项目最强的资产（47 份档案、CWKB、全部文档）只存在于一块硬盘上。**

这一条直接解释了好几个反复出现的病：

* **两份 `<title>` 完全相同的文件，内容差 11 KB** —— 没人知道哪个是新的
* `框架v3.0.html` 出现在完成清单里，而**全工作区零命中**
* `CWKB_v3.0_source.txt` 与 `CWKB v3.0.txt` **字节完全相同**（同一份两个名字）

**没有版本控制，就没有「哪个是哪个」的答案，也无法追溯谁在什么时候改了什么。**

---

## 范围

**入库**：`docs/`、`actors/`、`ConStruct_Archive/`、`CWKB_Vault/`、`content/`
（约 422 个文件，~51 MB）

**不入库**（见 `.gitignore`）：

* **14 个嵌套仓库**（`construct-engine/`、`construct-lab-site/`、`skills/daofu/` 等）
  —— 它们有自己的仓，嵌套进来会变成 submodule 地狱
* **`construct-stack/` 的运行时数据**（Neo4j / Postgres 数据目录，**2.4 GB**）
  以及 `ged261-csv.zip`（38 MB 二进制）—— 数据可以重新采集，不该进库
* `node_modules/`、`__pycache__/`、构建产物

---

## 分支约定

| 分支 | 内容 | 谁在推 |
|---|---|---|
| `main` | 引擎代码（原 `construct-engine`） | `construct-engine/` 这个仓 |
| `vault` | **项目资产**（本仓） | 根目录这个仓 |

**两条历史互不相干**，所以刻意分成两个分支，不合并。
