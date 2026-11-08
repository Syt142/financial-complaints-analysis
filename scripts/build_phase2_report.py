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
import textwrap

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, CondPageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, Circle, String, PolyLine
from reportlab.graphics import renderSVG

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from complaints_analyzer import phase2
sys.path.insert(0, str(ROOT / 'tests'))
from test_phase2 import Phase2Tests

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--font-regular', default='C:/Windows/Fonts/simsun.ttc')
parser.add_argument('--font-bold', default='C:/Windows/Fonts/simhei.ttf')
parser.add_argument('--student-ids', nargs=2, metavar=('SUN_ID', 'SHU_ID'),
                    help='Student IDs in byline order: Sun Yongtao, Shu Qiyu.')
args = parser.parse_args()
if args.student_ids and not all(re.fullmatch(r'[0-9]{8}', value) for value in args.student_ids):
    parser.error('--student-ids expects two eight-digit IDs')
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
body = ParagraphStyle('Text', fontName='CN2', fontSize=10.5, leading=12.075,
                      firstLineIndent=21, wordWrap='CJK', rightIndent=7, spaceAfter=4,
                      allowWidows=0, allowOrphans=0)
small = ParagraphStyle('Note', parent=body, firstLineIndent=0, fontSize=10, leading=11.5)
cell = ParagraphStyle('Cell', parent=small, leading=10, rightIndent=0, spaceAfter=0)
title = ParagraphStyle('Title', parent=small, fontName='CN2B', fontSize=18.5, leading=24,
                       alignment=TA_CENTER, rightIndent=0, spaceAfter=4)
head = ParagraphStyle('Section', parent=small, fontName='CN2B', fontSize=13, leading=16,
                      spaceBefore=8, spaceAfter=4, keepWithNext=True)
subhead = ParagraphStyle('Subsection', parent=head, fontSize=11, leading=13, spaceBefore=4)
cap = ParagraphStyle('Caption', parent=small, alignment=TA_CENTER, fontName='CN2B',
                     rightIndent=0, keepWithNext=True, spaceBefore=4, spaceAfter=3)
code_font = 'Courier'
console_font = Path('C:/Windows/Fonts/consola.ttf')
if console_font.is_file():
    pdfmetrics.registerFont(TTFont('ListingMono', str(console_font)))
    code_font = 'ListingMono'
mono = ParagraphStyle('Code',fontName=code_font,fontSize=10,leading=12)
line_numbers = ParagraphStyle('SourceLines', parent=mono, textColor=colors.HexColor('#60717C'))
listing_caption = ParagraphStyle('ListingTitle', parent=cell, fontName='CN2B', leading=12)
listing_source = ParagraphStyle('ListingSource', parent=mono, alignment=TA_RIGHT)

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
def code(caption, function, first_statement, last_statement):
    source, first_line = inspect.getsourcelines(function)
    start = next(i for i, line in enumerate(source) if line.lstrip().startswith(first_statement))
    stop = next(i for i in range(start, len(source)) if source[i].lstrip().startswith(last_statement))
    snippet = textwrap.dedent(''.join(source[start:stop + 1])).rstrip()
    first, last = first_line + start, first_line + stop
    anchor = f'L{first}' if first == last else f'L{first}-L{last}'
    source_path = Path(inspect.getsourcefile(function)).relative_to(ROOT).as_posix()
    url = f'{repo}/blob/{commit}/{source_path}#{anchor}'
    source_label = f'{Path(source_path).name} / {function.__name__}()'
    if pdfmetrics.stringWidth(source_label, code_font, 10) > W * .55 - 12:
        source_label = source_path
    header = Table([[Paragraph(caption, listing_caption),
                     Paragraph(f'<link href="{url}" color="#425460">{source_label}</link>', listing_source)]],
                   colWidths=[W * .45, W * .55], hAlign='LEFT')
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    gutter = 26
    available = W - gutter - 12
    if max(pdfmetrics.stringWidth(line, code_font, 10) for line in snippet.splitlines()) > available:
        raise ValueError(f'Listing exceeds the text column: {caption}')
    numbers = '\n'.join(str(n) for n in range(first, last + 1))
    panel = Table([[Preformatted(numbers, line_numbers), Preformatted(snippet, mono)]],
                  colWidths=[gutter, W - gutter], hAlign='LEFT')
    panel.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F6F7F8')),
        ('LINEABOVE',(0,0),(-1,0),.55,colors.HexColor('#81909A')),
        ('LINEBEFORE',(1,0),(1,0),.35,colors.HexColor('#CFD5D9')),
        ('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#ABB5BB')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),6),
        ('RIGHTPADDING',(0,0),(-1,-1),6)]))
    story.extend([KeepTogether([header, panel]), Spacer(1, 4)])
    md.extend([f'**{caption}**　[{source_label}（第{first}–{last}行）]({url})',
               '```python\n' + snippet + '\n```'])
def link(path,label=None):
    return f'<link href="{repo}/blob/{commit}/{path}" color="#1F4365">{label or path}</link>'
def pct(x):return f'{x*100:.2f}%'

# Article front matter and research question
p('金融产品月度投诉量的异常增长识别研究', title)
md[-1] = '# ' + md[-1]
p('——基于大规模投诉记录的时间回测', ParagraphStyle('Subtitle', parent=title, fontSize=13, leading=17))
authors = ['孙永滔', '束琪遇']
if args.student_ids:
    authors = [f'{name}（{number}）' for name, number in zip(authors, args.student_ids)]
p('　　　'.join(authors), ParagraphStyle('Authors', parent=title, fontName='CN2', fontSize=11.5, leading=15))
p('阶段二　数据与实验设计　　2026年11月8日',
  ParagraphStyle('Metadata', parent=small, rightIndent=0, alignment=TA_CENTER, spaceAfter=6))
p(f'项目仓库　<link href="{repo}">{repo}</link><br/>提交标签　phase-2-submission<br/>提交版本　<link href="{VERSION}">{commit}</link>',small)
p('<b>摘　要　</b>为找出有限复核名额下应优先核查的投诉增长月份，我们利用阶段一从1,654.54万条金融投诉中提取的月度计数，构建六类产品的624个产品月面板。以前12个月计数的中位数与绝对偏差中位数为基线，在144个验证候选中选取20条，并实施800次单点增长模拟。计数增加25%和100%时，入选比例分别为47%和95%。债务催收占真实候选前20名中的7条，部分月份相邻。结果显示该方法对强增长较敏感，温和增长和连续事件仍需进一步评估。',small)
p('<b>关键词　</b>金融投诉、异常增长、时间回测、滚动中位数、大模型辅助编程',small)
h('1　引言')
p('金融投诉量同时受到产品规模、申诉渠道和分类口径的影响。美国消费者金融保护局（CFPB）保留投诉人提交时选择的原始类别，并指出该数据库覆盖主动投诉人群[1–2]。Dou与Roh指出，历史叙述须经同意才能公开，文本子样本可能存在选择偏差[3]。因此，我们按原产品标签分组，将有叙述和无叙述的投诉一起计数。')
p('在阶段一，我们用流式读取程序汇总投诉记录并核对总量。在2025年较2024年的投诉增量中，约90.25%来自一个征信产品标签。全库增长率因而很难反映单个产品的历史波动。我们希望知道，在只能核查20条线索时，哪些产品月份的增长最突出？如果向已知月份加入不同幅度的增长，这种排名方法能识别多少？')
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
p('我们为主实验选择了历史标签连续的房贷、学生贷款、债务催收、支票或储蓄账户、车辆贷款或租赁、汇款相关服务。征信产品在2017年和2023年附近出现标签变动与重叠。为保持口径一致，我们只纳入这六类产品，样本截至2025年12月。验证期共纳入452,936条，占同期全库4,026,336条的'+pct(M['validation_coverage'])+'，研究结论的适用范围限于这些类别。')
table('表2　六类产品的时间划分',['区段','起止月份','产品月数','用途'],[
 ['预热期','2017.05—2018.04','72','建立首个历史窗口'],
 ['开发期','2018.05—2022.12','336','开发程序、确定规则'],
 ['验证期','2023.01—2024.12','144','评估基线与模拟检出率'],
 ['保留测试期','2025.01—2025.12','72','核查结构，供阶段三比较']], [1,1.55,.85,1.9])
p('表2将同月各产品划入同一区段，共104个月。我们在阶段一已看过2025年的年度汇总，因此本阶段只核查该年的数据结构，把逐月评分留到阶段三比较模型时使用。按收件月回测反映事后可见的信息。数据库公开可能滞后，且相邻月份可能相关，在线预警效果仍需专门验证。')
sub('2.3　异常增长的评分')
p('对每个产品月，以此前12个完整月的中位数作为参照，以计数相对中位数的绝对偏差中位数（MAD）度量历史波动。代码1给出历史窗口。代码2将尺度下限设为1条并记录尺度触底，避免历史波动为零时发生除零。中位数使用Python标准库计算[4]。')
code('代码1　历史预热与窗口构造', phase2.score_panel, 'if i < cfg["window"]:', 'history = [')
code('代码2　计算向上偏离分数', phase2.score_point, 'median = ', '"zero_mad":')
p('若历史12个月均为100条，当前为130条，则中位数为100、MAD为0、尺度取1，得到分数30。真实验证期的零MAD候选有'+str(M['zero_mad_count'])+'个。将两年验证期的正分数由高到低排序，取前20名。并列时依次按月份和原标签升序排列。完整实现见'+link('complaints_analyzer/phase2.py','评分与排序源码')+'。')
p('代码3给出固定预算排序的核心实现。仅保留向上偏离的候选，当正分候选数少于复核名额时，返回全部正分候选。月份和产品名提供确定性的并列顺序，使同一输入在不同运行中得到相同名单。')
code('代码3　固定预算下的候选排序', phase2.top_k, 'if budget < 1:', 'key=lambda')
sub('2.4　模拟实验与实现检验')
p('以模拟增长点进入前20的次数除以试验次数，衡量固定复核预算下的检出率。每个种子从144个验证位置中无放回抽取20个位置。每次只在一个位置将计数增加25%、50%、100%或200%，向上取整且至少增加1条。四档共用同一组位置，10个种子（0至9）合计800次。每次在副本上重新评分，单点注入可影响随后12个月的历史基线。')
code('代码4　向单个产品月注入增长', phase2.injection_experiment, 'altered = counts.copy()', 'altered[(month, product)] =')
p('单次注入先复制完整计数映射，再修改一个产品月。因此四种幅度可在相同起点上比较。检出结果由重新评分后的名单决定，注入点之后的月份继续沿用滚动规则。程序还记录该位置在原始名单中是否已入选，用于解释模拟结果的增量贡献。')
p('代码5检验时间顺序是否被实际实现：先保存评分，再把最后一个月份的计数改成一亿，断言此前所有月份的结果相同。若历史窗口错误地包含未来值，这个断言就可能失败。该测试对应表6中关于检验AI代码的追问。')
code('代码5　未来数据扰动的回归测试', Phase2Tests.test_future_change_cannot_change_past,
     'def test_future_change_cannot_change_past', 'self.assertEqual(')
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
draw.add(String(W/2, 2, '图1　债务催收月投诉量、历史中位数与入选月份',
                fontName='CN2B', fontSize=10, textAnchor='middle'))
story.extend([draw, Spacer(1, 4)])
md.append('![图1 债务催收月投诉量、历史中位数与入选月份](phase2_debt_collection.svg)')
renderSVG.drawToFile(draw,str(args.output_dir/'phase2_debt_collection.svg'))
first=ranked[0]
p(f'最高分出现在{first["month"]}，当月债务催收投诉为{int(first["count"]):,}条，历史中位数为{float(first["baseline"]):,.1f}条，分数为{float(first["score"]):.2f}。其相邻月份也入选，显示持续增长可能占用多个复核名额。连续月份重复入选会挤占其他线索的复核名额，低幅增长的漏选也可能延迟调查。由于缺少客户规模分母和真实事件标签，候选仍需结合类别调整及事件背景核查。')

peak = max(rows, key=lambda r: int(r['count']))
p(f'图1中投诉量最高的月份为{peak["month"]}，共{int(peak["count"]):,}条。此时历史中位数已升至{float(peak["baseline"]):,.0f}条，MAD为{float(peak["mad"]):,.1f}条，偏离分数为{float(peak["score"]):.2f}。与4月相比，10月数量更高，但较宽的历史波动范围降低了该月的排序。这一差异表明，解释候选线索需要同时查阅原始计数、历史参照和分数。')
sub('3.3　适用范围与局限')
p('各档模拟对同一位置单独增加投诉数。对原本排在前20以外的173次试验，增加25%后有67次进入前20，约占38.7%。温和变化更容易受原有波动掩盖。真实事件还可能缓慢演变或同时波及多个产品，单点模拟只能检验其中一种变化方式。')
p('有限复核预算要求同时考虑增长强度与候选竞争。同样增加25%，历史波动较窄的月份可能迅速升至前列，而本来波动较大的产品仍可能排在20名之后。因此，47%的检出率由本面板、所抽月份和预算共同决定。后续比较方法时，我们将固定面板、注入位置和复核预算，分别检查各产品的检出情况。')
p('跨产品比较还受到市场规模和投诉渠道的影响。我们按产品自身的历史波动排序，并限定复核名额，仍可能遗漏低频产品和改名产品。实际调查须结合业务背景，并核对数据在调查当时是否已经公开。')
h('4　成员分工与大模型协作')
p('我们按需要解决的问题分工。孙永滔负责研究范围、实验约定和技术验收，束琪遇负责字段口径、样本连续性和结果核对。我们在方案确认后请Codex辅助编写程序、操作本机PyCharm并导出结果。表5把各自承担的问题与本阶段材料对应起来，具体思路见4.1和4.2节。')
sub('4.1　孙永滔的研究方案与技术验收')
p('<b>问题一，怎样把研究题目变成具体任务？</b>我根据教师第一次指导意见，提出继续完善报告一，并要求明确输入、输出和成功标准。我们确认以产品月计数为输入，输出20条优先核查线索。程序沿用阶段一月表，减少重复扫描大文件。实验方案固定六类产品、12个月历史窗口和时间划分，便于后续方法在相同条件下比较。')
p('<b>问题二，怎样知道AI写的程序符合时间顺序？</b>我的技术验收要求是先解释手算样例，再检查边界情况，最后运行真实聚合数据。对“历史12个月均为100、当前为130”的样例，预期分数为30。我们还请AI编写代码5，把最后一个月改为一亿，检查此前评分是否改变。本机IDE日志记录了手算、32项测试和真实基线的执行过程。')
p('<b>问题三，怎样说明程序发现增长的能力？</b>我要求把代码、提问和结果放进同一篇论文。我们采用固定20条预算，在相同位置分别增加四档投诉量，并记录位置原本是否已入选。AI执行了800次配对模拟，结果表保留每次注入位置、原值、增量和是否入选，便于检查47%的平均检出率由哪些情况组成。')
sub('4.2　束琪遇的数据口径与结果复核')
p('<b>问题一，哪些产品月份可以放在一起比较？</b>我的字段与样本核查围绕16个字段说明和原产品月表展开。2023年8月，旧征信标签有77,311条投诉，新标签也有20,736条。它们在同月并存，要拼接序列还需核实分类范围。我们据此保留六类连续原标签，并报告其同期覆盖率11.25%。')
p('<b>问题二，怎样区分缺失记录和真实零值？</b>我负责的边界检查包括缺月、历史不足和零波动。显式记录的0条仍是一个有效值，月表中没有该产品则需要核查。对应测试会检查缺月时报错、前12个月只预热，以及MAD为0时使用尺度下限。这些条件决定一条记录何时有资格获得分数。')
p('<b>问题三，怎样核对图表和检出结果？</b>我的复核任务是让图1的七个债务催收入选点与候选清单逐月对应，并将表4与逐次模拟明细对账。例如，25%档94次入选可分为原已入选27次和新增67次。对同一位置增幅不同的情况，还应同时查看原计数、历史基线和排名，具体案例见第5节。')
table('表5　成员职责与本次参与说明',['成员','想解决的问题','对应工作与项目材料'],[
 ['孙永滔','题目如何落实为任务？','整理教师反馈并审核方案，确定产品月输入、前20条输出和后续比较条件。'],
 ['孙永滔','怎样验收AI生成的代码？','明确手算、时间窗口和边界检验要求，对应五段源码及本机32项测试日志。'],
 ['孙永滔','怎样评价增长识别能力？','确认四档配对注入和固定预算，要求以800条明细解释平均检出率。'],
 ['束琪遇','产品类别能跨月比较吗？','负责核对16字段、原标签和624行划分，结合新旧标签并存情况说明纳入范围。'],
 ['束琪遇','缺月和零值怎样处理？','负责检查缺月、历史不足和零波动规则，核对相应构造样例及边界测试。'],
 ['束琪遇','图表与入选比例是否对应？','负责逐月核对七个入选点，并用27次原已入选与67次新增核对94次命中。']], [.65,1.55,2.8])
table('表6　研究中的提示词与大模型协作记录',['编号','我们给 AI 的提示词','AI 给出的建议或采取的行动'],
      [[item['id'],item['prompt'],item['action']] for item in PROMPTS],[.34,2.45,2.21], long_table=True)
h('5　结论与展望')
p('六类产品两年共用20个复核名额，25%模拟增长有94/200次入选，100%增长有190/200次入选。以2024年6月车辆贷款或租赁为例，原计数946条低于历史中位数1,022条，增加237条后排名第46，增加473条后排名第18。同一位置能否入选，既取决于增长幅度，也取决于起点和历史波动。债务催收有七个月入选，部分月份相邻，一次持续增长可能占用多个名额。')
p('阶段三，我们将重点考察温和增长的漏选和相邻月份的重复入选。孙永滔负责实现可解释统计模型与孤立森林[5]，按相同预算和注入位置比较温和增长的检出情况，并做窗口敏感性分析。束琪遇负责核对各方法的时间边界，选择排名跨越前20名的配对案例，并在真实名单上标记连续月份。我们将共同整理方法比较表，记录不同方法对同一案例的判断，待参数确定后再用2025年保留测试期验收。')
p('系统集成时，我们将比较逐月复核与合并相邻线索的结果，同时记录节省的名额和可能遗漏的独立变化。文本覆盖和分类提示留待后续受控实验，公开材料采用聚合计数。')
page();h('参考文献')
refs=[
 '[1] Consumer Financial Protection Bureau. Consumer Complaint Database [DB/OL]. 2026-11-08. https://www.consumerfinance.gov/data-research/consumer-complaints/',
 '[2] Consumer Financial Protection Bureau. How we share complaint data [EB/OL]. 2026-11-08. https://www.consumerfinance.gov/complaint/data-use/',
 '[3] Dou Y, Roh Y. Public Disclosure and Consumer Financial Protection. Journal of Financial and Quantitative Analysis, 2024, 59(5), 2164–2198. DOI 10.1017/S0022109023000613. 文本公开的选择偏差见第2170页脚注10。',
 '[4] Python Software Foundation. statistics — Mathematical statistics functions [EB/OL]. 2026-11-08. https://docs.python.org/3/library/statistics.html',
 '[5] Liu F T, Ting K M, Zhou Z H. Isolation Forest. IEEE International Conference on Data Mining, 2008, 413–422. DOI 10.1109/ICDM.2008.17.'
]
for ref in refs:p(ref,small)


def footer(canvas,doc):
    canvas.saveState();canvas.setFont('CN2',9)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawCentredString(A4[0]/2,35,str(doc.page))
    canvas.restoreState()

report_name = '孙永滔_束琪遇_phase2_report.pdf'
if args.student_ids:
    report_name = f'{args.student_ids[0]}孙永滔_{args.student_ids[1]}束琪遇_phase2_report.pdf'
target=args.output_dir/report_name
doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=56.7,leftMargin=56.7,topMargin=56.7,bottomMargin=56.7,
                      title='金融产品月度投诉量的异常增长识别研究',author='孙永滔、束琪遇')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(args.output_dir/'报告2_可编辑稿.md').write_text('\n\n'.join(md),encoding='utf-8')
print(target)
