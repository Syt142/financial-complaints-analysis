"""Build the cumulative article, editable Markdown, and the validation figure."""
import argparse
import csv
import html
import inspect
import json
import math
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, CondPageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, Circle, String, PolyLine
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
body = ParagraphStyle('Text', fontName='CN2', fontSize=11, leading=12.65,
                      firstLineIndent=22, wordWrap='CJK', rightIndent=7, spaceAfter=4)
small = ParagraphStyle('Note', parent=body, firstLineIndent=0, fontSize=10, leading=11.5)
cell = ParagraphStyle('Cell', parent=small, rightIndent=0, spaceAfter=0)
title = ParagraphStyle('Title', parent=small, fontName='CN2B', fontSize=18.5, leading=24,
                       alignment=TA_CENTER, rightIndent=0, spaceAfter=4)
head = ParagraphStyle('Section', parent=small, fontName='CN2B', fontSize=13, leading=16,
                      spaceBefore=8, spaceAfter=4, keepWithNext=True)
subhead = ParagraphStyle('Subsection', parent=head, fontSize=11, leading=13, spaceBefore=4)
cap = ParagraphStyle('Caption', parent=small, alignment=TA_CENTER, fontName='CN2B',
                     rightIndent=0, keepWithNext=True, spaceBefore=4, spaceAfter=3)
mono = ParagraphStyle('Code',fontName='Courier',fontSize=10,leading=11.5,spaceAfter=4)

story, md = [], []
def p(text, style=body):
    story.append(Paragraph(text,style))
    clean=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',r'[\2](\1)',text)
    md.append(clean.replace('<b>','**').replace('</b>','**').replace('<br/>','\n'))
def h(text):
    p(text,head);md[-1]='## '+md[-1]
def sub(text):
    p(text,subhead);md[-1]='### '+md[-1]
def page():
    story.append(PageBreak());md.append('\n---\n')
def table(label, headers, rows, widths, *, long_table=False):
    if long_table:
        story.append(CondPageBreak(150))
        p(label, ParagraphStyle('LongTableCaption', parent=cap, keepWithNext=False))
    else:
        p(label, cap)
    allrows=[headers]+rows
    data=[[Paragraph(html.escape(str(v)).replace('\n','<br/>'),cell) for v in row] for row in allrows]
    t=Table(data,colWidths=[W*x/sum(widths) for x in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.9,colors.black),
                          ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#455A64')),
                          ('LINEBELOW',(0,-1),(-1,-1),.8,colors.black),
                          ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                          ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    story.extend([t,Spacer(1,6)])
    md.append('\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                        ['| '+' | '.join(str(v).replace('\n','<br>') for v in row)+' |' for row in rows]))
def code(text):
    if any(len(line)>78 for line in text.splitlines()):
        raise ValueError('Code line too wide')
    story.append(Preformatted(text,mono));md.append('```python\n'+text+'\n```')
def link(path,label=None):
    return f'<link href="{repo}/blob/{commit}/{path}" color="#1F4365">{label or path}</link>'
def pct(x):return f'{x*100:.2f}%'

# Article front matter and research question
p('金融产品月度投诉量的异常增长识别研究', title)
md[-1] = '# ' + md[-1]
p('——基于大规模投诉记录的时间回测', ParagraphStyle('Subtitle', parent=title, fontSize=13, leading=17))
p('孙永滔　束琪遇', ParagraphStyle('Authors', parent=title, fontName='CN2', fontSize=11.5, leading=15))
p(f'阶段二　数据与实验设计　　2026年11月8日　　<link href="{VERSION}" color="#244F70">项目版本 {commit[:12]}</link>',
  ParagraphStyle('Metadata', parent=small, rightIndent=0, alignment=TA_CENTER, spaceAfter=9))
p('<b>摘　要　</b>为确定有限复核名额下应优先核查的投诉增长月份，本文利用阶段一从1,654.54万条金融投诉中提取的月度计数，构建六类产品的624个产品月面板。以前12个月计数的中位数与绝对偏差中位数为基线，在144个验证候选中选取20条，并实施800次单点增长模拟。计数增加25%和100%时，入选比例分别为47%和95%。债务催收占真实候选前20名中的7条，部分月份相邻。结果显示该方法对强增长较敏感，温和增长和连续事件仍需进一步评估。',small)
p('<b>关键词　</b>金融投诉、异常增长、时间回测、滚动中位数、大模型辅助编程',small)
h('1　引言')
p('金融投诉量同时受到产品规模、申诉渠道和分类口径的影响。美国消费者金融保护局（CFPB）保留投诉人提交时选择的原始类别，并指出该数据库覆盖主动投诉人群[1–2]。Dou与Roh指出，历史叙述须经同意才能公开，文本子样本可能存在选择偏差[3]。因此，本研究以原产品标签分组，并将有叙述和无叙述的记录一起计数。')
p('阶段一完成了大文件流式解析和总量核对。在2025年较2024年的投诉增量中，约90.25%来自一个征信产品标签。全库增长率因而很难反映单个产品的历史波动。本文考察两个问题：在只能核查20条线索时，哪些产品月份的增长最突出？向已知月份加入不同幅度的增长，排名方法能识别多少？')
h('2　数据与方法')
sub('2.1　数据来源与字段')
p('教师提供的CFPB格式快照包含8,925,381,287字节、16,545,376条投诉和16个字段，收件日期覆盖2011年12月1日至2026年7月5日。表1给出字段口径，完整数据卡可在'+link('docs/phase2_data_card.md','项目仓库')+'查阅。CFPB允许公众分析其发布的数据[1]。课程快照的原下载批次、转换过程和再分发条件尚待核实，公开仓库提供代码、合成样例和聚合结果。')
table('表1　投诉快照的字段及其含义',['字段','含义','字段','含义'],[
 ['Date received','收件日期','State','州或地区'],
 ['Product','产品原标签','ZIP code','邮编或屏蔽值'],
 ['Sub-product','子产品','Tags','特定群体标签'],
 ['Issue','投诉问题','Submitted via','提交渠道'],
 ['Sub-issue','问题细类','Date sent to company','转交公司日期'],
 ['Consumer complaint narrative','公开叙述','Company response to consumer','公司处理结果'],
 ['Company public response','公司公开回应','Timely response?','回应是否及时'],
 ['Company','公司名称标签','Complaint ID','投诉标识符']], [1.7,.85,1.7,.85])
p('收件和转交时间按日期解析，邮编按字符串保存，产品及问题按类别计数。投诉标识符缺失2,390条，重复数值标识符的额外记录为0条，产品名缺失121条。公开叙述非空占23.06%。基线只需收件月、原产品标签及其计数，可直接复用阶段一月表。程序保留显式零值，并对缺失的产品月报错，以免将分类调整后的首次出现误判为骤增。')
sub('2.2　研究样本与时间划分')
p('主实验选择历史标签连续的房贷、学生贷款、债务催收、支票或储蓄账户、车辆贷款或租赁、汇款相关服务。征信产品在2017年和2023年附近出现标签变动与重叠。为保持口径一致，主实验限于上述六类，并使用截至2025年底的月份。验证期共纳入452,936条，占同期全库4,026,336条的'+pct(M['validation_coverage'])+'，研究结论的适用范围限于这些类别。')
table('表2　六类产品的时间划分',['区段','起止月份','产品月数','用途'],[
 ['预热期','2017.05—2018.04','72','建立首个历史窗口'],
 ['开发期','2018.05—2022.12','336','开发程序、确定规则'],
 ['验证期','2023.01—2024.12','144','评估基线与模拟检出率'],
 ['保留测试期','2025.01—2025.12','72','核查结构，供阶段三比较']], [1,1.55,.85,1.9])
p('表2将同月各产品划入同一区段，共104个月。阶段一曾观察2025年度总量，本阶段将该年的逐月评分保留至模型比较。按收件月回测反映事后可见的信息。数据库公开可能滞后，且相邻月份可能相关，在线预警效果仍需专门验证。')
sub('2.3　异常增长的评分')
p('对每个产品月，以此前12个完整月的中位数作为参照，以计数相对中位数的绝对偏差中位数（MAD）度量历史波动。代码1给出历史窗口。代码2将尺度下限设为1条并记录尺度触底，避免历史波动为零时发生除零。中位数使用Python标准库计算[4]。')
p('代码1　构造历史窗口',cap)
window_lines=[line.strip() for line in inspect.getsource(phase2.score_panel).splitlines() if 'history = [' in line]
code('\n'.join(window_lines))
p('代码2　计算向上偏离分数',cap)
source=inspect.getsource(phase2.score_point).splitlines()
code('\n'.join(line[4:] for line in source[source.index('    median = statistics.median(history)'):]))
p('若历史12个月均为100条，当前为130条，则中位数为100、MAD为0、尺度取1，得到分数30。真实验证期的零MAD候选有'+str(M['zero_mad_count'])+'个。将两年验证期的正分数由高到低排序，取前20名。并列时依次按月份和原标签升序排列。完整实现见'+link('complaints_analyzer/phase2.py','评分与排序源码')+'。')
sub('2.4　模拟实验与实现检验')
p('以模拟增长点进入前20的次数除以试验次数，衡量固定复核预算下的检出率。每个种子从144个验证位置中无放回抽取20个位置。每次只在一个位置将计数增加25%、50%、100%或200%，向上取整且至少增加1条。四档共用同一组位置，10个种子（0至9）合计800次。每次在副本上重新评分，单点注入可影响随后12个月的历史基线。')
p('代码3　向单个产品月注入增长',cap)
inj=inspect.getsource(phase2.injection_experiment).splitlines()
start=next(i for i,l in enumerate(inj) if 'altered = counts.copy()' in l)
end=next(i for i,l in enumerate(inj[start:],start) if 'scored = [' in l)
code('\n'.join(l[16:] for l in inj[start:end]))
table('表3　实现检验与复现条件',['检验项目','结果'],[
 ['阶段一回归','20项通过，覆盖CSV结构、计数、ID及隐私检查。'],
 ['阶段二新增','12项通过，覆盖时间窗口、未来值扰动、缺月、并列排序、位置配对及输入完整性等。'],
 ['数据对账与运行','历史哈希9/9通过，月表计数与16,545,376条原始记录相符。PyCharm使用Python '+M['environment']['python']+'，本机基线实验耗时'+str(M['elapsed_seconds'])+'秒。']], [1.15,3.85])
p('表3为实际运行结果。在项目根目录执行 <font name="Courier">python scripts/run_phase2.py</font> 可复现手算样例、测试与基线。六个原标签、时间边界及随机种子见'+link('configs/phase2.json','实验配置')+'，运行日志与评分表见'+f'<link href="{VERSION}/evidence_phase2" color="#244F70">固定版本实验记录</link>。',small)
h('3　实验结果与讨论')
sub('3.1　模拟增长的检出率')
table('表4　四种增长幅度的模拟检出结果',['增长幅度','入选次数/试验次数','检出率','种子间范围','标准差'],[
 [f'+{s["fraction"]*100:.0f}%',f'{s["hits"]}/{s["trials"]}',pct(s['rate']),
  f'{s["seed_rate_min"]*100:.0f}%—{s["seed_rate_max"]*100:.0f}%',f'{s["seed_rate_sd"]*100:.2f}个百分点'] for s in M['injections']], [1,1.5,.9,1.15,1.25])
p('表4中，增加25%时有106/200次未入选，增加100%时仍有10/200次未入选。每档200次注入中，有27次对应的位置原本就在前20名。扣除这部分后，由弱到强四档分别新增67、126、163和173次入选。种子间的范围与标准差刻画抽取位置带来的波动，同一位置可以出现在不同种子中。')
sub('3.2　候选月份的时间分布')
p('真实数据的144个候选中有103个正分数。前20名中，债务催收占7条、学生贷款5条、车辆贷款或租赁3条、汇款相关服务3条，其余两类各1条。图1以债务催收为例，同时画出月投诉量、历史中位数和入选点。')

draw=Drawing(W,170)
x0,y0,pw,ph=45,29,W-57,112
rows=sorted([r for r in scored if r['product']=='Debt collection'],key=lambda r:r['month'])
maximum = 5000 * math.ceil(max(float(r['count']) for r in rows) / 5000)
for tick in range(0, maximum + 1, 5000):
    yy = y0 + ph * tick / maximum
    draw.add(Line(x0,yy,x0+pw,yy,strokeColor=colors.HexColor('#DDDDDD'),strokeWidth=.4))
    draw.add(String(x0-5,yy-3,f'{tick:,}',fontName='CN2',fontSize=9,textAnchor='end'))
for field,color in [('count','#244F70'),('baseline','#B57930')]:
    points=[]
    for i,r in enumerate(rows):points.extend([x0+pw*i/(len(rows)-1),y0+ph*float(r[field])/maximum])
    draw.add(PolyLine(points,strokeColor=colors.HexColor(color),strokeWidth=1.3,
                      strokeDashArray=[5, 2] if field == 'baseline' else None))
chosen={(r['month'],r['product']) for r in ranked}
for i,r in enumerate(rows):
    if (r['month'],r['product']) in chosen:
        draw.add(Circle(x0+pw*i/23,y0+ph*float(r['count'])/maximum,2.7,fillColor=colors.HexColor('#B54738'),strokeColor=None))
for i in (0,6,12,18,23):draw.add(String(x0+pw*i/23,y0-13,rows[i]['month'],fontName='CN2',fontSize=9,textAnchor='middle'))
draw.add(Line(48,156,67,156,strokeColor=colors.HexColor('#244F70'),strokeWidth=1.4))
draw.add(String(72,152,'月投诉量（条）',fontName='CN2',fontSize=10))
draw.add(Line(167,156,186,156,strokeColor=colors.HexColor('#B57930'),strokeDashArray=[5,2],strokeWidth=1.4))
draw.add(String(191,152,'过去12个月的中位数',fontName='CN2',fontSize=10))
draw.add(Circle(328,156,2.7,fillColor=colors.HexColor('#B54738'),strokeColor=None))
draw.add(String(337,152,'进入前20名',fontName='CN2',fontSize=10))
story.append(KeepTogether([draw, Paragraph('图1　债务催收月投诉量、历史中位数与入选月份',cap)]))
md.append('![图1 债务催收月投诉量、历史中位数与入选月份](phase2_debt_collection.svg)')
renderSVG.drawToFile(draw,str(args.output_dir/'phase2_debt_collection.svg'))
first=ranked[0]
p(f'最高分出现在{first["month"]}，当月债务催收投诉为{int(first["count"]):,}条，历史中位数为{float(first["baseline"]):,.1f}条，分数为{float(first["score"]):.2f}。其相邻月份也入选，显示持续增长可能占用多个复核名额。连续月份重复入选会挤占其他线索的复核名额，低幅增长的漏选也可能延迟调查。由于缺少客户规模分母和真实事件标签，候选仍需结合类别调整及事件背景核查。')

peak = max(rows, key=lambda r: int(r['count']))
p(f'图1中投诉量最高的月份为{peak["month"]}，共{int(peak["count"]):,}条。此时历史中位数已升至{float(peak["baseline"]):,.0f}条，MAD为{float(peak["mad"]):,.1f}条，偏离分数为{float(peak["score"]):.2f}。与4月相比，10月数量更高，但较宽的历史波动范围降低了该月的排序。这一差异表明，解释候选线索需要同时查阅原始计数、历史参照和分数。')
sub('3.3　适用范围与局限')
p('各档模拟对同一位置单独增加投诉数。对原本排在前20以外的173次试验，增加25%后有67次进入前20，约占38.7%。温和变化更容易受原有波动掩盖。真实事件还可能缓慢演变或同时波及多个产品，单点模拟只能检验其中一种变化方式。')
p('跨产品比较还受到市场规模和投诉渠道的影响。本文采用产品自身的历史参照，并保留有限复核预算，仍可能遗漏低频产品和改名产品。实际调查须结合业务背景，并核对数据在调查当时是否已经公开。')
story.append(CondPageBreak(310))
h('4　成员分工与大模型协作')
p('孙永滔与束琪遇负责项目的问题界定、数据核查和结果解释，具体分工见表5。团队使用Codex辅助实现和验证，并按研究过程整理了表6中的15条提示词。关于缺月的提问影响了产品筛选，关于未来月份的反例则转化为自动化测试。')
table('表5　成员职责与本次参与说明',['成员','职责与参与情况'],[
 ['孙永滔','负责研究问题、技术验收、结果解释与定稿。本阶段提出修改要求，审核研究方案，并确定提示词的记录方式。'],
 ['束琪遇','本阶段分工包括核查16个字段和产品分类口径、检查边界样例、复核结果与校对论文。']], [.8,4.2])
p('表6按团队确认的提示词整理。第三列记录AI提出的建议或实际执行的工作，本次代码生成、PyCharm操作和运行记录由AI完成。',small)
table('表6　研究中的提示词与大模型协作记录',['编号','我们给 AI 的提示词','AI 给出的建议或采取的行动'],
      [[item['id'],item['prompt'],item['action']] for item in PROMPTS],[.34,2.45,2.21], long_table=True)
h('5　结论与展望')
p('在六类金融产品、两年验证期共20条的复核预算下，基线对25%单点增长的模拟检出率为47%，对100%单点增长为95%。债务催收的多个相邻月份重复入选，提示逐月排序可能高估一次持续增长所需的复核名额。阶段三将沿用相同面板、预算与注入位置，由孙永滔实现可解释统计模型和孤立森林[5]，束琪遇按分工核对时间划分和典型案例。以保留测试期的公平比较、窗口敏感性分析及重复入选案例分析作为验收依据。')
p('后续集成阶段将检验正常输入、边界和失败情形。文本覆盖与产品分类提示的作用留待受控比较。公开产物限于聚合计数和程序，投诉叙述及个人级位置数据保存在本地。')
page();h('参考文献')
refs=[
 '[1] Consumer Financial Protection Bureau. Consumer Complaint Database [DB/OL]. 2026-11-08. https://www.consumerfinance.gov/data-research/consumer-complaints/',
 '[2] Consumer Financial Protection Bureau. How we share complaint data [EB/OL]. 2026-11-08. https://www.consumerfinance.gov/complaint/data-use/',
 '[3] Dou Y, Roh Y. Public Disclosure and Consumer Financial Protection. Journal of Financial and Quantitative Analysis, 2024, 59(5), 2164–2198. DOI 10.1017/S0022109023000613. 文本公开的选择偏差见第2170页脚注10。',
 '[4] Python Software Foundation. statistics — Mathematical statistics functions [EB/OL]. 2026-11-08. https://docs.python.org/3/library/statistics.html',
 '[5] Liu F T, Ting K M, Zhou Z H. Isolation Forest. IEEE International Conference on Data Mining, 2008, 413–422. DOI 10.1109/ICDM.2008.17.'
]
for ref in refs:p(ref,small)
p(f'项目仓库　<link href="{repo}">{repo}</link><br/>提交标签　phase-2-submission<br/>提交版本　<link href="{VERSION}">{commit}</link>',small)


def footer(canvas,doc):
    canvas.saveState();canvas.setFont('CN2',9)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawCentredString(A4[0]/2,35,str(doc.page))
    canvas.restoreState()

target=args.output_dir/'孙永滔_束琪遇_phase2_report.pdf'
doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=56.7,leftMargin=56.7,topMargin=56.7,bottomMargin=56.7,
                      title='金融产品月度投诉量的异常增长识别研究',author='孙永滔、束琪遇')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(args.output_dir/'报告2_可编辑稿.md').write_text('\n\n'.join(md),encoding='utf-8')
print(target)
