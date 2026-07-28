#!/usr/bin/env python3
"""生成 47 主体的推演层结构验证项 → 写入 feedback_rules.json"""

import sys, os, json

sys.path.insert(0, r'D:\Projects\地缘推演台\construct-stack\scripts')
import canonical_actors as CA

RULES_FILE = r'D:\Projects\地缘推演台\construct-engine\feedback_rules.json'

# 构型模板 → 验证项
VERIFICATION_TEMPLATES = {
    '天下型': {
        'identity': '天下体系型',
        'method_stage': '复兴⑦ → 天下体系⑧',
        'confidence': 0.85,
        'items': [
            ('持续秩序输出', 'BRI/命运共同体/全球治理持续扩展，scope只增不减',
             'actor CHN + action 010-060 + tone trend'),
            ('GDP超US不减速', '方法⑦完成→转入方法⑧，经济方向事件tone不降',
             'CHN actor + 经济关键词 + tone'),
            ('全球治理参与加速', '外交/合作事件 count 不减',
             'CHN + diplom/cooper events count trend'),
            ('CIPS/金砖制度化推进', '天下体系基础设施建成',
             'structural FN domain events count trend'),
            ('US承认不满足', '障碍他者承认≠天下体系完成，不减全局tone',
             'CHN-USA pair tone after diplomacy events'),
            ('不接受双中心安排', '天下体系=单中心秩序',
             'CHN 对国际制度框架的表述中拒绝双领导角色 (需人工判定)'),
        ]
    },
    '冻结局': {
        'identity': '冻结现状型',
        'method_stage': '维持现有秩序结构，恐惧身份丧失',
        'confidence': 0.80,
        'items': [
            ('现状维持信号', 'GDELT 信号不出现激进方向切换',
             'actor tone 在 [-1,1] 区间，无连续5日暴跌'),
            ('对主要他者的反应模式一致', '对关键对手的反应强度不偏离历史均值',
             'actor pair tone 30d vs 90d delta < 1.5'),
            ('不触发主动扩张', 'action 100+ (demand/threaten/force) 事件数不显著上升',
             'actor action>=100 events count trend'),
        ]
    },
    '强权复兴式': {
        'identity': '强权复兴式',
        'method_stage': '武力恢复轨道 — 安全缓冲是Identity需求',
        'confidence': 0.82,
        'items': [
            ('安全缓冲维持', '在乌克兰/周边地区的军事事件密度不下降',
             'RUS actor + action>=150 events count'),
            ('不回应西方框架', '对西方谈判框架的接受不等于退出安全缓冲',
             'RUS + diplom events tone check: 外交接触不伴随全局tone上升'),
            ('同盟网络加固', '与中国/伊朗/朝鲜的同盟关系 markers 持续',
             'RUS pair CN/IRN/KP alliance signals'),
            ('国内叙事控制', 'SOCIAL structural事件不出现政权动摇信号',
             'RUS + SOCIAL domain events'),
        ]
    },
    '整合式': {
        'identity': '整合式',
        'method_stage': '制度融合驱动 — 通过一体化维护存在',
        'confidence': 0.80,
        'items': [
            ('整合深度不倒退', '一体化相关事件方向不反',
             'actor + 合作(030-060) events trend'),
            ('对他者的规则约束', '利用制度权力约束对手的能力',
             'actor pair tone in institutional disputes'),
            ('内部裂变信号', '成员国/地区退出风险',
             'actor + SOCIAL domain events'),
        ]
    },
    '自主型': {
        'identity': '自主型',
        'method_stage': '多边对齐策略 — 在体系中追求最大自主',
        'confidence': 0.78,
        'items': [
            ('多边平衡', '与各主要大国的关系同时推进不偏向任一方',
             'actor pair 中/美/俄 三国 tone 差 < 2'),
            ('区域霸权稳固', '在南亚/印度洋的主导地位不被挑战',
             'actor + action>=100 只对周边国家'),
            ('国内凝聚力', '民主/宗教/种姓问题不引发结构性分裂',
             'actor + SOCIAL domain events'),
        ]
    },
    '互锁式': {
        'identity': '互锁式',
        'method_stage': '存在威胁互为锁定 — 对手的存在定义了身份的需求',
        'confidence': 0.83,
        'items': [
            ('对手行为驱动identity', '关键对手的威胁信号→ 本方的identity强度',
             'actor pair tone with key opponent trend'),
            ('不信任对等让步', '在关键安全议题上不会先手让步',
             'actor rejection(120) events count trend'),
            ('外部安全保障', '关键盟友的支持不显著下降',
             'actor pair tone with key ally'),
        ]
    },
    '交易式': {
        'identity': '交易式',
        'method_stage': '利益交换驱动 — 对齐是可交易的',
        'confidence': 0.75,
        'items': [
            ('利益导向行为', '不因意识形态锁定方向',
             'actor pair tone 波动大 ≠ Identity危机'),
            ('盟友关系弹性', '对同一盟友的关系有谈判/让步空间',
             'actor pair 010(statement) vs 120(reject) ratio'),
            ('交易换安全/繁荣', '经济安全交织的行为模式',
             'actor + structural domain events'),
        ]
    },
    'Ordnung型': {
        'identity': 'Ordnung型',
        'method_stage': '基于规则的秩序维护 — 制度恐惧崩坏',
        'confidence': 0.80,
        'items': [
            ('制度框架维护', '多边机构参与/推动不减',
             'actor + action 030-060 events trend'),
            ('对秩序挑战者的约束', '对破坏规则的实体施加成本',
             'actor pair tone with rule-breakers'),
            ('欧洲中心角色', '在欧盟/欧元区内的领导力不减',
             'actor + EU/ECB related events'),
        ]
    },
    '摆荡式': {
        'identity': '摆荡式',
        'method_stage': '大国间摇摆 — 在安全依赖与经济利益间平衡',
        'confidence': 0.72,
        'items': [
            ('摆动范围可控', '摇摆幅度不超历史极值',
             'actor pair tone 中-美 差 < 3'),
            ('不触发大国红线', '不引发安全担保国家的撤离信号',
             'actor pair tone with security guarantor'),
        ]
    },
    '撕裂式': {
        'identity': '撕裂式',
        'method_stage': 'Identity 内部冲突 — 在西方化与伊斯兰化间撕裂',
        'confidence': 0.76,
        'items': [
            ('内部张力', '世俗/宗教/民族矛盾不触发政权危机',
             'actor + SOCIAL domain events'),
            ('自主外交', '在对西方依赖与自主追求间维持空间',
             'actor pair tone with NATO/Russia ratio'),
        ]
    },
}


def main():
    with open(RULES_FILE, encoding='utf-8') as f:
        rules = json.load(f)

    # 保留已有 CHN
    existing = set(rules.get('hypotheses', {}).keys())

    for code, a in CA.CANONICAL_ACTORS.items():
        if code in existing:
            continue
        config = a.get('config', '')
        tier = a.get('tier', 3)
        template = VERIFICATION_TEMPLATES.get(config)

        # 无构型的主体: 给最简模板
        if not template:
            if tier <= 2:
                template = {
                    'identity': config or '未标定',
                    'method_stage': '待人工定义',
                    'confidence': 0.65,
                    'items': [
                        ('行为一致性', '行为不偏离区域角色',
                         f'actor {code} + tone trend 30d'),
                    ]
                }
            else:
                # Tier3: 企业/组织 → 最简 passive 模板
                template = {
                    'identity': a.get('type', 'Organization'),
                    'method_stage': f'被动观测 (Tier {tier})',
                    'confidence': 0.60,
                    'items': [
                        ('存在信号', '在 GDELT 中出现即记录',
                         f'actor {code} + any events count'),
                    ]
                }

        items = []
        for idx, (name, expected, gdelt_q) in enumerate(template['items'], 1):
            items.append({
                'id': f'{code}-{idx}',
                'item': name,
                'expected': expected.replace('{code}', code),
                'gdelt_check': {'query': gdelt_q.replace('{code}', code)},
                'contrary_signal': f'{name} — 持续背离预期',
                'observation_window': '3-6月',
                'status': 'pending',
            })

        rules.setdefault('hypotheses', {})[code] = {
            'identity': template['identity'],
            'method_stage': template['method_stage'],
            'confidence': template['confidence'],
            'confidence_delta': 0,
            'last_reviewed': None,
            'counter_evidence': [],
            'verification_items': items,
        }

    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    total = len(rules.get('hypotheses', {}))
    total_items = sum(len(h.get('verification_items', [])) for h in rules.get('hypotheses', {}).values())
    print(f'feedback_rules.json: {total} 主体, {total_items} 项验证 → {RULES_FILE}')


if __name__ == '__main__':
    main()
