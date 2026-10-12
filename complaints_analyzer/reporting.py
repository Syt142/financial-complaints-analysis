"""Produce a human-readable report using only aggregate values."""
def make_markdown(r):
    n=r['rows'];f=r['frequencies']
    percent=lambda x,d: f'{100*x/d:.2f}%' if d else '不可计算'
    lines=['# 投诉数据自动分析报告','',
        f'输入文件：`{r["source"]["file_name"]}`；字节数：{r["source"]["bytes"]:,}。',
        f'已分析记录：**{n:,}**；范围：**{"全量" if r["run"]["complete_file"] else "限定前若干条，不能代表全量"}**。',
        f'收件日期（UTC）：{r["min_received"]} 至 {r["max_received"]}。','',
        '## 数据质量','',
        '| 指标 | 记录数 |','| --- | ---: |']
    lines += [f'| {k} | {v:,} |' for k,v in r['quality'].items()]
    lines += ['', '缺失仅指原始空字符串。重复ID仅作诊断，不自动删除对应记录。','',
        '| 字段 | 空值数 | 空值占比 |','| --- | ---: | ---: |']
    lines += [f'| {k} | {v:,} | {percent(v,n)} |' for k,v in r['missing'].items()]
    lines += ['','## 年度分布','','| 年份 | 记录数 |','| --- | ---: |']
    lines += [f'| {k} | {v:,} |' for k,v in sorted(f['year'].items())]
    lines += ['','首尾年份及最新月份须按日期覆盖范围判断，不应直接与完整期间比较。',
              '记录增长不能直接解释为客户投诉率或服务质量的变化。','']
    for col in ['Product','Issue','Company','State','Submitted via','Company response to consumer']:
        lines += [f'## {col}（前十）','','| 原始标签 | 记录数 | 占全部记录 |','| --- | ---: | ---: |']
        for k,v in list(f[col].items())[:10]:
            label=(k or '（空值）').replace('|','\\|').replace('\n',' ')
            lines.append(f'| {label} | {v:,} | {percent(v,n)} |')
        lines.append('')
    lines += ['## 指标口径','']
    for name,m in r['metrics'].items():
        lines.append(f'- {name}：{m["numerator"]:,} / {m["denominator"]:,} = {percent(m["numerator"],m["denominator"])}。{m["definition"]}')
    lines += ['','及时回应不是解决率；转交日期差不是企业处理时长；投诉记录不是独立消费者。',
        '产品和问题保留原标签，历史分类未统一；公司排名不考虑客户量。',
        '公开文本为空不等于消费者没有填写叙述。程序没有执行因果分析或训练AI模型。','',
        f'总量与ID分区校验：{sum(r["checks"].values())}/{len(r["checks"])} 项通过。',
        f'扫描耗时：{r["run"]["elapsed_seconds"]}秒。内存测量口径及环境见summary.json。']
    return '\n'.join(lines)+'\n'
