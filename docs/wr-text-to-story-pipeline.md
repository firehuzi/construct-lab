# WorkRally 文本→分镜管线参数明细

> 基于 JS bundle 逆向 + CLI v2.4.1 实测
> 层级: Project → Series → Story → Layer

---

## L0: Project（项目级）

### 创建参数（project_create）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| project_name | string | ✅ | 项目名称 |
| cover_image_url | string | 可选 | 封面图 URL |
| series_count | int | 可选 | 剧集数量 |
| auto_create_series | bool | 可选 | 自动建剧集 |
| canvas_size | int | 可选 | 0=1K, 1=2K, 2=4K |
| canvas_size_value | string | 可选 | 如"1920:1080" |
| series_sort | int | 可选 | 排序类型 |
| project_type | int | 可选 | 0=默认 |
| project_permission | int | 可选 | 权限类型 |
| naming_rule_id | string | 可选 | 命名规则ID |

**CLI**: workrally project create "推演实验室"

---

## L1: Series（剧集级）

### 创建参数（series_create）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| project_id | string | ✅ | 所属项目ID |
| series_name | string | ✅ | 剧集名称 |
| story_count | int | 可选 | 预计场次数 |
| finish_time | string | 可选 | 完成时间 |

**CLI**: workrally series create --project-id <id> --name "E01-特朗普协议"

---

## L2: Story（场次/分镜级）← 核心层

### 创建参数（shot_manage action=add）

| 参数 | CLI | 必填 | 说明 |
|---|---|---|---|
| series_id | --series-id | ✅ | 所属剧集ID |
| shots[] | --json-list | ✅ | 场次数组 |

**shots[] 内每项字段：**

| 字段 | 必填 | 说明 |
|---|---|---|
| image_prompt | ⭐ 至少填一个 | **关键帧画面描述**（决定生图内容） |
| animation_prompt | ⭐ 至少填一个 | **视频动效描述**（决定运镜/过渡） |

**CLI**: workrally shot create --series-id <id> --json-list '[{"image_prompt":"...","animation_prompt":"..."}]'

### 更新参数（shot_manage action=edit_content）

| 参数 | CLI flag | 说明 |
|---|---|---|
| image_prompt | --image-prompt | 修改静态画面描述 |
| animation_prompt | --animation-prompt | 修改动效描述 |
| story_num | --story-num | 场次编号 |

### 模型配置（shot_manage action=set_model）

| 参数 | CLI flag | 说明 |
|---|---|---|
| story_ids | --story-ids | 不传=全剧集生效 |
| series_id | --series-id | ✅ 必填 |
| image_model | --image-model | 图片模型 en_name |
| animation_provider | --video-provider | provider 数字 |
| animation_model | --animation-model | "mode,provider" |
| animation_duration | --duration | 视频时长（秒） |
| aspect_ratio | --aspect-ratio | 宽高比 |
| enable_sound | --enable-sound | 音画直出 |

### 生图生视频

| 工具 | CLI | 说明 |
|---|---|---|
| shot_generate_image | shot generate-image --story-ids | Kontext 逐场次生图 |
| shot_generate_video | shot generate-video --story-ids | mode=9 主体生视频 |

---

## 模型速查

### 图片（9个）

| en_name | 中文 | 推荐 |
|---|---|---|
| nano-banana-pro | 贝宝pro | ⭐ 主推 2K/4K |
| nano-banana | 贝宝2 | 备用 |
| nano-banana1 | 贝宝1 | 快速 |
| vidu | 维宝 | 高质量 |
| doubao-seedream-3-0-t2i-250415 | 多宝 | 豆包 |
| doubao-pro | 多宝pro | 豆包高质量 |

### 视频（13个，mode=9 固定）

| provider | 名称 | 时长 | 音频 | 推荐 |
|---|---|---|---|---|
| 2200 | 梦宝2.0 | 4-15s | ✅ | ⭐ 主推 |
| 2202 | 梦宝2.0.1080 | 4-15s | ✅ | 高清 |
| 2201 | 梦宝2.0连镜优化 | 4-15s | ✅ | 连镜 |
| 1 | 灵宝O3 | 3-15s | ✅ | 3D写实 |
| 102 | 灵宝O3.4K | 3-15s | ✅ | 超高清 |
| 157 | 万宝2.7 | 5-15s | ❌ | 首尾帧 |

---

## 文本→分镜数据流

`
文本（公众号分析文章）
  │
  │  ConStruct Lab: create-video-script workflow
  │  产出 shot.json（含 image_prompt + animation_prompt）
  │
  ▼
① project_create("推演实验室")
  │
  ▼
② series_create(project_id, "E01-特朗普协议")
  │
  ▼
③ shot_manage(action=add, series_id, shots[])
  │   每项: {image_prompt, animation_prompt}
  │
  ▼
④ shot_manage(action=set_model, series_id,
  │   image_model=nano-banana-pro,
  │   animation_provider=2200, duration=10)
  │
  ▼
⑤ shot_generate_image(story_ids)
  │   → 每场次出关键帧图
  │
  ▼
⑥ [下一层: shot_generate_video → VideoConcat]
`

## 关键发现

1. **Story 是核心单元**——一个 story = 一个分镜段落，至少填 image_prompt 或 nimation_prompt
2. **image_prompt 决定画面**——这就是我们写约束可见化描述的地方
3. **animation_prompt 决定动效**——缓慢平移/推拉/过渡
4. **set-model 统一配置**——可以一次把全剧集的模型/时长/比例设好
5. **Layer 是可选细化**——推演内容一般一个 story = 一个 layer