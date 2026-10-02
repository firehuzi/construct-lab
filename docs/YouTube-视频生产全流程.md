# YouTube 视频生产全流程 — 从素材到成片

> 以 ConStruct Lab 地缘政治内容创作为例，打通"选题→素材→脚本→视觉→录音→剪辑→发布"的完整管线。
> 结合现有工具链：CWKB Vault + ConStruct Engine + dynamic-archify + AI 工具。

---

## 一、整体管线全景

```
阶段 0: 选题规划         → 选题库 + 竞争分析
阶段 1: 素材搜集整理      → CWKB + 新闻图片 + 新闻文本 + 视频素材 ← 本期重点
阶段 2: 脚本撰写          → 叙事弧 + 逐段脚本 + 时间轴
阶段 3: 视觉资产准备      → B-roll / 动画 / 封面 / 配图
阶段 4: 录音              → 旁白录制 + AI TTS
阶段 5: 剪辑合成          → 时间线编排 + 动效 + 配乐
阶段 6: 导出 + 发布       → 格式优化 + 标题/描述/Tags + 缩略图
```

### 与 ConStruct Lab Skill 的映射

```
ConStruct Lab 管线               YouTube 生产管线
────────────────────────────────────────────────────
routing.md                       阶段 0: 选题
阶段 1: 证据收集                  阶段 1: 素材搜集整理  ← create-video-script 第1步
阶段 2: 分析框架                  阶段 2: 脚本撰写      ← create-video-script 第2-3步
阶段 3: 输出设计                  阶段 3: 视觉资产计划  ← create-video-script 第4步
阶段 4: 生成生产                  阶段 4-5: 录音+剪辑
阶段 5: 质量关卡                  阶段 6: 导出+发布审核
```

---

## 二、阶段 0 — 选题规划

### 2.1 选题来源

```
用户已有：
  content/analysis/  → 30+ 篇深度分析，每条可做一期视频
  content/scenarios/ → 10 个推演场景，每条可做深度解读
  CWKB Vault         → 43 个概念/主体档案，可做系列

推荐系列化策略（从已有脚本规划看）：
  系列 A: 「地缘政治诊断」    单集深度分析
  系列 B: 「小国生存术」      系列化国家研究
  系列 C: 「推演实验室」      情景模拟 + 多路径推演
```

### 2.2 竞争分析清单

```
选定选题后，在 YouTube 上搜索同类内容，记录：
□ 头部视频标题结构（Hook 怎么写的）
□ 封面风格（文字/人物/情绪）
□ 评论区高频问题（用作脚本中的预判回答）
□ 观众留存率可能的低谷段（用来调整结构）
```

---

## 三、阶段 1 — 素材搜集整理 ← 重中之重

### 3.1 素材类型总览

```
一条 10-15 分钟的地缘政治视频，需要的素材：

图片类（8-15 张）       新闻图片、地图截图、人物肖像、数据截图
视频类（5-10 段）       新闻片段、空镜/B-roll、动画片段
文本类                  新闻稿、分析报告、引文、数据表格
音频类                  旁白录音、背景音乐、音效
动画类                  dynamic-archify 生成的流程图/架构图动画

素材获取渠道分三类：
  A. 自有资产 — CWKB Vault, content/analysis/, ConStruct Engine 输出
  B. 开放网络 — 新闻网站, 图片库, 视频素材站, 数据公开源
  C. AI 生成 — dynamic-archify 动画, AI 配图, AI TTS
```

---

### 3.2 自有资产优先（已有，可直接取用）

#### A) CWKB Vault — 核心事实与数据

```powershell
# 按主题查知识库
python skills/construct-lab/scripts/sync_cwkb.py search "中东"
python skills/construct-lab/scripts/sync_cwkb.py search "以色列"

# 按层级筛选
python skills/construct-lab/scripts/sync_cwkb.py layer L6   # 主体档案（以色列、伊朗等）
python skills/construct-lab/scripts/sync_cwkb.py layer L0   # 概念词典

# 生成标准证据表
python skills/construct-lab/scripts/sync_cwkb.py evidence "制裁"
```

#### B) content/analysis/ — 已成稿的分析

```powershell
# 选题相关已有分析
Get-ChildItem content/analysis/ | Select-String "以色列" -SimpleMatch | Select-Object Filename

# 提取已有分析素材
$topic = "特朗普的中东大交易"
Get-ChildItem content/analysis/ -Filter "*$topic*" | Get-Content -Encoding UTF8
```

#### C) content/scenarios/ — 推演场景素材

```powershell
# 推演场景中的路径描述，可直接转化为视频中的"推演段"
Get-ChildItem content/scenarios/ -Filter "*中东*" | Get-Content -Encoding UTF8
```

---

### 3.3 新闻图片搜索获取 ← 新增详细流程

#### 优先级策略

```
图片搜索顺序（从快到慢，从免费到付费）：

1. 新闻头条图（最快） → 新闻网站主视觉图
2. Getty/AP/Reuters 新闻图片 → 新闻图片社
3. 政府/机构发布图 → 白宫/国务院/UN Flickr
4. 维基百科 → 开放共享图片
5. AI 生成配图 → Midjourney/DALL-E
6. 自制（Canva/截图+标注） → 最后手段
```

#### 图片来源清单（地缘政治类优先）

| 来源 | 类型 | 搜索策略 | 版权 | 适合场景 |
|---|---|---|---|---|
| **Reuters Graphics** | 新闻配图/数据图 | `reuters.com/graphics/` | 新闻引用 | 事件实时画面、数据视觉 |
| **AP Images** | 新闻图片社 | `apimages.com` | 新闻引用 | 新闻现场、人物特写 |
| **Getty Images** | 新闻图片社 | `gettyimages.com` 搜"Israel Gaza" | 嵌入码免费 | 高品质新闻画面 |
| **UN Photo** | 官方图片 | `unmultimedia.org` | 署名免费 | 联合国相关议题 |
| **White House Flickr** | 官方图片 | `flickr.com/whitehouse` | 官方公开 | 美国外交/政策 |
| **EU/European Commission** | 官方图片 | `ec.europa.eu` | 官方公开 | 欧盟相关 |
| **Wikimedia Commons** | 开放图片 | `commons.wikimedia.org` | CC BY-SA | 历史画面、地图、人物 |
| **Wikipedia 条目** | 即时可用 | 找到对应条目，取 infobox 图 | 各条目不同 | 快速获取基础画面 |
| **Pexels/Pixabay** | 免费图库 | "middle east city" 等泛搜 | CC0 免费 | B-roll 空镜 |

#### 搜索关键词策略

```
对同一个事件，用多组角度关键词获得不同构图：

角度 1: 事件焦点（who what where）
  "Israel Gaza 2025"
  "Netanyahu press conference"
  "Gaza airstrike aftermath"

角度 2: 人物/特写
  "Biden + Netanyahu handshake"
  "Trump Middle East envoy"
  "Iran foreign minister"

角度 3: 地图/地理
  "Middle East map political"
  "Israel Gaza border map"
  "Iran missile range map"

角度 4: 数据/视觉
  "Middle East oil fields"
  "military spending Middle East chart"
  "refugee camp Gaza"

角度 5: 历史对照
  "Oslo Accords signing 1993"
  "Camp David 1978"
  "Abraham Accords 2020"
```

#### 图片下载与命名规范

```
项目文件夹结构：

project/video-特朗普中东大交易/
├── sources/                    ← 文本类素材
│   ├── evidence-table.md
│   ├── news-articles/          ← 新闻稿原文
│   └── analysis-notes.md
├── images/                     ← 图片素材
│   ├── 01-cover-concept.jpg      封面构思
│   ├── 02-netanyahu-speech.jpg   事件新闻图
│   ├── 03-map-middle-east.png    地图
│   ├── 04-oil-prices-chart.png   数据图
│   ├── 05-trump-deal-signing.jpg 特写
│   ├── 06-gaza-aftermath.jpg     冲突画面
│   ├── 07-historical-comparison  历史对照图集/
│   ├── 08-screenshots/           截图集合
│   └── credits.md                图片来源清单（必建！）
├── video/                      ← 视频素材
│   ├── b-roll/                   空镜/过渡镜头
│   ├── news-clips/               新闻片段
│   └── animations/               dynamic-archify 输出
├── audio/
├── script-v1.md
└── thumbnail-concept.jpg
```

#### 图片来源记录（credits.md，每次必建）

```markdown
# 图片来源 / Credits

## 使用图片清单
| 文件 | 来源 | URL | 版权条件 | 修改 |
|---|---|---|---|---|
| 02-netanyahu-speech.jpg | Getty Images | url | 嵌入许可 | 裁切 |
| 03-map-middle-east.png | Wikimedia Commons | url | CC BY-SA 4.0 | 标注修改 |
| 05-trump-deal-signing.jpg | AP Images | url | 新闻引用 | 无 |
| 06-gaza-aftermath.jpg | Reuters | url | 新闻引用 | 调色 |

## 未使用但参考过的图
| 来源 | 原因 |
|---|---|
| ... | 构图不合适/版权不清晰 |
```

---

### 3.4 新闻文字素材获取 ← 新增详细流程

#### 新闻源分级

```
一级源（事实锚点）：
  Reuters, AP, AFP                       → 事件确认
  UN/ICJ/IMF/WB 官方声明/报告            → 数据确认
  各国政府/外交部/大使馆官方声明         → 立场确认

二级源（分析补充）：
  Foreign Affairs, Foreign Policy        → 深度分析
  Chatham House, CFR, Carnegie, RAND     → 智库报告
  CSIS, IISS, SIPRI                      → 安全/军事数据
  The Economist, FT, WSJ, NYT            → 综合媒体

三级源（参考/快速更新）：
  Al Jazeera, BBC, CNN, Guardian         → 新闻快讯
  Twitter/X 当事方账号/记者一手信息       → 即时讯息（需交叉验证）
  Telegram 频道                           → 战况/冲突更新（需高度验证）

知识库补充：
  CWKB Vault                             → 已验证的长期数据
  content/analysis/                       → 已有分析框架
```

#### 搜索获取流程

```
Step 1: 事件确认
  "Reuters Middle East [topic]"
  "AP News [topic]"
  → 确认核心事实：谁、何时、何地、发生了什么

Step 2: 数据提取
  IMF/World Bank 数据查询
  SIPRI 军事支出数据
  → 提取 CSV/表格数据，记录来源URL和访问日期

Step 3: 深度背景
  Chatham House / CFR 分析文章
  Foreign Affairs 评论
  → 提取分析角度、引文金句

Step 4: 引文收集
  搜索 '"[person]" [topic] speech' / '"[person]" statement'
  联合国大会发言转录
  新闻发布会记录
  → 记录原话，标注来源和日期（不要二次转述的版本）

Step 5: 最近更新
  搜索 "[topic] 2025 latest" / "[topic] today"
  查看当地媒体（Al Jazeera / 新华社 / 俄罗斯卫星社等）
  → 补齐时效性信息，与 CWKB 已有数据做交叉对比

Step 6: 信息缺口标记
  [GAP：某事的具体数据无法在一级源找到]
  [冲突：Reuters 与 俄罗斯卫星社 对同一事件的描述不一致]
```

#### 新闻文章提取方法

```
方法 A：直接复制 + 来源标注（最常用）
  1. 打开新闻页面
  2. 选中正文 → 复制
  3. 粘贴到 sources/news-articles/ 下
  4. 文件头标注：URL / 发布日期 / 作者 / 媒体

方法 B：PDF 存档（适合研究报告）
  浏览器打印 → 保存为 PDF
  存到 sources/reports/

方法 C：转录（适合视频/音频新闻）
  YouTube 自动字幕 → 复制字幕文本
  或手动听抄关键段落
```

---

### 3.5 视频素材搜索获取 ← 新增详细流程

#### 视频素材分类

```
| 类型 | 用途 | 获取难度 | 推荐来源 |
|---|---|---|---|
| 新闻片段 | 事件现场/人物发言 | 中 | YouTube 新闻频道 / Twitter 视频 |
| B-roll 空镜 | 城市/地标/自然过渡 | 低 | Pexels / Pixabay / Pond5 免费 |
| 动画 | 流程图/推演可视化 | 低（已有工具） | dynamic-archify 生成 GIF/WebM |
| 地图动画 | 区域/边境/势力变化 | 中 | Google Earth Studio / MapBox |
| 屏幕录制 | 数据操作/网站展示 | 低 | OBS / Windows Game Bar |
| AI 视频 | 概念性动画画面 | 中 | Runway / Pika / Sora |
```

#### B-roll / 空镜来源

```yaml
Pexels Video:
  URL: pexels.com
  搜索: "middle east city" "Jerusalem" "Tel Aviv" "desert landscape"
  版权: 免费（Pexels license）
  适合: 过渡空镜、城市环境

Pixabay Video:
  URL: pixabay.com
  搜索: "flag" "military parade" "diplomatic meeting"
  版权: 免费（Pixabay license）
  适合: 旗/检阅/会议中性画面

Pond5:
  URL: pond5.com
  搜索: 同上，过滤器选 Free
  版权: 部分免费
  适合: 高品质新闻存档画面

Internet Archive:
  URL: archive.org/details/news
  搜索: 历史新闻广播
  版权: 公共领域
  适合: 历史新闻片段（1960s-2000s）
```

#### 新闻片段获取

```
方案 A：YouTube 新闻频道（首选）
  YouTube → 搜 "Reuters [topic]" / "AP [topic]" / "BBC News [topic]"
  → 下载视频片段（使用 yt-dlp 或截图录屏）
  → 截取关键 5-30 秒
  → 标注来源：媒体名 + 播出日期 + URL

方案 B：Twitter/X 视频
  事件现场往往首先出现在 Twitter
  → 打开推文 → 下载视频（社交媒体解析工具）
  → 标注：发布者 + 时间 + 是否已验证

方案 C：直播存档
  YouTube 直播回放 / Twitch 新闻直播
  → 定位关键时间戳
  → 录音（OBS 或录屏）
  → 截取片段

下载工具：
  yt-dlp --format bestvideo+bestaudio "URL"    # 最高质量下载
  OBS Studio                                     # 实时录制
  浏览器开发者工具 → Network → Media            # 直接取源视频
```

#### 新闻片段使用规范

```
□ 每个新闻片段不超过 30 秒（地缘政治视频中，新闻画面是辅助，不是主体）
□ 标注来源：角落标注 "Reuters / AP / BBC" 标识
□ 保留原始画质（不要过度压缩）
□ 避免使用模糊/低像素/抖动画面（损伤专业感）
□ 穿插 B-roll 时，注意色调一致性（全部调成统一的色温/对比度）
```

---

### 3.6 素材整理规范

#### 分集文件夹结构

```
video-{编号}-{简短主题}/
├── sources/                      文本素材
│   ├── evidence-table.md          CWKB 证据表 ← sync_cwkb.py 输出
│   ├── analysis-notes.md          从已有分析提取的核心论点
│   ├── news-articles/             新闻稿原文/PDF
│   │   ├── 2025-01-15-reuters-deal-announcement.txt
│   │   ├── 2025-01-20-ap-israel-response.txt
│   │   └── 2025-02-01-foreign-affairs-analysis.txt
│   └── references.md              全部引用来源汇总
├── images/                       图片素材
│   ├── 00-credits.md              图片来源清单（必建）
│   ├── 01-{描述}.jpg              序号=在视频中的出现顺序
│   ├── 02-{描述}.png
│   └── screenshots/               截图集合
├── video/                        视频素材
│   ├── 00-credits.md              视频来源清单
│   ├── b-roll/                    空镜
│   │   ├── 01-jerusalem-skyline.mp4
│   │   └── 02-gaza-street.mp4
│   ├── news-clips/                新闻片段
│   │   ├── 01-netanyahu-speech-15s.mp4
│   │   └── 02-deal-signing-10s.mp4
│   └── animations/                dynamic-archify 动画输出
│       ├── scenario-flow.html
│       └── scenario-flow.gif
├── audio/
│   ├── narration-final.mp3        最终旁白
│   └── music/                     背景音乐
├── script-v1.md                   脚本版本
├── script-v2.md                   修改版
└── thumbnail-concept.jpg          封面构思
```

#### 素材饱和检查清单（进入脚本前必须过）

```
□ 至少有 1 张本事件的核心新闻图片（Getty/AP/Reuters 级别）
□ 每个关键人物至少有 1 张可用肖像/特写
□ 涉及地域至少有 1 张地图（静态或动态）
□ 每一条核心数据至少有 1 个来源交叉验证（CWKB + 一级新闻源）
□ 分析中使用的引文已找到原始出处（非二次转述）
□ 脚本中的每段旁白至少对应 1 个画面素材
□ 需要推演动画的段落已标记，准备调用 dynamic-archify
□ 所有图片/视频来源已记录到 credits.md
□ 版权风险高的素材已标记备选方案
□ 所有文件已按序号命名，可在剪辑软件中按文件名排序快速拖入
```

---

### 3.7 版权与引用（地缘政治视频特别重要）

#### 不同素材的版权处理

```
| 素材类型 | 标准做法 | 注意事项 |
|---|---|---|
| 新闻图片（Getty/AP/Reuters） | 引用标注 + 画面角标 | 不要剪裁掉水印；部分需付费 |
| 政府/UN 官方图片 | 署名来源 | 通常不需要额外许可 |
| Wikimedia Commons CC BY | 署名作者 + 链接 | 有些需要相同方式共享 |
| 新闻视频片段 | 引用标注 + 来源角标 | 合理使用原则（短片段+评论性质） |
| AI 生成图像/视频 | 标注"AI Generated" | 部分平台要求显式标注 |
| 媒体引文/数据 | 来源链接 | 注明日期和访问时间 |

安全原则：
  1. 能用一级新闻源，不用二级媒体
  2. 能用官方发布，不用未核实来源
  3. 所有素材标注来源，不存侥幸
  4. 有版权不确定的，换免费替代方案
```

---

### 3.8 从选题到素材 Ready 的执行清单

```
Step 1: 从 content/analysis/ 和 content/scenarios/ 确定选题方向
Step 2: CWKB 查询 → sync_cwkb.py 生成证据表
Step 3: 新闻搜索（按 3.3 图片 + 3.4 文字 + 3.5 视频 的顺序）
  □ 一级新闻源确认事实
  □ 图片下载 + 命名 + credits.md 记录
  □ 新闻文章提取 + 来源标注
  □ 视频片段下载 + 裁剪
  □ B-roll 空镜补充
Step 4: 素材归类到文件夹结构
Step 5: 运行素材饱和检查清单
Step 6: ✅ 素材 Ready → 进入脚本阶段
```

---

## 四、阶段 2 — 脚本撰写

### 4.1 地缘政治视频的标准叙事弧

```
Hook（0-30 秒）
  "XX 事件发生了，但你以为的原因可能全是错的。"
  → 用反差/悬念/硬数据打断预期

Context（30 秒 - 2 分钟）
  背景铺陈：谁、什么、何时、为什么重要
  → 建立认知框架

Core Analysis（2-15 分钟）
  三段式核心分析：
    Layer 1: 表面逻辑（大多数人看到的部分）
    Layer 2: 底层结构（ConStruct 分析框架揭示的部分）
    Layer 3: 推演与含义（如果 X 继续，下一步会怎样）

Shift / Counter-argument（可选）
  打破自证：另一种解释是什么？
  让分析更有说服力的关键。

Takeaway / SO WHAT（最后 30-60 秒）
  一句话总结 + 可传播的金句 + CTA
```

### 4.2 脚本格式（参考已有脚本）

```
## [段落标题]
时间轴：00:00 - 01:30
画面：[视觉描述] ← 每段必须有画面参考
画面素材：[引用 images/ 或 video/ 中的文件]
旁白：[完整的旁白文本] ← 可直接用于录音
```

### 4.3 地缘政治视频的特殊约束

```
1. 事实准确性最高优先级
   → 每个数字必须有来源（CWKB 引用号或新闻原文）
   → 不确定信息明确标注："这是我们基于现有数据的推演"

2. 多面性呈现
   → 至少提及一个反方论证或替代解释
   → 不要做成"单声道宣教"

3. 推演 vs 预测的边界要清晰
   → 说"可能的路径"而不是"将会发生"
   → 标注置信度

4. 视觉节奏
   → 每 20-30 秒换一次画面
   → 地缘政治视频的视觉节奏模板：
      地图 → 新闻画面 → 引文卡 → 数据图 → 动画 → 地图 → ...
```

---

## 五、阶段 3 — 视觉资产准备

### 5.1 视觉类型选择

| 视觉类型 | 适合内容 | 制作工具 |
|---|---|---|
| 地图标注 | 区域/边界/战略位置 | 截图+标注 / Google Earth |
| 数据图表 | 经济/军事/人口数据 | dynamic-archify / Canva |
| 流程图/架构图 | 推演路径/行为体关系 | **dynamic-archify workflow** |
| 时间线动画 | 历史事件序列 | dynamic-archify sequence |
| 引文卡 | 关键数据/金句引用 | Canva / Photoshop |
| AI 配图 | 概念性画面/封面 | Midjourney / DALL-E |
| 实景/B-roll | 城市/地标/会议 | 阶段 1 已准备的素材 |
| 新闻画面 | 事件现场 | 阶段 1 已准备的新闻片段 |

### 5.2 dynamic-archify 集成

```
脚本中有推演路径分析
  → python construct_to_archify.py workflow script.md
  → 输出：推演路径流程图（HTML 动画）
  → 导出为 GIF/WebM → 作为视频素材

脚本中有行为体关系分析
  → python construct_to_archify.py architecture script.md
  → 输出：行为体关系架构图
  → 导出为 PNG → 作为画面
```

### 5.3 封面设计

```
YouTube 封面公式：冲击性画面 + 核心主张（3-6字） + 悬念缺口

示例（适配已有分析稿）：
  特朗普的中东大交易 → [交易签字画面] + "3000亿买和平?"
  新加坡的裂痕       → [新加坡天际线] + "中介的黄昏"
  塞尔维亚生存术     → [巴尔干地图] + "摆荡式生存"

尺寸：1280×720px，移动端缩略图文字须可辨识
```

---

## 六、阶段 4-6 — 录音 · 剪辑 · 发布（简洁版）

### 录音
```
□ 真人录制或 AI TTS（ElevenLabs / Edge TTS）
□ 150-180 字/分钟
□ 专有名词标注读音
```

### 剪辑（推荐剪映或 Davinci Resolve）
```
□ Hook 快切（0-30s）
□ 每 20-30s 换一次画面
□ 阶段 1 的素材直接按文件名排序拖入
□ 自动字幕 + 校对
□ 配乐：低音量贯穿 + 关键段抬高
```

### 导出与发布
```
格式: 3840×2160 / H.264 / 45 Mbps 或 1920×1080 / 15 Mbps
音频: AAC 320kbps / 48kHz

发布清单:
□ 标题: 前 30 字符含核心关键词
□ 描述: 核心论点 + 时间戳 + 来源链接
□ Tags: 核心 + 长尾 + 系列
□ 缩略图: 1280×720 JPG
□ 多平台: YouTube + B站 + Substack(文字版) + Twitter(预告)
```
