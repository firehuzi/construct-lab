# WorkRally CLI (workrally)

[WorkRally](https://workrally.qq.com) 是面向 AI Agent 的 AIGC 漫剧视频创作全流程工具集，提供 AI 生图、AI 生视频、资产管理、无限画布等一站式 AIGC 创作能力。

**workrally** 是 WorkRally 平台的官方命令行工具，让你在终端中即可完成项目管理、素材上传、AI 生成等全部操作，也方便在自动化脚本和 CI/CD 流程中集成 WorkRally 的能力。

## 安装

```bash
npm install -g workrally
```

要求 Node.js >= 18.0.0。

## 快速开始

```bash
# 1. 登录（API Key 从 WorkRally 平台获取）
workrally auth login --token <YOUR_API_KEY>

# 2. 查看当前登录用户
workrally whoami

# 3. 列出你的项目
workrally project list

# 4. 上传一张图片
workrally upload ./image.png

# 5. 用 AI 生成图片
workrally generate image-models                    # 查看可用模型
workrally generate image --prompt "一只猫在窗台上" --model <model_id>

# 6. 用 AI 生成视频
workrally generate video-models                    # 查看可用视频模型
workrally generate video --prompt "云海翻涌" --model <provider_id> --poll   # 纯文生视频
```

## 功能一览

| 能力 | 说明 |
|------|------|
| 🔐 **认证管理** | 安全存储 API Key，支持环境变量、交互式输入、自定义配置目录 |
| 📁 **项目管理** | 创建、列出、查看、更新项目 |
| 🎨 **资产库** | 人物 / 道具 / 场景 / 网盘文件夹的树形目录管理 |
| 🖼️ **媒资管理** | 搜索、创建、查看、改名素材 |
| ⬆️ **文件上传** | COS SDK 直传图片 / 视频 / 音频到云端 |
| ⬇️ **素材下载** | 通过素材 ID 或 URL 下载文件，私有读文件自动签名 |
| 🎭 **画布管理** | 无限画布项目的创建、编辑、删除和草稿增量构建 |
| 🎯 **AI 生图** | Kontext 多模型画布生图，支持参考主体图片 |
| 🎬 **AI 生视频** | 3 种驱动模式（纯文 / 单图 / 首尾帧 / 参考主体）生视频，支持音效 |
| 📊 **多格式输出** | JSON / 表格 / 纯文本三种输出模式，方便脚本集成 |
| 🔧 **通用工具** | 列出、查看、透传调用 MCP 服务端任意工具 |
| 🔄 **自动升级** | 后台版本检查 + 一键升级，命令不阻塞 |

## 命令参考

### 认证与配置

```bash
# 登录
workrally auth login --token <YOUR_API_KEY>

# 交互式登录
workrally auth login

# 查看登录状态
workrally auth status

# 登出
workrally auth logout

# 查看当前用户信息
workrally whoami
```

```bash
# 配置管理
workrally config list                  # 列出所有配置
workrally config get output_format     # 查看某项配置
workrally config set output_format table  # 修改配置
workrally config path                  # 查看配置文件路径
```

### 项目管理

```bash
# 列出所有项目
workrally project list

# 按名称搜索
workrally project list --search "我的动画"

# 分页查询
workrally project list --page 1 --page-size 10

# 创建项目
workrally project create "测试项目"

# 查看项目详情
workrally project get <project_id>

# 更新项目
workrally project update <project_id> --name "新名字"
```

### 文件上传

```bash
# 上传图片
workrally upload ./character.png

# 上传视频
workrally upload ./demo.mp4

# 静默模式（仅输出 URL，适合脚本管道）
workrally upload ./image.jpg -o text
```

### AI 生图

```bash
# 查看可用模型
workrally generate image-models

# 文本生图
workrally generate image \
  --prompt "一只橘猫坐在窗台上，窗外是夕阳" \
  --model <model_id> \
  --aspect-ratio 16:9

# 生成并自动等待结果
workrally generate image \
  --prompt "赛博朋克城市街道" \
  --model <model_id> \
  --poll

# 使用参考图片生成
workrally generate image \
  --prompt "第一张图片在花园中散步" \
  --model <model_id> \
  --input-images "https://example.com/ref.jpg"

# 一次生成多张
workrally generate image \
  --prompt "水墨山水画" \
  --model <model_id> \
  --count 4

# 在画布中生成（自动创建占位节点）
workrally generate image \
  --prompt "古风少女弹琴" \
  --model <model_id> \
  --project-id <canvas_id> \
  --name "我的画布_古风少女弹琴" \
  --poll
```

### AI 生视频

```bash
# 查看可用视频模型（必须先调用！）
workrally generate video-models

# 纯文生视频（默认 Text 模式，不传图片）
workrally generate video \
  --prompt "云海翻涌，阳光穿透云层洒向大地" \
  --model <provider_id> \
  --poll

# 图生视频（Text 模式 + 参考图）
workrally generate video \
  --prompt "角色缓缓转头微笑" \
  --model <provider_id> \
  --single-image-url "https://example.com/frame.jpg" \
  --poll

# 首尾帧驱动
workrally generate video \
  --mode FirstLastFrame \
  --prompt "从白天到黄昏的变化" \
  --model <provider_id> \
  --first-frame-url "https://example.com/first.jpg" \
  --last-frame-url "https://example.com/last.jpg"

# 参考主体驱动
workrally generate video \
  --mode SubjectToVideo \
  --prompt "角色在城市街道中奔跑" \
  --model <provider_id> \
  --reference-assets '[{"type":"image","url":"https://example.com/character.jpg"}]'

# 生成音效 + 自定义时长 + 多个
workrally generate video \
  --prompt "海浪拍打沙滩" \
  --model <provider_id> \
  --duration 5 --count 2 --enable-sound --poll

# 在画布中生成（自动创建占位节点）
workrally generate video \
  --prompt "樱花飘落" \
  --model <provider_id> \
  --project-id <canvas_id> \
  --name "我的画布_樱花飘落" \
  --poll

# 查询生成任务状态
workrally generate task <task_id>

# 轮询等待任务完成
workrally generate task <task_id> --poll
```

> 💡 `--mode` 默认 `Text`，可省略。通用选项：`--duration <秒>` `--count 1-4` `--enable-sound` `--name <名称>` `--poll`

### 媒资管理

```bash
# 搜索素材（project-id 必填）
workrally asset search --project-id <project_id>

# 按关键词搜索
workrally asset search --project-id <project_id> --keyword "角色"

# 按类型筛选
workrally asset search --project-id <project_id> --type video

# 创建素材记录（入库）
workrally asset create --url "https://example.com/image.jpg" --project-id <project_id>

# 画布场景入库（需额外指定 channel 和画布 ID）
workrally asset create --url "https://example.com/image.jpg" \
  --project-id <project_id> \
  --channel toolbox_canvas \
  --canvas-project-id <canvas_id>

# 查看素材详情（支持多个 ID）
workrally asset get <asset_id1> <asset_id2>

# 修改素材名称
workrally asset update <asset_id> --name "新名称"
```

### 资产库管理

```bash
# 列出人物角色
workrally material list role_person

# 列出道具
workrally material list role_prop

# 列出场景
workrally material list role_scene

# 列出网盘文件夹（用户自建）
workrally material list root

# 按关键词搜索
workrally material list role_person --keyword "战士"

# 查看角色详情（训练状态、LoRA 版本等）
workrally role get <role_id>

# 查看素材详情（支持多个 ID）
workrally material get <material_id1> <material_id2>

# 批量更新素材（重命名/移动/更新描述）
workrally material update --json-list '[{"material_id":"xxx","material_name":"新名称"}]'
# 或从文件读取
workrally material update --file updates.json

# 添加素材到资产库
workrally material add --file items.json --project-ids <project_id>

# 面包屑路径
workrally material breadcrumb <material_id>
```

### 画布管理

```bash
# 创建画布
workrally canvas create "我的画布"

# 列出画布
workrally canvas list

# 查看画布详情
workrally canvas get <canvas_id>

# 更新画布信息
workrally canvas update <canvas_id> --title "新标题"

# 删除画布（支持多个 ID）
workrally canvas delete <canvas_id1> <canvas_id2>

# 构建草稿 — 增量合并（添加/修改节点，已有节点自动保留）
workrally canvas build-draft <canvas_id> --file nodes.json
workrally canvas build-draft <canvas_id> --nodes '[{"id":"n1","type":"image","position":{"x":0,"y":0},"data":{"asset":{"id":"xxx"}},"style":{"width":400,"height":300}}]'

# 删除指定节点
workrally canvas build-draft <canvas_id> --delete-node-ids "node_id1,node_id2"

# 同时增删改
workrally canvas build-draft <canvas_id> --nodes '[...]' --delete-node-ids "old_id"

# 全量覆盖（清空后重建）
workrally canvas build-draft <canvas_id> --nodes '[...]' --mode overwrite
```

> 💡 `build-draft` 默认增量合并模式，同 ID 覆盖、新 ID 追加、未提及的已有节点保留。
> 支持的节点类型：`image` / `video` / `audio` / `imageGenerator` / `videoGenerator` / `artboard` / `text` / `freehand`。
> 画布支持多人协同编辑，CLI 写入不会覆盖其他用户的并发操作。

### 素材下载

```bash
# 通过素材 ID 下载
workrally download <asset_id>

# 通过 URL 直接下载
workrally download --url <url>

# 指定输出目录和文件名
workrally download <asset_id> --dir ./output --name my-file.mp4

# 静默模式（不显示进度）
workrally download <asset_id> --quiet

# 输出下载文件路径（适合脚本管道）
workrally download <asset_id> -o text
```

> 💡 私有读文件（视频/音频）会自动获取带签名的下载地址，无需手动处理签名。

### URL 工具

```bash
# 解析 WorkRally 页面地址
workrally url parse "https://workrally.qq.com/project/xxx"

# 构建页面地址
workrally url build "资产库"

# 列出所有可用页面路由
workrally url list
```

### 通用工具（高级）

```bash
# 列出 MCP 服务端所有可用工具
workrally tools list

# 以 JSON 格式输出
workrally tools list --json

# 查看某个工具的详细参数定义
workrally tools describe <tool_name>

# 透传调用任意工具（键值对参数）
workrally tools call <tool_name> --arg key1=value1 --arg key2=value2

# 透传调用任意工具（JSON 参数）
workrally tools call <tool_name> --json-args '{"key":"value"}'

# 从文件读取参数
workrally tools call <tool_name> --file params.json
```

> 💡 `tools` 命令用于直接与 MCP 服务端工具交互，适合高级用户和调试场景。CLI 内置的命令（如 `project`、`canvas`）已覆盖常用功能，优先使用内置命令。

### 升级

```bash
# 检查并自动升级到最新版本
workrally upgrade

# 仅检查是否有新版本
workrally upgrade --check
```

> **自动更新提示**: workrally 会在每次运行时后台检查新版本 (每 4 小时最多一次, 不阻塞命令执行)。
> 发现新版时在命令结束后打印提示。设置 `WORKRALLY_NO_UPDATE_CHECK=1` 可禁用。

## 输出格式

所有命令都支持通过 `-o` 参数指定输出格式：

```bash
# JSON（默认，结构化数据，适合程序解析）
workrally project list -o json

# 表格（适合人类阅读）
workrally project list -o table

# 纯文本（适合管道和脚本）
workrally project list -o text
```

设置全局默认输出格式：

```bash
workrally config set output_format table
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WORKRALLY_API_KEY` | API Key（优先于配置文件） | — |
| `WORKRALLY_ENDPOINT` | 服务端点地址 | `https://workrally.qq.com/zenstudio/api/mcp` |
| `WORKRALLY_CONFIG_DIR` | 配置文件目录（非持久化容器建议指向持久卷） | `~/.workrally` |
| `WORKRALLY_NO_UPDATE_CHECK` | 设为 `1` 禁用自动版本检查 | — |

## 配置文件

CLI 配置存储在 `~/.workrally/config.json`（可通过 `WORKRALLY_CONFIG_DIR` 环境变量自定义目录），包括认证信息和个性化设置。

可配置项：`endpoint`（服务端点 URL）、`output_format`（json/table/text）、`color`（是否彩色输出）。

```bash
# 查看配置文件位置
workrally config path

# 列出所有配置项
workrally config list

# 设置默认输出格式
workrally config set output_format table
```

## 脚本集成示例

在自动化脚本中使用 workrally：

```bash
#!/bin/bash
# 确保已设置 API Key
export WORKRALLY_API_KEY="your-api-key"

# 批量生成图片并等待结果
workrally generate image \
  --prompt "一个古风少女在竹林中弹琴" \
  --model "$MODEL_ID" \
  --poll \
  -o json

# 纯文生视频 + 轮询等待
workrally generate video \
  --prompt "星空下的极光缓缓流动" \
  --model "$PROVIDER_ID" \
  --duration 5 \
  --poll \
  -o json

# 上传 → 入媒资库 → 下载签名文件
URL=$(workrally upload ./video.mp4 -o text)
ASSET_ID=$(workrally asset create --url "$URL" --project-id "$PROJECT_ID" -o json | jq -r '.id')
workrally download "$ASSET_ID" --dir ./output
```

## License

本项目为专有软件（Proprietary），未经授权不得修改、反编译或重新分发。
