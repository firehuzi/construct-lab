ConStruct 项目 · 完成内容与版本迭代
框架迭代
v1.0  初始构型分类（10种国家构型）
v2.0  方法≠Identity修正（JP冻结局=方法⑤，Identity=国体）
v3.0  Identity分层（Identity ≠ 表达 ≠ 方法）
v4.0  ICC（身份—能力耦合度）
v5.0  DNA矩阵（四维剖面拆解旧标签）
v5.x  数据流统一（frontmatter + 桥接脚本）
四层架构
层	内容	数量	状态
Layer 1 主体库	国家/国际组织/企业档案	46档	✅
DNA矩阵 + ICC框架	2份	✅
Layer 2 场景地图	10个核心场景分析	10+1档	✅
场景耦合图 + 行为系统地图	2份	✅
Layer 3 事件传播	事件传播索引 + 四级传播链定义	1份	✅
Layer 4 推演引擎	主体情景推演	6档	✅
SUL 战略不确定性层	1模块	✅
工程系统
数据流：   construct_bridge.py → actors.json → engine + HTML工具
引擎：     construct-engine/ → pipeline.py → engine.py → radar.html
诊断工具： 框架v2.0.html（11层）→ 框架v3.0.html（+SUL）
内容生产
系列	篇数	状态
特朗普中东	2篇	已排版
新加坡	3篇	已发布
十年六相	3篇	已排版
不接电话	4篇	已排版（Ref_003 存档）
跨域验证
域	案例	存档位置
地缘	46档主体 + 10场景	ConStruct_Archive/
经济	中国收入结构 + 稳定锚迁移	Ref_001 / Ref_002
社会	不接电话系列四篇	Ref_003
工具	三域同构指南	ConStruct_Archive/
工具版本
版本	核心变化	文件
v2.0	11层交互式诊断 + L2瀑布映射	框架v2.0.html
v3.0	+SUL层（五维不确定性）	框架v3.0.html
v4.0	Python引擎四核 + Radar仪表盘	construct-engine/
v4.1	GDELT+FRED 数据接入 + Tier1规则	pipeline.py + rules/
目录结构
D:\地缘推演台\
├── ConStruct_Archive/     # 46档主体 + 10场景 + DNA矩阵 + 参考档案
├── construct-engine/      # v4.1实时引擎（Python）
├── construct_bridge.py    # MD↔JSON桥接
├── actors.json            # 结构化主体数据
├── 框架v3.0.html           # 交互式诊断工具（含SUL）
├── 框架v2.0.html           # 交互式诊断工具
├── *公众号排版.html        # 8篇已排版
└── References/            # 跨域案例