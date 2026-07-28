#!/usr/bin/env python3
"""ConStruct 结构词典 — 第二批 12 条目"""

import os, json, urllib.request

API_KEY = 'sk-db8545d5f3984ec394867778b636bd98'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'lexicon')
os.makedirs(OUT_DIR, exist_ok=True)

entries = [
    ('无对手的对抗', 'Opponentless Confrontation',
     '俄罗斯报告核心概念。GDELT 040(军事动员/演习)高频 + Actor2=None主导 = 武力不是反应性的，是身份表达。来自Russia ConStruct诊断。'),
    ('主权与安全分离', 'Sovereignty-Security Decoupling',
     '日本战后模式：行政主权完整，但安全外包给美国框架。COW数据支撑——战后独立同盟记录=0。冻结局的核心运作机制。'),
    ('整合式', 'Integration-Type Identity',
     'EU/法/英的构型。通过制度融合维护存在。核心恐惧：一体化倒退。运作机制：利用制度权力约束他者、成员国退出风险、规则输出。'),
    ('强权复兴式', 'Power-Restoration Identity',
     '俄罗斯构型。武力锁定为身份表达。核心恐惧：被降级为非帝国。行为模式：只在绝对力量前让步(中俄边界交易1996/2008)。'),
    ('摆荡式', 'Oscillating Identity',
     '菲律宾/塞尔维亚构型。大国间摇摆——在安全依赖与经济利益间平衡。核心恐惧：被任一方的安全保证者抛弃。'),
    ('撕裂式', 'Torn Identity',
     '土耳其/乌克兰构型。内部Identity冲突——在西方化与本土化/宗教化之间撕裂。核心恐惧：内部矛盾爆发导致政权危机。'),
    ('Ordnung型', 'Ordnung Identity',
     '德国构型。基于规则的秩序维护——制度恐惧崩坏。运作机制：多边机构参与、对秩序挑战者的约束、欧洲中心角色。'),
    ('外包式安全', 'Outsourced Security',
     '日本冻结局的子机制。安全完全依赖美国框架，代价是外交行为密度极低。GDELT 48h仅10起事件 vs 美国348——结构性收缩的证据。'),
    ('G2共治不可能', 'G2 Co-Leadership Impossibility',
     '中国诊断核心判断。天下体系=单中心秩序。接受双中心安排=Identity不允许。不是策略选择，是结构性不可能。'),
    ('媒体距离', 'Media Distance',
     'GDELT覆盖密度的理论基础。某主体在西方英文媒体中的能见度 ≠ 地缘政治重要性。USA密度10.13 vs PRK 0.07——145倍差距是西方媒体框架的结构性特征。'),
    ('行为反证', 'Behavioral Falsification',
     'ConStruct反馈环的核心机制。主体行为偏离结构假设预测 → 检测矛盾 → 降低置信度 → 累积超阈值 → 人工复核 → 修正假设。结构诊断可被证伪。'),
    ('路径枚举·逻辑排除', 'Path Enumeration and Logic Elimination',
     '推演方法论——不做概率预测，枚举结构上可能的路径，排除逻辑上不可能的路径。每条推演带结构性前提标注。'),
]

for i, (name, en, body) in enumerate(entries):
    prompt = f"""你是ConStruct Lab结构词典的条目作者。用纯Markdown写一条结构概念条目。按以下模板严格输出，300-500字：

# {name} ({en})

> 一句话定义。

**所属层**: [从内容推断: L2/L4/L5/L6/L7/L8/L10]
**适用构型**: [哪些构型用到]
**运作机制**:
- [核心机制1]
- [核心机制2]
- [核心机制3]

**典型主体**:
- [国家名]: [表现]

**常见误解**:
- 误解1: "[误解]" — 实际情况: [纠正]
- 误解2: "[误解]" — 实际情况: [纠正]

**相关条目**: [交叉引用的其他词典条目]

素材：{body}"""

    data = json.dumps({
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': '你是ConStruct Lab结构词典条目作者。冷静精准，无废话。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.3, 'max_tokens': 1500,
    }).encode()

    req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions', data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        content = resp['choices'][0]['message']['content']
        path = os.path.join(OUT_DIR, f'{name}.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[{i+1}/12] {name}.md')
    except Exception as e:
        print(f'[{i+1}/12] {name} FAILED: {e}')

print('Done.')
