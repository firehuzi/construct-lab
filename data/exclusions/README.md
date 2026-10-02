# 把工具导出的排除断言记录放这里

在 `backtest-tool/index.html` 里跑完一个场景、写完「🚫 我排除的路径」后，
点「🚫 导出排除断言（JSON）」，把 `exclusions-<场景>.json` 放到本目录。

然后：

    python exclusion_ledger.py --ingest

它会算出【不可证伪比例】= 框架当前的健康读数。
（也可直接放在 `backtest-tool/` 下，摄入器两个目录都扫。）
