# 大规模金融投诉 CSV 分析程序

阶段一原型。输入老师提供的约 8.93 GB CSV，逐条处理逻辑记录，输出聚合统计、质量诊断、统计口径和校验结果。未训练 AI 模型，不作因果推断，不预测消费者赔付。数据文件不随仓库或压缩包分发。

## 仓库与阶段一提交版本

仓库地址：[Syt142/financial-complaints-analysis](https://github.com/Syt142/financial-complaints-analysis)。这是私有仓库；教师需使用自己的 GitHub 账号接受协作者邀请后才能查看和克隆。仓库地址本身不会授予访问权限，本说明不表示已发送或接受邀请。

阶段一正式代码版本使用 [`phase-1-submission` 标签](https://github.com/Syt142/financial-complaints-analysis/tree/phase-1-submission)。提交报告引用该标签及其对应的提交号，后续开发继续在 `main` 上进行，不移动提交标签。

教师获得权限后，可执行：

```powershell
git clone https://github.com/Syt142/financial-complaints-analysis.git
cd financial-complaints-analysis
git checkout phase-1-submission
python -m unittest discover -s tests -v
python -m complaints_analyzer data/synthetic_complaints.csv --outdir results/demo
```

检出标签用于复现，不用于日常开发。在 PyCharm 继续修改项目时，先确认当前分支为 `main`；检查变更后通过 Git 菜单的“提交”和“推送”保存并上传，Windows 默认快捷键分别为 `Ctrl+K`、`Ctrl+Shift+K`。提交前检查文件清单，避免添加原始数据、本机环境或运行结果。

## 环境

- Python 3.10 或以上；已在 Windows 与 Python 3.12.14 实测。
- 核心程序、示例和自动测试仅使用 Python 标准库，无需 pandas 或显卡。
- `requirements.txt` 说明可选的报告生成依赖；生成 PDF 才需要 reportlab 4.4.9。
- 在解压后的项目根目录执行以下命令。将 `python` 换成你机器的 Python 可执行文件路径即可。

## 最短复现路径

```powershell
python -m unittest discover -s tests -v
python scripts/make_demo.py
python -m complaints_analyzer data/synthetic_complaints.csv --outdir results/demo
```

合成示例应有 12 条记录、9 条及时回应、6 条有文本、3 条金钱救济。示例文本明确写着 SYNTHETIC，不能用作真实实验数据。

## 分析老师的真实文件

```powershell
python -m complaints_analyzer "E:/QQ/complaints.csv/complaints.csv" --outdir results/full --batch-size 500000
```

第一次调试可增加 `--limit 10000`。输出中的 `run.complete_file=false` 会明确说明该次不是全量。`--batch-size` 只控制进度输出间隔，不代表将整批记录载入内存。文件必须按 UTF-8/UTF-8 BOM 编码；格式错误时停止并说明位置，不静默跳行。

预期字段为老师文件中的 16 列。允许列重新排序和新增列，缺少必需列、重复列名、行字段数不匹配或引号损坏均报错。程序将源文件以只读方式打开，输出目标不能覆盖输入。

## 输出

| 文件 | 内容 |
| --- | --- |
| `analysis.md` | 可阅读的自动分析报告与统计口径 |
| `summary.json` | 完整聚合值、缺失、指标分子分母、运行环境、校验 |
| `frequencies.csv` | 年/月、产品、问题、公司、地区、渠道和回应频数 |
| `cross_tables.csv` | 年×产品、月×产品、年×回应、年×文本等交叉计数 |
| `quality.csv` | 各字段空值和日期、ID质量诊断 |
| `manifest.json` | 上述产物的 SHA-256，便于检查文件是否改变 |

原始叙述不进入输出。默认输出目录放入 `.gitignore`，避免意外提交大文件。`evidence/` 中是本次真实运行的选定证据，`data/` 中仅有合成样本。

原始投诉数据不上传到任何 Git 仓库，无论仓库是公开还是私有；也不提交 `.venv/` 和 `.idea/` 等本机环境与 IDE 工作区配置。老师可先运行随包的合成样例，进行全量复现时再指定其持有的原始 CSV 路径。

可选的独立复算（需要 `requirements-reference.txt` 中的 pandas/numpy）及报告重建：

```powershell
python -m pip install -r requirements-reference.txt
python scripts/reference_pandas.py "PATH_TO_COMPLAINTS.csv" --outdir results/reference
python -m pip install -r requirements-report.txt
python scripts/build_report.py --output-dir reports
```

报告生成脚本默认使用Windows宋体/黑体；其他系统通过`--font-regular`和`--font-bold`提供可用中文TTF/TTC字体。原始参考脚本执行完整预分析，与标准库主程序的实现独立。`verify_reference.py`使用随包保存的控制值进行快速比对。

## 核心模块

- `complaints_analyzer/core.py`：严格 CSV 读取、UTC日期转换、计数、精确数值ID位图查重、对账、结果导出。
- `complaints_analyzer/reporting.py`：把聚合结果转换为 Markdown。
- `complaints_analyzer/__main__.py`：CLI参数、输入保护、错误出口。
- `tests/test_analyzer.py`：20项单元和端到端测试。
- `scripts/make_demo.py`：可重复生成合成输入。
- `scripts/verify_reference.py`：将当前结果与独立 pandas 预分析的控制值对照。

## 关键口径

1. 统计单位为投诉记录，不能视为独立消费者。
2. 空值是精确的空字符串，`NA`、`0` 和空白字符保持原值。
3. 及时回应率分母只含 Yes/No；分母为零输出 null，不输出虚假的0%。
4. 文本覆盖率是非空叙述/全部记录，不能解释成消费者是否写过文本。
5. 转交间隔是 UTC 收件日至转交日的日历日差，不是企业处理时间。
6. 同时保留“精确时间戳倒置”和“日历日期倒置”两个计数。
7. 产品、问题和公司保持原始标签。历史类别、别名和 Pending Company Match 不擅自合并。
8. ID缺失与重复单独计数，不直接删行。数值ID的前导零被规范化；`001` 与 `1` 算同一编号。
9. 位图按每 2^20 个编号分块，每块128 KiB。默认最多1024块，超过则明确报错；不能把精确查重悄悄改为近似。
10. 读取前后检查文件大小和修改时间；强内容指纹另存于 `evidence/source_fingerprint.json`。它不是源文件合法性认证。

## 性能和限制

内存不保存所有记录。主要占用为当前 CSV 字段、分类/交叉表的不同键及ID位块；分类基数过高仍会增加内存，不能声称对任何输入都是常数空间。单个字段默认上限1000万字符。输出构造、排序和JSON序列化还会使用额外内存。本次 `peak_process_memory_bytes` 在扫描结束测量，包含此前进程峰值，不包括随后导出阶段。

真实输入全量运行的时间和内存见 `evidence/full_run.json`。当前验证主要面向这份文件和合成边界输入，不代表所有编码、CSV方言和恶意输入都已验证。

## 后续阶段

阶段二：完善数据字典、历史分类断点、完整月份范围和评估设计。阶段三：在清洗后的月度聚合上比较规则基线、可解释统计方法与Isolation Forest等AI方法，标记需要人工复核的异常线索。阶段四：集成加载、分析、检测、报告与异常输入处理。阶段五：受控比较加入文本覆盖及分类变更提示前后，分析误报与样本选择偏差。

异常检测是待教师批准的后续路线，阶段一未实现；异常不代表违法、欺诈或消费者受到损害。不存在真实异常标签时，注入异常实验只能检验对指定扰动的识别能力，不能当成真实世界准确率。

## 归属与AI辅助披露

本代码、报告初稿和测试由 Codex AI 助手辅助生成；初始全量分析、后续全量复算及相应核验由助手工具执行。学生已在 PyCharm 中使用项目 `.venv` 的 Python 解释器运行 `python -m unittest discover -s tests -v`，用户提供的控制台日志显示：20 项测试全部通过，耗时 0.446 秒，进程退出代码为 0。这条记录确认了学生的测试复现，不代表学生已亲自完成全量分析或独立编写全部代码。分批记录与证据范围见 [核验与复现记录](docs/verification_records.md)。

团队名称、成员及真实个人分工尚待填写；远程仓库地址与正式提交版本约定见上文。不得把助手工具执行虚构为学生已亲自完成的实验。提交前每位成员应能说明其实际修改、测试、理解与验证内容。

外部数据：老师提供的 CFPB 风格投诉数据；定义参考 CFPB 官方页面。未复制第三方项目代码；核心调用 Python 标准库。原始数据的取得范围、版本及使用许可需由团队依据老师说明补充。无论仓库是否公开，仅提交代码、合成样本、说明与聚合证据，不上传原始投诉文件。
