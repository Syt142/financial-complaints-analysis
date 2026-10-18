# 核验与复现记录

本记录区分助手工具运行与学生本人复现，不把不同批次的耗时合并。更新日期为 2026-10-18。团队为孙永滔、束琪遇组，孙永滔担任主负责人，束琪遇为协作成员；职责与已确认贡献分别记载于 [团队分工与贡献记录](team_contributions.md)。

远程仓库：[Syt142/financial-complaints-analysis](https://github.com/Syt142/financial-complaints-analysis)，通过 PyCharm 创建为私有仓库并完成首次推送；该次 `main` 提交号为 `1eadd990bd810128eb236c2711c6d959aaae7797`。首次推送记录不等于最终提交版本，报告一正式代码以 [`phase-1-submission` 标签](https://github.com/Syt142/financial-complaints-analysis/tree/phase-1-submission) 及其对应提交号为准。

2026-10-18，按团队要求将仓库改为公开，教师可直接访问和克隆，无需协作者邀请。上段保留首次建仓时的历史状态。本次补齐团队信息后同步 `phase-1-submission` 标签，并保留此前快照；正式报告所列提交号用于核对本次版本。复现命令见项目根目录 `README.md`。

| 批次 | 执行者与证据来源 | 结果与范围 |
| --- | --- | --- |
| 初始全量分析 | Codex 助手通过本机工具执行；聚合结果保存在 `evidence/full_run.json` | 16,545,376 条记录，`complete_file=true`，耗时 358.075 秒。随包保存的历史证据，不改写为学生亲自执行。 |
| 后续全量复算 | Codex 助手操作；本机结果位于 `results/full/summary.json` | 16,545,376 条记录，`complete_file=true`，耗时 304.465 秒。`results/` 被 Git 忽略，此批结果不随仓库分发，也不替换上述历史证据。 |
| 2026-10-13 孙永滔在 PyCharm 复现自动测试 | 孙永滔本人运行并在对话中提供控制台日志 | 使用项目 `.venv/Scripts/python.exe` 执行 `-m unittest discover -s tests -v`；20 项测试全部通过，耗时 0.446 秒，进程退出代码 0。日志不含 Python 版本，故本条不据此声明版本。 |

两次全量运行的耗时不同，不能仅凭两次运行判定程序性能发生改进；这里仅如实记录各批测量值。

## 随仓库保存的证据

- `evidence/full_run.json`、`analysis.md`、各汇总 CSV：初始全量分析的聚合结果。
- `evidence/reference_control.json` 与 `reference_comparison.json`：独立 pandas 分析的控制值及 31 项比对通过记录。
- `evidence/test_results.txt`：助手初始执行 20 项测试的日志（0.468 秒），与学生后续的 0.446 秒记录是不同批次。
- `evidence/source_fingerprint.json`：原始文件大小及 SHA-256，便于持有老师数据的复现者确认输入版本。
- `evidence/manifest.json`：上述选定证据的 SHA-256 清单。本次整理前只读检查 9 项全部匹配；原文件保持不变。

## 孙永滔提供的测试日志摘要

以下内容摘录自孙永滔在对话中贴出的 PyCharm 控制台输出，便于说明复现来源；不是助手重新运行后生成的日志。原输出中 20 个具名测试均显示 `ok`。

```text
E:\Gpt\2026-10-12\fen\outputs\phase1_project\.venv\Scripts\python.exe -m unittest discover -s tests -v
----------------------------------------------------------------------
Ran 20 tests in 0.446s

OK

进程已结束，退出代码为 0
```

该测试命令运行合成和边界测试，不扫描老师的完整 8 GB CSV。后续若学生亲自执行全量分析，应另行保存运行命令、日期、摘要和核验结果，并新增记录，不能把既有助手运行改写成学生工作。

## 教师复现与提交范围

按项目根目录的 `README.md` 可在 Python 3.10 或以上版本运行测试及合成示例。全量复现需自行指定老师原始 CSV 的位置，并可先用源文件指纹确认输入版本。

无论使用公开还是私有仓库，原始投诉 CSV 和原始投诉叙述均不上传；`.venv/`、`.idea/` 和 `results/` 等本机产物不提交。代码、合成样例与聚合证据可以随项目提交。代码与文稿中的 AI 辅助披露保留；团队成员只填写本人实际完成的工作。
