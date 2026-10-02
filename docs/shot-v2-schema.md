# shot-v2 Schema

## 设计原则

- **保留原 shot.json 全部字段** → v2 是增强而非重构，向后兼容
- **取用 WorkRally 四栏结构** → 叙事功能、视觉分层、证据溯源、卖点标签
- **排除污染** → 没有人设/世界观/游戏化/双语模式
- **约束可视化独立成字段** → 不藏在 template 字符串里

---

## 根结构

```json
{
  "meta": { },
  "shots": [ ]
}
```

meta 字段完全沿用原版，不做改动。

---

## ShotV2Item 增强字段

| 字段 | 必填 | 说明 |
|---|---|---|
| narrative_function | 是 | 叙事功能：开场/铺垫/高压/转折/设定说明/高潮/钩子/收敛/结论 |
| sell_tags | 否 | 卖点标签：A:分析深度/B:剧情张力/C:影视感/D:视觉冲击 |
| visual_focus | 是 | 一句话说明观众应看什么 |
| evidence_ref | 否 | 证据溯源，如 causal_chain:0 |
| screen_text | 否 | 屏幕叠加文字 |
| visual_composition | 否 | 视觉构成分层 |
| constraint_visual | 否 | 约束可视化手法 |

---

## visual_composition

```json
{
  "shot_type": "全景 | 中景 | 近景 | 特写 | 大特写",
  "camera_movement": "固定 | 缓慢推入 | 快速推入 | 摇摄 | 画面抖动",
  "animation": "淡入 | 切入 | 拼贴 | 滑入 | 缩放",
  "transition_effect": "胶片闪烁 | 切黑 | 模糊过渡 | 粒子消散",
  "ui_elements": ["说明性文字", "数据指示器", "警告元素", "地图标注"]
}
```

---

## constraint_visual（仅 constraint / branch 类型）

```json
{
  "metaphor": "冰晶覆盖 | 冻结 | 部分重叠圈 | 防御滤镜 | 裂痕蔓延 | 警报爆闪 | 塌缩",
  "entities": [
    {
      "name": "实体名称",
      "state": "frozen | partial | collapse | active",
      "visual_detail": "具体视觉描述"
    }
  ],
  "rules_triggered": ["规则名称"],
  "warning": "警告文字"
}
```

---

## 分支增强项

每个 branch 条目的分支新增：

| 字段 | 说明 |
|---|---|
| probability | 概率标签，如 "高（短期）" |
| visual_focus | 分支级别视觉焦点 |
| warning | 约束警告文字 |

## 数据流通

spec_lock.causal_chain[].step -> shot.evidence_ref[]
spec_lock.branches[].branch_a/b -> shot.branches[].probability
spec_lock.constraint_diagrams[].status -> shot.constraint_visual.entities[].state
spec_lock.constraint_diagrams[].large_set/small_set/intersection -> visual_detail
