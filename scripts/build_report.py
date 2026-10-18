"""Create a Chinese phase-one report and editable Markdown from actual evidence.

Optional dependency: reportlab==4.4.9. Analyzer itself has no third-party deps.
Usage: python scripts/build_report.py --output-dir OUTPUT --font-regular FONT --font-bold FONT
"""
import argparse
from datetime import date
import html
import json
from pathlib import Path
import re
import subprocess

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics.charts.barcharts import VerticalBarChart

ROOT=Path(__file__).resolve().parents[1]
REPO_URL='https://github.com/Syt142/financial-complaints-analysis'
SUBMISSION_TAG='phase-1-submission'
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--font-regular',default=r'C:\Windows\Fonts\simsun.ttc')
parser.add_argument('--font-bold',default=r'C:\Windows\Fonts\simhei.ttf')
args=parser.parse_args()
r=json.loads((ROOT/'evidence'/'full_run.json').read_text(encoding='utf-8'))
comparison=json.loads((ROOT/'evidence'/'reference_comparison.json').read_text(encoding='utf-8'))
fingerprint=json.loads((ROOT/'evidence'/'source_fingerprint.json').read_text(encoding='utf-8'))
N=r['rows']; f=r['frequencies']; run=r['run']
try:
    commit_full=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
except (OSError,subprocess.CalledProcessError):
    commit_full=SUBMISSION_TAG
commit=commit_full[:12] if commit_full != SUBMISSION_TAG else '见提交标签'
VERSION_URL=f'{REPO_URL}/tree/{commit_full}'
MARGIN=56.7
CONTENT_WIDTH=A4[0]-2*MARGIN-12  # Frames add 6 pt padding on each side.
pdfmetrics.registerFont(TTFont('CN',args.font_regular))
pdfmetrics.registerFont(TTFont('CNBold',args.font_bold))
pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNBold',italic='CN',boldItalic='CNBold')
BODY=ParagraphStyle('Body',fontName='CN',fontSize=10.5,leading=12.075,spaceAfter=8,wordWrap='CJK')
SMALL=ParagraphStyle('Small',parent=BODY,fontSize=10,leading=11.5,spaceAfter=6)
H1=ParagraphStyle('H1',parent=BODY,fontName='CNBold',fontSize=14,leading=19,spaceBefore=9,spaceAfter=8,keepWithNext=True)
H2=ParagraphStyle('H2',parent=BODY,fontName='CNBold',fontSize=11.5,leading=17,spaceBefore=6,spaceAfter=6,keepWithNext=True)
TITLE=ParagraphStyle('Title',parent=BODY,fontName='CNBold',fontSize=19,leading=26,spaceAfter=10)
CAP=ParagraphStyle('Caption',parent=SMALL,fontName='CNBold',leading=14,spaceBefore=5,spaceAfter=6,keepWithNext=True)
CODE=ParagraphStyle('Code',fontName='Courier',fontSize=10,leading=11.5,spaceBefore=5,spaceAfter=8)
story=[];md=[]
def p(text,style=BODY):
    story.append(Paragraph(text,style))
    md_text=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',r'[\2](\1)',text)
    md.append(md_text.replace('<b>','**').replace('</b>','**').replace('<br/>','\n'))
def h(text):p(text,H1);md[-1]='## '+md[-1]
def sub(text):p(text,H2);md[-1]='### '+md[-1]
def gap(n=5):story.append(Spacer(1,n))
def page():story.append(PageBreak());md.append('\n---\n')
def source_link(path,label=None):
    return f'<link href="{REPO_URL}/blob/{commit_full}/{path}" color="#1F4365">{html.escape(label or path)}</link>'

def table(caption,headers,rows,widths):
    p(caption,CAP)
    data=[[Paragraph(html.escape(str(v)),SMALL) for v in headers]]
    data += [[Paragraph(html.escape(str(v)).replace('\n','<br/>'),SMALL) for v in row] for row in rows]
    widths=[width*CONTENT_WIDTH/sum(widths) for width in widths]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EDF1')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),.45,colors.HexColor('#D9D9D9')),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(t);gap(7)
    md_rows=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    md_rows.extend('| '+' | '.join(str(v).replace('\n','<br>') for v in row)+' |' for row in rows)
    md.append('\n'.join(md_rows))
def code(text):
    story.append(Preformatted(text,CODE));md.append('```python\n'+text+'\n```')
def pct(n,d=N):return f'{100*n/d:.2f}%' if d else '不可计算'

def commands(text):
    story.append(Preformatted(text,CODE))
    md.append(chr(96)*3+'text\n'+text+'\n'+chr(96)*3)

# Main text page 1
p('大规模金融投诉数据的流式分析\n与异常线索发现'.replace('\n','<br/>'),TITLE)
p('报告1  问题与计算原型',H2)
p(f'团队成员：孙永滔、束琪遇　　阶段：1　　更新日期：2026-10-19<br/>仓库URL：<link href="{REPO_URL}" color="#1F4365">{REPO_URL}</link><br/>代码：<link href="{VERSION_URL}" color="#1F4365">{commit}</link>　　提交标签：{SUBMISSION_TAG}',SMALL)
h('执行摘要')
p('本项目面向需要分析大规模金融投诉数据的学生与研究人员，拟构建可在本地计算机运行的Python分析系统。阶段一完成CSV流式解析、质量诊断、分类与时间汇总、统计口径说明和自动化测试，并在老师提供的约8.93 GB文件上执行全量验证。程序处理16,545,376条记录，20项测试全部通过。初步结果显示投诉集中于征信相关类别，文本覆盖率随年份明显变化。当前证据限于描述性统计，不能据此推断企业责任或服务质量。下一阶段将完善数据字典，固定异常线索的定义、时间划分与评估方案。')
h('1 问题定义与申请批准的范围')
p('现实任务是把包含长文本、缺失值及多年分类变更的大型CSV，转换为可检查、可复现的分析证据。目标用户是课程项目成员、助教及投诉数据研究人员。输入为包含16个必需字段的本地CSV，允许字段重排和额外字段；输出为统计表、质量诊断、指标分子分母和运行记录。')
p('本阶段覆盖整份文件，不限定为某一金融产品或赔付预测任务。系统不会保存或上传原始叙述，不自动删除异常记录，不生成消费者身份画像，不作因果判断、赔偿决定或违法认定。产品和问题暂保留原标签，历史类别统一留待阶段二论证。')
p('后续任务拟识别超过预设偏离阈值的“产品-月份”，输出偏离分数、历史基准与质量提示，供使用者核对分类变化和事件背景。异常仅表示待调查线索。历史窗口、阈值和复核办法将在阶段二固定；本次申请批准这一任务范围，阶段一的工程验收标准见表1。')
table('表1 阶段一的可衡量完成标准',['标准','验收方式'],[
('正确处理全量文件','解析至文件结束；结果明确标记全量；总量与交叉表对账通过。'),
('在有限内存内运行','本机扫描阶段峰值进程内存低于512 MiB；记录实际环境和耗时。'),
('处理边界并可复现','至少8项有意义测试；合成示例可运行；原文件只读；输出含版本与口径。')],[130,352])

# Main text page 2
page();h('2 动机与初步相关工作')
p('CFPB数据库及字段说明[1][2]提供投诉的产品、问题、日期和企业回应信息，同时明确投诉并非消费者总体的随机样本。它们决定本项目的观察单位和解释边界。项目的学习目标是把数据定义落实为可执行检查，使使用者知道每个比例来自哪些记录。')
p('Python标准库csv[3]支持带引号的逗号与换行。本项目采用该解析器和流式计数，避免按物理行计数或把全部文本载入列表。流式读取是成熟方法，本项目不把它称为新的算法。')
p('Dou与Roh[4]研究投诉公开的经济影响，并在第2170页脚注10指出，历史叙述公开的同意机制可能带来选择偏差。本文据此将全体记录与文本子样本的比较列为待检验的敏感性问题，其对本地数据的影响仍需验证。Liu等的Isolation Forest[5]拟用于阶段三的异常检测比较。')
h('3 计算表示与模块分解')
p('一条逻辑CSV记录表示为字符串列表；字段名映射为列索引。频数采用Counter，交叉表以元组为键，日期转换为UTC。数值投诉ID用按需分配的位块记录是否出现，精确统计重复的额外记录。空值、非法值和零值分开表示。')
p('输入采用UTF-8或带BOM的UTF-8；无时区日期按UTC解释。空值仅指空字符串，NA及空白字符不自动视为缺失；数值ID去除前导零后比较。流程见图1，核心函数及输出见表2。',SMALL)
flow=Drawing(CONTENT_WIDTH,85)
labels=['CSV输入','结构与值检查','逐条聚合','对账与导出']
box_width=(CONTENT_WIDTH-3*13)/4
for i,label in enumerate(labels):
    x=i*(box_width+13)
    flow.add(Rect(x,32,box_width,34,fillColor=colors.HexColor('#F4F6F8'),strokeColor=colors.HexColor('#79848E'),strokeWidth=.7))
    flow.add(String(x+box_width/2,44,label,fontName='CN',fontSize=10.5,textAnchor='middle'))
    if i<3:
        end=x+box_width
        flow.add(Line(end+2,49,end+10,49,strokeColor=colors.black))
        flow.add(Polygon([end+10,49,end+6,52,end+6,46],fillColor=colors.black,strokeColor=None))
flow.add(String(CONTENT_WIDTH/2,11,'聚合JSON与CSV供阶段二分析和阶段三方法比较使用',fontName='CN',fontSize=10,textAnchor='middle'))
p('图1 阶段一处理流程',CAP);story.append(flow);md.append('CSV输入 → 结构与值检查 → 逐条聚合 → 对账与导出')
table('表2 核心函数及可检查的输出',['模块或函数','职责与输出'],[
('analyze_csv','读取并更新频数、缺失、日期与ID诊断；返回聚合字典。'),
('parse_timestamp','解析日期并统一为UTC；非法或缺失日期返回None并单独计数。'),
('ExactIdTracker.add','精确检查数值ID；超过位块内存上限时明确报错。'),
('export_results','导出JSON、CSV、Markdown及产物哈希清单。')],[140,342])
p('设输入总字符数为S、记录数为N、不同聚合键数为K、已分配ID位块数为B，则扫描时间主要为O(S+N)，末尾排序约为O(K log K)。扫描内存主要为O(K+B×128 KiB+最大记录长度)，并非对任意高基数数据都恒定。',SMALL)

# Main text page 3
page();h('4 Python原型与关键实现')
p('原型由解析统计、报告生成和命令行入口三个模块组成。正文保留说明设计取舍的短片段；以下展示读取与结构检查方式[3]，边界处理汇总见表3。')
code('with path.open("r", encoding="utf-8-sig",\n               newline="", buffering=4*1024*1024) as stream:\n    reader = csv.reader(stream, strict=True)\n    header = next(reader)\n    for row in reader:\n        if len(row) != len(header):\n            raise DataError("Unexpected field count")\n        # Update counters; do not append raw rows to a list.')
p(f'代码片段1 流式读取与行结构检查。片段缩略了空文件和列名检查；完整实现见{source_link("complaints_analyzer/core.py","core.py")}，边界用例见{source_link("tests/test_analyzer.py","test_analyzer.py")}。引号内换行由解析器处理，因此逻辑记录数与物理行数可以不同。',SMALL)
p('比例必须同时输出分子和分母。分母为零时返回None，由JSON表示为null，防止把“无法计算”误写为0%。及时回应率只以Yes和No作为有效分母；空值或未知取值保留在频数表内。')
code('def safe_rate(numerator, denominator):\n    return numerator / denominator if denominator else None\n\nchecks = {\n    name: sum(counter.values()) == total_rows\n    for name, counter in frequency_tables.items()\n}')
p('代码片段2 比例计算与总量对账。后半段是对实际对账步骤的简化表达；仓库还检查交叉表及ID分区。重复ID只记为诊断，不自动删行，以保持原始记录总量。',SMALL)
table('表3 无效或边界输入的处理',['输入情况','原型行为'],[
('缺列、重复列名、引号损坏或行列数不一致','停止并报错；不静默跳过。'),
('日期为空或无法解析','保留记录并计数；时间汇总放入无效日期组。'),
('ID为空、非数字或重复','分别统计；不把缺失编号当作同一个重复ID。'),
('文件只有表头或限制读取条数','零记录的比例为空；受限扫描明确标记非全量。'),
('输出可能覆盖输入；读取前后文件大小或修改时间变化','拒绝相应操作或拒绝接受该次结果；不等同逐字节篡改检测。')],[175,307])

# Main text page 4
page();h('5 真实文件运行与初步观察')
p('表4汇总2026年10月12日完整文件运行的主要结果，统计单位为投诉记录。数据为老师提供的CFPB格式快照，含16个字段；收件日期覆盖2011年12月1日至2026年7月5日。合成数据仅用于测试。')
table('表4 全量运行的主要数据与质量结果',['指标','结果'],[
('文件字节数及记录数',f'{r["source"]["bytes"]:,}字节；{N:,}条'),
('唯一数值ID及重复额外记录',f'{r["quality"]["unique_numeric_ids"]:,}个；{r["quality"]["duplicate_id_extra_rows"]}条'),
('ID缺失',f'{r["quality"]["missing_id"]:,}条'),
('非空叙述文本',f'{r["metrics"]["narrative_coverage"]["numerator"]:,}条；{pct(r["metrics"]["narrative_coverage"]["numerator"])}'),
('及时回应率',f'{r["metrics"]["timely_response"]["numerator"]:,}/{r["metrics"]["timely_response"]["denominator"]:,} = {100*r["metrics"]["timely_response"]["rate"]:.2f}%'),
('UTC日历日倒置',f'{r["quality"]["negative_forwarding_calendar_day"]:,}条；不作负处理时长解释')],[210,272])
p('文本覆盖率以全部记录为分母；及时回应率以Yes/No有效记录为分母，本文件该分母恰好等于总记录数，及时回应不等于问题解决。日期倒置按UTC日历日计为7,054条，按精确时间戳计为7,055条。',SMALL)
chart=Drawing(CONTENT_WIDTH,172);bars=VerticalBarChart();bars.x=42;bars.y=29;bars.width=CONTENT_WIDTH-59;bars.height=129
bars.data=[[f['year'][str(y)]/10000 for y in range(2020,2026)]]
bars.categoryAxis.categoryNames=[str(y) for y in range(2020,2026)]
bars.categoryAxis.labels.fontName='CN';bars.categoryAxis.labels.fontSize=10
bars.valueAxis.labels.fontName='CN';bars.valueAxis.labels.fontSize=10
bars.valueAxis.valueMin=0;bars.valueAxis.valueMax=600;bars.valueAxis.valueStep=200
bars.bars[0].fillColor=colors.HexColor('#435C75');bars.bars[0].strokeColor=None
chart.add(bars);chart.add(String(42,165,'单位：万条',fontName='CN',fontSize=10))
p('图2 2020至2025年的年度投诉记录数',CAP);story.append(chart)
md.append('图2数据（万条）：'+str({str(y):round(f['year'][str(y)]/10000,2) for y in range(2020,2026)}))
p(f'数据：{source_link("evidence/full_run.json","evidence/full_run.json")}中的year频数；绘图：{source_link("scripts/build_report.py","scripts/build_report.py")}。',SMALL)
p('2025年记录数比2024年增长99.08%。其中约90.25%的新增记录来自“Credit reporting or other personal consumer reports”标签。因此后续异常线索应按产品细分，不能只对全库总量设置阈值。图2不纳入2026这个未覆盖全年期间。')
p('同比 = (5,443,266 - 2,734,276) / 2,734,276；增量归属比例 = 上述原标签两年记录数之差 / 全部记录两年之差。后者仅针对该标签，不代表合并历史类别后的全部征信投诉。',SMALL)
p('有文本记录占比从2024年的29.78%变为2025年的22.45%；2026年截至文件截止日仅2.19%。这些变化提示文本子样本可能不具可比性，但尚不能确定公开延迟、类别构成或其他机制的贡献。公司字段还包含Pending Company Match，名称标签数不能当作真实企业家数。',SMALL)

# Main text page 5
page();h('6 正确性测试与可复现证据')
p('表5汇总自动化测试，表6列出历史全量扫描的资源测量；内部对账与独立实现比较分别检验不同层面的正确性。')
table('表5 自动化测试覆盖（合计20项）',['测试组','项数','主要验证内容'],[
('计数与指标',3,'手工计数一致；空值区别于NA/0；未知及时状态不进入有效分母。'),
('CSV与表结构',6,'逗号/换行、列顺序、缺列、重复列名、短行和损坏引号。'),
('日期与ID',5,'非法日期、UTC跨年、时间倒置、重复ID、缺失/非法/零ID。'),
('资源与读取范围',3,'位块上限、空文件/表头、受限扫描与恰好EOF。'),
('导出及端到端',3,'输入不变、叙述不导出、产物哈希、CLI成功及覆盖拒绝。')],[103,35,344])
p('20项测试全部通过。用例中刻意构造的坏输入用于验证失败处理，不代表真实文件发生解析失败。合成示例包含12条记录，其中9条及时回应、6条有叙述、3条金钱救济；输出与人工预期一致。')
p(f'真实运行包含{len(r["checks"])}项内部对账，全部通过。另将本程序与先前独立的pandas分块预分析比较，记录总数、缺失、日期范围、主要频数、交叉表和ID诊断共{len(comparison["checks"])}项控制均一致。这比仅检查“程序没有报错”提供了更强的正确性证据。')
peak=run.get('peak_process_memory_bytes')
table('表6 2026-10-12本机单次全量运行的资源证据',['项目','实测或说明'],[
('环境',f'Windows；AMD Ryzen 9 7945HX；Python {run["python"]}。'),
('全量扫描耗时',f'{run["elapsed_seconds"]:.1f}秒（约{run["elapsed_seconds"]/60:.2f}分钟）。'),
('扫描结束前进程峰值内存',f'{peak/1024**2:.2f} MiB；操作系统工作集口径。' if peak else '当前操作系统未返回测量。'),
('ID位块实际存储',f'{run["id_tracker_bytes"]/1024**2:.2f} MiB；不包含其他Python对象。'),
('适用限制','表中为单机单次测量；未作冷缓存或重复运行性能试验，不等同跨机器性能保证。')],[153,329])
p('峰值内存是在扫描结束时读取，覆盖此前进程峰值，不包含之后的JSON序列化和文件导出。源文件另计算完整SHA-256以固定数据版本。核心程序仅依赖标准库；运行命令、合成样本及证据文件随代码包提供。')
p('在项目根目录使用Python 3.10或以上执行以下最短核验；样例输出写入demo目录，不需要原始大文件。',SMALL)
commands('python scripts/verify_evidence.py\npython -m unittest discover -s tests -v\npython -m complaints_analyzer data/synthetic_complaints.csv --outdir demo')
p(f'设置及全量复现见{source_link("README.md","README")}；证据校验应为9/9通过。证据目录禁用Git换行转换，以保持清单所记录的原始字节。历史运行未直接记录Git提交号，本报告所列版本用于交付与复现，不倒填为历史运行版本。批次来源见{source_link("docs/verification_records.md","核验记录")}。',SMALL)

# Main text page 6
page();h('7 创新思路及其证据边界')
p('<b>工程贡献：</b>整合流式统计、精确ID诊断、总量对账、完整性标记及指标分母，使大文件分析结果可检查。各项技术已有成熟方法，本项目侧重面向教师数据的可复现集成与验证。')
p('<b>拟检验的研究问题：</b>限制为有文本记录时，回应分布和异常月份排序是否改变？阶段五拟在相同时间与分类口径下比较全体记录与文本子样本，并检查调整可观测构成后的差异。潜在贡献是把样本覆盖与分类变化纳入线索解释，该效果尚待受控评估。')
h('8 风险控制与阶段二至五计划')
p('主要风险为历史分类断点、未完整月份、文本子样本选择偏差及回应标签误读。采用原标签保留、稳定口径子集和敏感性分析；公司比较缺少客户量分母。教师文件的原下载地址、转换过程与再利用许可仍需向课程方确认；本项目仅作课程分析，公开仓库只提供代码、合成样本和聚合证据。后续里程碑见表7。')
table('表7 累积阶段计划及验收条件',['阶段与时间','工作及验收条件','分工安排'],[
('阶段2\n第6节课结束','依赖当前指纹及聚合；交付字段字典、分类与完整月份规则，冻结时间划分、窗口、阈值及评估方案。','孙永滔设计\n束琪遇复核'),
('阶段3\n第10节课结束','依赖冻结方案；比较滚动中位数/MAD、可解释统计模型、Isolation Forest，交付同一划分下的误报分析与至少一项消融。','孙永滔建模\n束琪遇核对'),
('阶段4\n第13节课结束','依赖方法选择结果；集成统计、检测与报告，交付正常/困难/失败三类演示、端到端及延迟测试。','孙永滔集成\n束琪遇测试'),
('阶段5\n第16节课结束','依赖稳定系统；受控评估文本覆盖/分类断点提示扩展，交付敏感性结果、监控回滚方案及反馈回应。','孙永滔定稿\n束琪遇校对')],[78,326,78])
p('拟在同一候选预算下比较方法，并由两位成员分别复核前20条线索，保留判据、分歧与讨论结果；实际数量随阶段二方案冻结。无真实标签时，注入识别率与人工复核结果分开报告；特征只使用当期及历史信息。可比月份不足时缩小产品范围，方法不优于基线时保留负结果并采用较简单方法。',SMALL)
h('9 个人贡献与AI辅助说明')
p('职责安排：孙永滔负责问题与范围、技术方案、开发验收、结果解释及报告定稿；束琪遇负责数据口径与结果复核、资料整理、测试补充及校对。测试复现：孙永滔于2026年10月13日在PyCharm中复现20项测试，0.446秒通过、退出代码0（本人提供日志）。代码、测试及稿件初稿由Codex辅助生成，全量分析由助手工具执行。',SMALL)

# References and appendix are outside the six-page main text.
page();h('参考文献')
references=[
('[1] Consumer Financial Protection Bureau. Consumer Complaint Database. 访问日期：2026-10-12.', 'https://www.consumerfinance.gov/data-research/consumer-complaints/'),
('[2] Consumer Financial Protection Bureau. How we share complaint data. 访问日期：2026-10-12.', 'https://www.consumerfinance.gov/complaint/data-use/'),
('[3] Python Software Foundation. csv — CSV File Reading and Writing, Python 3.12 documentation. 访问日期：2026-10-12.', 'https://docs.python.org/3.12/library/csv.html'),
('[4] Y. Dou and Y. Roh. Public Disclosure and Consumer Financial Protection. Journal of Financial and Quantitative Analysis, 59(5), 2164–2198, 2024. DOI: 10.1017/S0022109023000613.', 'https://doi.org/10.1017/S0022109023000613'),
('[5] F. T. Liu, K. M. Ting, and Z.-H. Zhou. Isolation Forest. IEEE ICDM, 413–422, 2008. DOI: 10.1109/ICDM.2008.17.', 'https://doi.org/10.1109/ICDM.2008.17'),
]
for label,url in references:
    p(html.escape(label),SMALL);p(f'<link href="{url}" color="#1F4365">{html.escape(url)}</link>',SMALL)
h('附录A 版本与提交信息')
p(f'源文件SHA-256：<br/>{fingerprint["sha256"][:32]}<br/>{fingerprint["sha256"][32:]}',SMALL)
p(f'公开仓库：<link href="{REPO_URL}" color="#1F4365">{REPO_URL}</link><br/>固定提交：<link href="{VERSION_URL}" color="#1F4365">{commit_full}</link><br/>提交标签：{SUBMISSION_TAG}；团队成员：孙永滔、束琪遇。本版更新于2026年10月19日；原始约8.93 GB数据不纳入代码包。',SMALL)
p('证据目录包含：evidence/full_run.json、evidence/reference_control.json、evidence/reference_comparison.json、evidence/source_fingerprint.json及evidence/test_results.txt。统计源于教师文件；历史采集和当前复现的边界见核验记录。',SMALL)
p('报告按《作业指导》第1–4页的通用格式与阶段一要求组织；后续阶段仅列计划。正文为前6页，参考文献及本附录不计入正文页数。提交前已补齐图表引用、校正实际页边距与换行哈希规则，并细化复现步骤及研究验收条件。',SMALL)
p('本阶段申请批准：以整份投诉CSV的可复现分析程序为基础，后续在稳定口径的月度聚合上研究异常线索识别，并把文本样本偏差作为受控扩展。是否采用该后续AI路线，需由教师在问题与范围审批中确认。',SMALL)

def footer(canvas,doc):
    canvas.saveState();canvas.setFont('CN',9)
    canvas.drawString(56.7,30,'报告1  问题与计算原型')
    canvas.drawRightString(A4[0]-56.7,30,str(doc.page))
    canvas.restoreState()
args.output_dir.mkdir(parents=True,exist_ok=True)
pdf=args.output_dir/'孙永滔_束琪遇_phase1_report.pdf'
doc=SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=56.7,leftMargin=56.7,
    topMargin=56.7,bottomMargin=56.7,title='大规模金融投诉数据的流式分析与异常线索发现',author='孙永滔、束琪遇')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(args.output_dir/'报告1_可编辑稿.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
print(pdf)
