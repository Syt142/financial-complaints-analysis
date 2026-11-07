# 阶段二在PyCharm中使用

继续打开原项目：E:\Gpt\2026-10-12\fen\outputs\phase1_project，不必复制或新建项目。

1. 顶部运行项选择“阶段二：样例、测试与基线”，点击绿色三角形。
2. 入口scripts/run_phase2.py依次运行手算例、32项测试、9项历史证据哈希和真实聚合基线。所有子步骤通过后显示PHASE 2 COMPLETE，退出代码为0。
3. 展开results/phase2：top20.csv是候选清单；validation_scores.csv是144个验证评分；injection_summary.csv是四档模拟结果；metrics.json记录配置与环境；run_log.txt保存过程。
4. 结果需与冻结的evidence_phase2比较：面板624行，划分72/336/144/72；四档每档200次，入选94/153/190/200，注入前已入选各27。耗时与测试秒数随电脑改变。

若没有该运行项，打开scripts/run_phase2.py，右键运行。解释器为项目.venv，工作目录为项目根目录。也可使用终端：python scripts/run_phase2.py。此入口无需8GB原始文件、无需联网安装模型、不需要GPU。

本次IDE以原缓存启动失败，提示.port文件无法访问。AI为本次启动单独使用E:/Gpt/pcsys作为缓存，原用户设置与项目解释器保持不变。这不是项目依赖；普通电脑正常打开PyCharm即可。缓存问题若重现可用工作区中的work/phase2/pycharm.vmoptions启动，不应删除个人设置。

软件在IDE内由AI操作完成验收；成员应亲自运行并解释结果后填写相应个人参与记录。报告中的模拟比例不是真实准确率。
