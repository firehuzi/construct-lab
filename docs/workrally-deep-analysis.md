# WorkRally 深度研究报告

> 来源: npm v2.4.1 CLI分析 + Web UI JS bundle (20MB) 反向工程

---

## 1. WorkRally 是什么

**WorkRally = 腾讯视频的AI影视拍摄平台（漫剧/短剧方向）**

不是\"文字生成视频\"这么简单。它是一个**全流程影视制作平台**，覆盖：
- 项目管理（project）
- 角色库（人物/LoRA/三视图）
- 素材库（图片/视频/音频/3D）
- 无限画布编辑器（类似 Figma 的节点式编辑）
- AI 生图 + AI 生视频 + TTS + 音乐生成
- 后期制作（视频裁切/变速/帧率转换/冻帧延长）
- 成本控制面板
- MCP 接口（Agent 可调用）

## 2. Web UI 核心路线（从JS逆向）

### 核心工作区 (/film/)
- /film/index — 首页
- /film/project — 项目列表
- /film/project/:projectId/index — 项目首页
- /film/project/:projectId/work/* — **工作区（核心编辑）**
- /film/project/:projectId/project-manage — 项目管理
- /film/project/:projectId/script/:scriptId — 脚本详情
- /film/project/:projectId/resource-library — 资源库
- /film/project/:projectId/settings — 项目设置
- /film/project/:projectId/cost-dashboard — 成本面板

### 独立编辑工具
- /film/character-edit/:id — **角色工作室**（三视图/LoRA）
- /film/costume-edit/:id — 服装编辑
- /film/dialogue-edit/:id — 对白编辑
- /film/lip-edit/:id — **口型编辑**（AI对口型）
- /film/music-gen/:id — **音乐生成**
- /film/tts/editor/:id — **TTS编辑器**
- /film/video-edit/:id — 视频编辑
- /film/video-fps/:id — 帧率调整
- /film/video-hires/:id — 视频高清化
- /film/post-production — **后期制作**

### 工具箱（节点式工作流）
- /film/toolbox — 工具箱入口
- /film/toolbox/canvas-manager — 画布管理
- /film/toolbox/workflow/:id — **工作流编排**
- /film/toolbox/workflow/:id/:taskId — 工作流任务详情

## 3. CLI 能做什么（对我们有用的）

| 能力 | 命令 | 价值 |
|---|---|---|
| 项目管理 | workrally project create/list/get | 每集视频=1个项目 |
| 素材上传 | workrally upload | 地图/图表/推演图素材 |
| 素材管理 | workrally asset create/search | 管理素材库 |
| AI 生图 | workrally generate image --poll | Kontext控图，替代MJ |
| AI 生视频 | workrally generate video --poll | 3种驱动模式 |
| 画布编排 | workrally canvas build-draft | 推演路径可视化 |
| MCP工具 | workrally tools call | 高级自定义调用 |

## 4. 对我们的价值判断

### 高价值能力
1. **Kontext 生图** — 参考主体控图，可以生成推演角色、约束示意图等
2. **AI 生视频（首尾帧驱动）** — 可以生成推演路径动画
3. **TTS** — 火山豆包 TTS，旁白生成
4. **画布管理** — 推演路径的可视化编排

### 中价值能力
5. **项目管理** — 多集推演视频的结构化管理
6. **素材库** — 地图/图表等重复素材的复用

### 低价值
7. **漫剧角色**（人设/三视图/LoRA）— 我们的内容是实景+地图+约束图，没有\"漫剧角色\"
8. **口型/对口型** — 不需要

## 5. 下一步：接入路线

`
1. 安装 workrally CLI → npm install -g workrally
2. 申请 API Key → workrally.qq.com/open-api
3. 创建一个推演视频项目 → workrally project create \"推演实验室-E01\"
4. 上传品牌素材 → workrally upload palette/fonts
5. 用 Kontext 生图 → generate image 生成约束图
6. 用首尾帧生视频 → generate video 生成推演片段
7. 用 canvas 编排推演路径
