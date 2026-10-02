# WorkRally 六步管线参数全矩阵

> 基于 JS bundle 逆向 + CLI v2.4.1 工具定义

数据流: ① 小说上传 → ② 小说分析 → ③ 改编方向 → ④ 结构化文字剧本 → ⑤ 剧本正文(生图) → ⑥ 文字分镜脚本(生视频) → 成片

## Step 0: 项目创建(前置)
- project_gen_mode=1 (从小说/剧本开始)
- CLI: workrally project create --gen-mode 1

## Step 1: 小说上传
API: AddUserPrompt + upload_file
参数: source(0文本/1文件), user_prompt_list[](prompt_key, prompt)
CLI: 无直接命令, 需 tools call

## Step 2: 小说分析
API: ExtractPromptByImage
参数: extract_type(角色/场景/情节), image(参考图)
产出: 结构化角色/场景/情节数据

## Step 3: 改编方向
Web UI 用户选择, 非API调用
写入 project.agent_sub_mode 或 story.extend_info_json

## Step 4: 结构化文字剧本 <<< 核心
API: BatchAddStory(series_id, story_list[])
story_list[].字段:
  story_description(结构化文字内容)
  story_num(场次编号)
  layer_list[](图层)
  sort_num(排序)
  bg_color(背景色)
  role_data_json(角色绑定)
  extend_info_json(扩展信息, 含animation_prompt)
CLI封装: shot create --series-id <id> --json-list
  image_prompt → story_description + layer[0].prompt
  animation_prompt → extend_info_json

## Step 5: 剧本正文 → 生图
API: GenerateImages / BatchGenerateLayerImage
底层参数: cfg_scale, sampling_steps, seed, scheduler, model_name
CLI: shot generate-image --story-ids <ids>
前置: shot set-model(配置image_model)

## Step 6: 文字分镜脚本 → 生视频
API: BatchGenerateStoryAnimation(series_id)
驱动: 固定mode=9(SUBJECT_TO_VIDEO)
CLI: shot generate-video --story-ids <ids>
前置: shot set-model(配置animation_provider/duration)

## 终点: 成片
API: VideoConcat(video_asset_ids[], audio_asset_ids[])

---
## 各级参数总览

Level 0 - Project: project_name, gen_mode, cover, permission
Level 1 - Series: series_name, story_count
Level 2 - Story: story_description(⭐), story_num, layer_list, role_data_json, extend_info_json
Level 3 - Layer: layer_name, layer_type, prompt, negative_prompt, lora_weight, role_id, model_id, asset_id, transform
Level 4 - Generate: AIDrawingProParams(cfg_scale, sampling_steps, seed, scheduler)
Level 5 - Concat: VideoConcat(video_asset_ids, audio_asset_ids)
