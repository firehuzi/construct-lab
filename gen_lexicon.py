#!/usr/bin/env python3
"""ConStruct 结构词典 — 批量生成 10 条目"""

import os, json, urllib.request

API_KEY = 'sk-db8545d5f3984ec394867778b636bd98'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'lexicon')
os.makedirs(OUT_DIR, exist_ok=True)

entries = [
    ('冻结局', 'Frozen Settlement',
     'L10六型之保守型。以主权让渡换取外部安全保证和经济稳定形成的长期制度均衡。冻结局是方法不是Identity。典型主体：日本(战后)、韩国、台湾(现状维持)。核心恐惧：身份消失(被降级) > 秩序崩溃。常见误解：冻结局=和平主义(错——日本仍保有强大自卫队)。'),
    ('天下体系型', 'Tianxia Identity',
     'L2 Identity类型。以中国为中心的文明秩序——秩序建立能力(OBC)是核心，不是领土扩张。方法⑦(复兴) → 方法⑧(天下体系)是当前过渡期。Identity兼容行为：秩序输出、制度建立、不接受双中心安排。'),
    ('打而不占', 'Strike-Without-Occupy',
     '中国1962(中印)、1979(中越)战争模式：军事胜利后主动单方面撤军，不要求割让领土。目标不是占领而是恢复秩序基线。与俄罗斯在乌克兰、美国在伊拉克的战争模式形成鲜明对比。'),
    ('互锁式', 'Interlocked Security Dilemma',
     'A的安全措施自动构成B的威胁，双方都被对方的身份需求锁定。典型：伊朗-以色列、印度-巴基斯坦。不是经典囚徒困境——双方都不信任对方会让步，因为让步意味身份丧失。'),
    ('交易式方法⑤', 'Transactional Method 5',
     '以退出威胁获取单边收益的行为模式。利益对齐=关系存在，利益消失=结构切换。当前美国的主要方法。不是Identity——美国Identity是例外论/山巅之城。'),
    ('秩序建立能力', 'Order-Building Capacity',
     '天下体系型Identity的核心衡量标准。一个主体不以暴力为主而以制度、规则、叙事维持秩序的能力。中国(BRI/CIPS/金砖)和美国(布雷顿森林/NATO/美元体系)分别以不同方式展现。'),
    ('ICC', 'Internal Cohesion Coefficient',
     'L5维持机制的核心指标。主体内部子系统之间的耦合程度。高ICC=中央集权、快速动员能力，低ICC=联邦/民主制衡、路径依赖。'),
    ('SUL', 'Strategic Uncertainty Layer',
     '战略不确定性层。不是风险——风险可量化，SUL是已知的未知的总和。每条推演路径标注SUL指数：低=刚性约束推着走，高=依赖不可控变量。'),
    ('方法七→方法八过渡', 'Method 7→8 Transition',
     '中国当前的方法过渡——复兴(⑦)将完成，天下体系(⑧)已启动。Scope只增不减——BRI开始后不会倒退。触发条件：台湾统一进程加速 / CIPS覆盖扩大。'),
    ('民族·族群·文明型', 'Ethnic vs Civilizational Identity',
     'L2 Identity的三个子类型：民族型(德/法/日——共同血缘-文化)、族群型(土/塞/印——身份绑在特定族群上)、文明型(中/俄/美——身份绑在普世使命上)。三种类型核心恐惧完全不同。'),
]

for i, (name, en, body) in enumerate(entries):
    prompt = f"""你是ConStruct Lab结构词典的条目作者。用纯Markdown写一条结构概念条目。按以下模板严格输出：

# {name} ({en})

> 一句话定义。

**所属层**: [从内容推断: L2/L6/L8/L10]
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
        print(f'[{i+1}/10] {name}.md')
    except Exception as e:
        print(f'[{i+1}/10] {name} FAILED: {e}')

print('Done.')
