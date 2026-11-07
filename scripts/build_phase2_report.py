"""Build the cumulative phase-2 paper (6 body pages + references/appendices)."""
import argparse
import csv
import html
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect, PolyLine
from reportlab.graphics import renderSVG

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from complaints_analyzer import phase2

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--font-regular', default='C:/Windows/Fonts/simsun.ttc')
parser.add_argument('--font-bold', default='C:/Windows/Fonts/simhei.ttf')
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
E = ROOT / 'evidence_phase2'
M = json.loads((E/'metrics.json').read_text(encoding='utf-8'))
F = json.loads((ROOT/'evidence/full_run.json').read_text(encoding='utf-8'))
C = M['config']
PROMPTS = json.loads((ROOT/'docs/phase2_prompts.json').read_text(encoding='utf-8'))
def read_csv(name):
    with (E/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
ranked, scored = read_csv('top20.csv'), read_csv('validation_scores.csv')
repo = 'https://github.com/Syt142/financial-complaints-analysis'
try:
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
except (OSError, subprocess.CalledProcessError):
    commit = 'phase-2-submission'
VERSION = f'{repo}/tree/{commit}'
pdfmetrics.registerFont(TTFont('CN2', args.font_regular))
pdfmetrics.registerFont(TTFont('CN2B', args.font_bold))
pdfmetrics.registerFontFamily('CN2', normal='CN2',bold='CN2B',italic='CN2',boldItalic='CN2B')
W = A4[0]-2*56.7-12
body = ParagraphStyle('Body2',fontName='CN2',fontSize=10.5,leading=12.075,spaceAfter=7,wordWrap='CJK',rightIndent=8)
small = ParagraphStyle('Small2',parent=body,fontSize=10,leading=11.5,spaceAfter=5)
cell = ParagraphStyle('Cell2',parent=small,rightIndent=0)
title = ParagraphStyle('Title2',parent=body,fontName='CN2B',fontSize=18,leading=24,alignment=TA_CENTER,spaceAfter=8)
head = ParagraphStyle('Head2',parent=body,fontName='CN2B',fontSize=13,leading=17,spaceBefore=7,spaceAfter=7,keepWithNext=True)
cap = ParagraphStyle('Cap2',parent=small,fontName='CN2B',keepWithNext=True,spaceBefore=4)
mono = ParagraphStyle('Code2',fontName='Courier',fontSize=10,leading=11.5,spaceAfter=7)
story, md = [], []
def p(text, style=body):
    story.append(Paragraph(text,style))
    clean=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',r'[\2](\1)',text)
    md.append(clean.replace('<b>','**').replace('</b>','**').replace('<br/>','\n'))
def h(text):
    p(text,head);md[-1]='## '+md[-1]
def page():
    story.append(PageBreak());md.append('\n---\n')
def table(label, headers, rows, widths):
    p(label,cap)
    allrows=[headers]+rows
    data=[[Paragraph(html.escape(str(v)).replace('\n','<br/>'),cell) for v in row] for row in allrows]
    t=Table(data,colWidths=[W*x/sum(widths) for x in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ECEFF1')),
                          ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#455A64')),
                          ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#455A64')),
                          ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                          ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([t,Spacer(1,6)])
    md.append('\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                        ['| '+' | '.join(str(v).replace('\n','<br>') for v in row)+' |' for row in rows]))
def code(text):
    if any(len(line)>78 for line in text.splitlines()):
        raise ValueError('Code line too wide')
    story.append(Preformatted(text,mono));md.append('```python\n'+text+'\n```')
def link(path,label=None):
    return f'<link href="{repo}/blob/{commit}/{path}" color="#1F4365">{label or path}</link>'
names={'Mortgage':'房贷','Student loan':'学生贷款','Debt collection':'债务催收',
       'Checking or savings account':'支票或储蓄账户','Vehicle loan or lease':'车辆贷款或租赁',
       'Money transfer, virtual currency, or money service':'汇款相关服务'}
def pct(x):return f'{x*100:.2f}%'

# 1: title, abstract and cumulative research question
p('金融产品月度投诉量的异常增长识别研究',title)
p('基于大规模投诉记录的时间回测',ParagraphStyle('Subtitle',parent=title,fontSize=13,leading=18))
p('孙永滔　束琪遇',ParagraphStyle('Authors',parent=body,alignment=TA_CENTER))
p(f'阶段二累积修订稿 · 数据与实验设计 · 2026-11-08<br/>公开仓库：<link href="{repo}">{repo}</link><br/>固定版本：<link href="{VERSION}">{commit[:12]}</link>　标签：phase-2-submission',small)
h('摘　要')
p('为支持有限人工复核，本文研究金融产品月度投诉量的异常增长识别。沿用阶段一对约8.93 GB、1,654.54万条投诉的流式处理，构造六类连续原标签的624个产品月，按时间划分并建立过去12个月的中位数/MAD基线。验证期144个候选中取前20；对四档单点增长实施800次配对模拟，增加25%和100%的入选比例分别为47%和95%。32项测试通过。结果仅刻画回顾性排名及模拟敏感性，不代表真实异常准确率；后续将按冻结方案比较模型。')
p('<b>关键词：</b>金融投诉；月度异常线索；时间回测；大模型辅助编程；可复现评估',small)
h('1　引言与研究问题')
p('课程分析者面对长文本、缺失及多年分类变化的大文件，首先需要可靠计数，再决定把有限复核时间花在哪些月份。本文的研究问题是：相对于同一产品此前12个月的自身波动，哪些完整月份的投诉增长应优先核查；简单基线又会遗漏哪些幅度的增长？输入为产品月计数，输出为排名、历史参照及质量提示。')
p('本文承接报告一的读取、质量诊断及总量对账，增加数据筛选、时间划分、基线与受控实验，并回应“未看见计划研究题目”的教师反馈。阶段一发现2025年同比增量约90.25%来自单个征信原标签，提示不能用全库增长替代产品自身变化；本次据分类连续性缩小范围，而非把所有产品混在一起排序。')
p('CFPB明确投诉并非消费者经历的随机样本，且保留消费者当时所选产品标签[1]。本文以其字段说明[2]界定观察单位；中位数/MAD及时间窗口采用可解释统计基线，不声称提出新算法。既有投诉公开研究亦提示文本同意机制可能产生选择偏差[4]。本文的学习贡献在于用明确提示词提出反例、约束AI编程并落实为可运行检查，关键交互见第6节和附录B。')

# 2: data and split
page();h('2　数据来源、范围与探索性分析')
p('数据为教师提供的CFPB格式快照，含16字段；原始单位是一条投诉，日期范围为2011-12-01至2026-07-05。官方公开数据允许使用和分析[1]，但教师快照的原下载批次、转换过程及额外再分发条件未核实。因此不公开原始文件，仅使用阶段一固定指纹和聚合表。字段字典见附录A。')
table('表1　沿用阶段一的规模与质量诊断',['项目','数值及其设计含义'],[
 ['原始规模','8,925,381,287字节；16,545,376条；16列'],
 ['ID与产品','ID缺失2,390，重复额外记录0；Product缺失121。先对账，筛选时按原标签排除。'],
 ['日期及叙述','UTC日历日倒置7,054；叙述非空3,814,581条（23.06%）。不以叙述是否公开筛选主样本。'],
 ['范围变化','征信类别存在历史改名与重叠；2026年为不完整年度，均不进主实验。']], [1,3])
p('表1促成两项设计调整：以六条连续原标签代替征信混合标签；以全体投诉的月度数量代替有文本子样本。它们降低口径混淆，却牺牲覆盖：验证期六类合计452,936条，只占全库同期4,026,336条的'+pct(M['validation_coverage'])+'。覆盖较窄是限制，不能据此概括全库风险。')
table('表2　冻结的面板与整月划分',['区段','日期范围','产品月数','用途'],[
 ['暖启动','2017-05—2018-04','72','仅建立首个12月窗口'],
 ['开发','2018-05—2022-12','336','调试与规则设定'],
 ['验证','2023-01—2024-12','144','初始结果与模拟实验'],
 ['保留测试','2025-01—2025-12','72','本次仅核验结构；阶段三比较']], [1,1.8,.9,2.1])
p('六类为房贷、学生贷款、债务催收、支票或储蓄账户、车辆贷款或租赁、汇款相关服务；英文原标签见附录A。104个月×6=624个产品月，表2按同月整体划分。第一阶段已看过2025年度汇总，因此不将其描述为从未接触的数据；本次不生成2025评分或据此选参数。')
p('主特征仅为历史月计数；产品用于分组，月份用于排序，没有监督学习目标。实际公开日期和历史快照不可得，按收件月回测只能代表事后可见条件，不能证明真实在线提前预警。连续月份也存在自相关；时间划分避免直接看未来，但不会使样本自动独立。')

# 3: method and key code
page();h('3　处理流水线与可解释基线')
p('图1将阶段一与本阶段衔接。代码先核验历史证据，再读取month_product，独立核对月表计数与原总量，随后检查选中产品逐月是否存在。缺月停止，显式零保留；不把产品消失自动填为0。原始叙述及个人级邮编、标签、公司信息不进入评分。')
table('图1　累积的数据处理与分析流程',['阶段一保留','阶段二增补','最终输出'],[
 ['原CSV只读流式解析\n质量与ID诊断\n全量计数及哈希','聚合总量对账\n原标签/月份检查\n历史评分与配对注入','前20候选及历史参照\n分档模拟入选率\n日志、配置与图表']], [1,1,1])
p('设当前计数为n，历史12月中位数为m，MAD为历史各值到m的绝对偏差中位数；中位数计算使用Python标准库[3]。尺度s=max(1.4826×MAD,1)，得分=max(0,(n-m)/s)。1是以“条”为单位的下限，避免除零；常数1.4826采用常见尺度约定，不构成正态分布假设或显著性检验。得分只衡量向上偏离。')
p('代码1取自实际'+link('complaints_analyzer/phase2.py','phase2.py')+'的score_point。100条重复12次后变成130条：m=100、MAD=0、s=1、分数30；程序保留尺度触底标记，不能把30解释为概率。真实验证期零MAD候选为'+str(M['zero_mad_count'])+'个。',small)
source=inspect.getsource(phase2.score_point).splitlines()
snippet='\n'.join(line[4:] for line in source[source.index('    median = statistics.median(history)'):])
p('代码1　评分核心及零波动保护',cap);code(snippet)
p('历史窗口实际采用以下两行；timeline[i-window:i]不含当前月。得分时不使用回应、转交或其他事后字段。源码链接为本稿固定提交，非不可定位的截图。',small)
window_lines=[line.strip() for line in inspect.getsource(phase2.score_panel).splitlines() if 'history = [' in line]
p('代码2　排除当前月的历史切片',cap);code('\n'.join(window_lines))
p('候选只取正分数，按分数降序，月份、产品升序打破并列。固定预算为验证期两年共20条（20/144=13.89%），不是每月20条。实际第20名分数是这次名单截断点，不是部署时可通用的异常阈值。窗口和预算按课程解释性目标事先设定，本阶段未搜索最优参数。')

# 4: experiment design and verification
page();h('4　评估设计、模拟与实现验证')
p('无真实异常标签，真实流只报告候选名单与集中度。主模拟指标为“注入点进入前20的次数/试验次数”，反映固定人工预算下的增长敏感性；漏检意味着线索可能未获关注，误选会消耗复核时间，但本数据不能量化真实误报率。')
p('固定种子0—9，每种子从144个验证位置中无放回抽20个。每次只在一个位置增加25%、50%、100%或200%（向上取整且至少1条），四档位置配对；不同种子可重复，共800次单点实验，每档200次。每次复制原计数，重新计算滚动评分，允许注入影响后续窗口。还记录该位置在未注入时是否已入选。代码3摘取实际实现，省略末尾汇总。')
p('代码3　单点注入在副本上执行',cap)
inj=inspect.getsource(phase2.injection_experiment).splitlines()
start=next(i for i,l in enumerate(inj) if 'altered = counts.copy()' in l)
end=next(i for i,l in enumerate(inj[start:],start) if 'scored = [' in l)
code('\n'.join(l[16:] for l in inj[start:end]))
table('表3　正确性与可复现性检查',['检查','实际执行结果'],[
 ['阶段一回归20项','计数、CSV边界、日期/ID、隐私、CLI等均通过'],
 ['阶段二新增12项','手算、首个可评分月、未来扰动、当前排除、缺月/显式零、并列、非法月、配置顺序、注入不改原值/配对、坏聚合、测试期不评分均通过'],
 ['证据与环境','历史哈希9/9通过；月表对账16,545,376。PyCharm内Python '+M['environment']['python']+'，32项测试通过。'],
 ['时间与范围','评分/模拟及导出单次'+str(M['elapsed_seconds'])+'秒；不含IDE启动、单测及PDF。未重扫8.93 GB原始文件。']], [1,3])
p('表3对应的实际入口为'+link('scripts/run_phase2.py','scripts/run_phase2.py')+'。完整日志和配置随包提供。首次IDE启动因缓存锁失败，使用独立缓存后在原项目解释器运行成功，未修改原设置。核心仍仅依赖标准库；PDF额外使用reportlab，环境和随机种子分别记录。',small)
p('不确定性用各随机位置种子下检出比例的最小值、最大值和标准差描述。种子间位置可能重叠，且真实流已包含未知事件，所以这些波动不能解释为总体置信区间；也不能把未注入位置全部视为正常负类。')

# 5: results with actual chart
page();h('5　初始结果与错误线索分析')
table('表4　验证期单点增长进入前20的比例',['增加幅度','入选/试验','平均比例','种子最小—最大','标准差'],[
 [f'+{s["fraction"]*100:.0f}%',f'{s["hits"]}/{s["trials"]}',pct(s['rate']),
  f'{s["seed_rate_min"]*100:.0f}%—{s["seed_rate_max"]*100:.0f}%',f'{s["seed_rate_sd"]*100:.2f}个百分点'] for s in M['injections']], [1,1,1,1.5,1.2])
p('表4显示，增加25%仍有106/200次未进入候选预算；100%增幅亦有10/200次未入选。200%全部入选只说明强扰动容易检出。200个位置中27个在注入前已入选；四档新增入选依次为67、126、163、173，避免把全部命中都归功于注入。')
p('自然流144个候选中103个分数为正（71.53%），不能把“正分数”当作可信异常判据。前20为债务催收7、学生贷款5、车辆3、汇款3、账户1、房贷1；分组参照仍会反复选择持续上升的序列。图2展示债务催收的实际计数、历史中位数与入选点，供观察基线追随的滞后。')
draw=Drawing(W,170)
x0,y0,pw,ph=45,29,W-57,112
rows=sorted([r for r in scored if r['product']=='Debt collection'],key=lambda r:r['month'])
maximum=max(float(r['count']) for r in rows)*1.1
for j in range(4):
    yy=y0+ph*j/3
    draw.add(Line(x0,yy,x0+pw,yy,strokeColor=colors.HexColor('#DDDDDD'),strokeWidth=.4))
    draw.add(String(x0-5,yy-3,str(round(maximum*j/3)),fontName='CN2',fontSize=9,textAnchor='end'))
for field,color in [('count','#244F70'),('baseline','#B57930')]:
    points=[]
    for i,r in enumerate(rows):points.extend([x0+pw*i/(len(rows)-1),y0+ph*float(r[field])/maximum])
    draw.add(PolyLine(points,strokeColor=colors.HexColor(color),strokeWidth=1.3))
chosen={(r['month'],r['product']) for r in ranked}
for i,r in enumerate(rows):
    if (r['month'],r['product']) in chosen:
        draw.add(Circle(x0+pw*i/23,y0+ph*float(r['count'])/maximum,2.7,fillColor=colors.HexColor('#B54738'),strokeColor=None))
for i in (0,6,12,18,23):draw.add(String(x0+pw*i/23,y0-13,rows[i]['month'],fontName='CN2',fontSize=9,textAnchor='middle'))
draw.add(String(x0,154,'蓝：月投诉量　棕：过去12月中位数　红点：前20入选',fontName='CN2',fontSize=10))
p('图2　债务催收验证期计数与历史参照（单位：条）',cap)
story.append(draw);md.append('![图2 债务催收](phase2_debt_collection.svg)')
renderSVG.drawToFile(draw,str(args.output_dir/'phase2_debt_collection.svg'))
first=ranked[0]
p(f'最高分为{first["month"]}债务催收：{int(first["count"]):,}条，历史中位数{float(first["baseline"]):,.1f}条，分数{float(first["score"]):.2f}。相邻月份也进入候选，提示可能是连续过程而非彼此独立的事件。本文没有事件真值或人工已确认结论，不据图推断原因。主要失败风险是温和增长漏选、持续抬升重复占用预算及尺度估计不稳。')

# 6: AI and honest contribution, limitations, future
page();h('6　大模型协作、局限与下一阶段')
p('本阶段以Codex大模型辅助需求分解、Python开发、测试设计、统计解释和排版。成员提供教师反馈，要求先审方案，并多轮修订提示词及记录形式；AI执行开发与本机IDE操作。附录B完整展示15条经确认整理的提示词及建议/行动，属于交互内容整理，不冒充逐字日志。')
p('<b>一次数据判断：</b>“缺月能否填零”的提问促使AI核查原标签连续性，进而排除征信断点而保留六类面板。这一决定避免将改名人为构造成异常，代价是验证期只覆盖全库同期11.25%。<b>一次代码约束：</b>“把未来月份改得很大”的反例落实为防泄漏测试，并在PyCharm通过。相比接受AI口头保证，这使关键主张具有可失败的检查。')
table('表5　成员职责与本次参与说明',['成员','工作安排与记录边界'],[
 ['孙永滔','已在本次对话提供教师反馈、确定累积写作与IDE顺序、修改提示词要求并审核执行方案；负责问题界定、技术验收、结果解释与定稿。'],
 ['束琪遇','本阶段分工：负责16字段字典、产品口径核查、边界样例检查、结果复核与论文校对。'],
 ['AI辅助范围','代码、测试、数据卡、图表与论文由Codex辅助生成；本次PyCharm点击与运行由AI执行。后续成员分别执行和解释所属任务后更新贡献记录。']], [1,3])
p('表5将成员分工、已确认的需求审核与AI执行分别说明。可供两人复现和讲解的具体产物包括16字段字典、六类面板资格规则、624行划分、144行评分、20条候选、800条配对模拟及12项新增测试；未将AI操作日志记为成员亲自执行。')
p('<b>局限与伦理：</b>数据选择、渠道与公开延迟可能造成观测变化，缺少客户基数和事件标签；历史快照不等于当时可见信息。仅按连续原标签筛选也会遗漏研究上重要的征信类别。模型不能用于认定企业违法、个体画像或自动赔付；原始叙述及个人级字段不上传。尺度下限和固定预算是可解释约定，其敏感性尚待验证。')
table('表6　累积后续安排与完成标准',['阶段','任务、分工与验收'],[
 ['三：比较研究','孙永滔配置MAD/可解释统计模型/Isolation Forest[5]；束琪遇核查统一切分、案例和窗口/尺度消融。验证后冻结，2025只用于最终比较，保留不优于基线的负结果。'],
 ['四：系统集成','孙永滔集成分析与解释入口；束琪遇设计正常、困难及失败案例。验收端到端结果、输入失败处理及耗时。'],
 ['五：受控扩展','共同检验文本覆盖/分类提示是否改善解释；需要时新增扫描并遵守许可。报告前后成本、无收益情形及监控方案。']], [1,3])
p('<b>阶段结论：</b>历史中位数/MAD在固定20条预算下能稳定选出强模拟增长，但对25%增长只检出47%，且真实候选中存在连续月份重复入选。这支持在阶段三检验季节性与持续趋势处理，而非直接宣布已解决异常识别。现申请批准面板、时间划分及评估方案，完整模型比较沿同一论文继续累积。')

page();h('参考文献')
refs=[
 '[1] Consumer Financial Protection Bureau. Consumer Complaint Database. 访问：2026-11-08. https://www.consumerfinance.gov/data-research/consumer-complaints/',
 '[2] Consumer Financial Protection Bureau. How we share complaint data. 访问：2026-11-08. https://www.consumerfinance.gov/complaint/data-use/',
 '[3] Python Software Foundation. statistics — Mathematical statistics functions. https://docs.python.org/3/library/statistics.html （中位数计算接口；访问2026-11-08）.',
 '[4] Y. Dou, Y. Roh. Public Disclosure and Consumer Financial Protection. Journal of Financial and Quantitative Analysis, 59(5):2164–2198, 2024. DOI:10.1017/S0022109023000613. 文本选择偏差见p.2170脚注10。',
 '[5] F. T. Liu, K. M. Ting, Z.-H. Zhou. Isolation Forest. IEEE ICDM, 413–422, 2008. DOI:10.1109/ICDM.2008.17. （阶段三拟比较方法）.'
]
for ref in refs:p(ref,small)
h('附录A　数据字典、版本与复现')
p('原始字段及风险见下表；本阶段实际输入只有月份、原产品标签、计数。历史原始指纹与阶段一证据保持不变。',small)
dictionary=[
 ('Date received','日期时间','UTC月；非法另计'),('Product','类别','分组；历史标签原样保留'),
 ('Sub-product','类别','子产品；不评分'),('Issue','类别','问题；不评分'),('Sub-issue','类别','子问题；不评分'),
 ('Consumer complaint narrative','可空文本','不进入评分/公开产物'),('Company public response','可空类别','事后回应；不作特征'),
 ('Company','类别','不比较公司质量'),('State','地区类别','不作特征'),('ZIP code','字符串','不转整数/不画像'),
 ('Tags','可空标签','可能敏感；不作特征'),('Submitted via','类别','渠道变化可影响覆盖'),
 ('Date sent to company','日期时间','事后字段；不作特征'),('Company response to consumer','可空类别','不等于满意度'),
 ('Timely response?','类别','不等于问题已解决'),('Complaint ID','标识字符串','只用于阶段一质量诊断')]
table('表A1　原始16字段字典',['字段','类型','解释/本阶段用途'],dictionary,[2.1,1,2])
page();h('附录A（续）　原标签、复现与反馈回应')
table('表A2　六个原产品标签',['原标签','本文简称'],[[p,names[p]] for p in C['products']],[3,1])
p(f'固定代码版本：<link href="{VERSION}">{commit}</link><br/>阶段二标签：phase-2-submission；阶段一保留标签：phase-1-submission。源码中的核心评分见'+link('complaints_analyzer/phase2.py','phase2.py')+'，实验参数见'+link('configs/phase2.json','configs/phase2.json')+'。',small)
p('最短运行（在项目根目录，Python 3.10及以上；核心无第三方依赖）：',small)
story.append(Preformatted('python scripts/run_phase2.py\npython scripts/verify_evidence.py evidence_phase2',mono))
md.append('```text\npython scripts/run_phase2.py\npython scripts/verify_evidence.py evidence_phase2\n```')
p('运行输出在results/phase2。冻结产物在evidence_phase2，包括metrics.json、panel.csv、validation_scores.csv、top20.csv、injection_trials.csv、injection_summary.csv、run_log.txt及manifest.json。运行耗时随机器改变；同配置计数、排名及模拟统计应相同。IDE直接选择“阶段二：样例、测试与基线”。',small)
p('重建PDF：安装requirements-report.txt后执行python scripts/build_phase2_report.py --output-dir reports。默认使用Windows宋体/黑体；其他平台通过字体参数指定中文TTF/TTC。图2的SVG及可编辑Markdown同时生成。',small)
table('表A3　教师反馈与累积修订',['教师反馈','本次采取的行动','位置'],[
 ['未看见计划研究题目','标题、摘要及研究问题明确产品月增长识别','第1页'],
 ['采用论文格式','按引言、数据、方法、实验、讨论及参考组织，沿用阶段一成果','正文第1—6页'],
 ['关键代码写入PDF','实际评分、历史切片与注入片段，固定源码链接','第3—4页代码1—3'],
 ['展示大模型提示词与工作','确认后整理15条，说明AI建议和实际行动','第6页、附录B']], [1.3,2.6,1])
p('正文前6页；参考文献和附录不计正文页数。本版基于报告一修订，不另起研究项目。70分为成员转述的教师评分；本稿只回应已提供的具体意见，不倒推未经提供的评分细项。',small)

# fixed four pages for full prompts, three columns only
for start,end in [(0,3),(3,7),(7,11),(11,15)]:
    page();h('附录B　我们给AI的提示词与建议/行动'+('（续）' if start else ''))
    if start==0:
        p('以下为成员需求及经确认的第一人称提示词整理，非逐字聊天转录。AI回答按本次已采取的行动概括；未实施事项明确保留为建议。表格仅含编号、提示词和建议/行动三列。',small)
    table('表B1　大模型协作记录'+('（续）' if start else ''),['编号','我们给AI的提示词','AI给出的建议或采取的行动'],
          [[x['id'],x['prompt'],x['action']] for x in PROMPTS[start:end]],[.35,2.4,2.25])

def footer(canvas,doc):
    canvas.saveState();canvas.setFont('CN2',9)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(63,37,'金融产品月度投诉量的异常增长识别研究 · 阶段二累积稿')
    canvas.drawRightString(A4[0]-63,37,str(doc.page));canvas.restoreState()

target=args.output_dir/'孙永滔_束琪遇_phase2_report.pdf'
doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=56.7,leftMargin=56.7,topMargin=56.7,bottomMargin=56.7,
                      title='金融产品月度投诉量的异常增长识别研究',author='孙永滔、束琪遇')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(args.output_dir/'报告2_可编辑稿.md').write_text('\n\n'.join(md),encoding='utf-8')
print(target)
