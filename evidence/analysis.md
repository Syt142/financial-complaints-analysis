# 投诉数据自动分析报告

输入文件：`complaints.csv`；字节数：8,925,381,287。
已分析记录：**16,545,376**；范围：**全量**。
收件日期（UTC）：2011-12-01T00:00:00+00:00 至 2026-07-05T09:07:53+00:00。

## 数据质量

| 指标 | 记录数 |
| --- | ---: |
| invalid_received | 0 |
| invalid_sent | 0 |
| negative_forwarding_timestamp | 7,055 |
| negative_forwarding_calendar_day | 7,054 |
| missing_id | 2,390 |
| invalid_id | 0 |
| duplicate_id_extra_rows | 0 |
| unique_numeric_ids | 16,542,986 |

缺失仅指原始空字符串。重复ID仅作诊断，不自动删除对应记录。

| 字段 | 空值数 | 空值占比 |
| --- | ---: | ---: |
| Date received | 0 | 0.00% |
| Product | 121 | 0.00% |
| Sub-product | 235,415 | 1.42% |
| Issue | 151 | 0.00% |
| Sub-issue | 923,106 | 5.58% |
| Consumer complaint narrative | 12,730,795 | 76.94% |
| Company public response | 7,706,704 | 46.58% |
| Company | 0 | 0.00% |
| State | 62,097 | 0.38% |
| ZIP code | 1,612 | 0.01% |
| Tags | 15,765,213 | 95.28% |
| Submitted via | 0 | 0.00% |
| Date sent to company | 56,922 | 0.34% |
| Company response to consumer | 274,577 | 1.66% |
| Timely response? | 0 | 0.00% |
| Complaint ID | 2,390 | 0.01% |

## 年度分布

| 年份 | 记录数 |
| --- | ---: |
| 2011 | 2,536 |
| 2012 | 72,368 |
| 2013 | 108,214 |
| 2014 | 152,909 |
| 2015 | 168,273 |
| 2016 | 191,294 |
| 2017 | 242,745 |
| 2018 | 257,132 |
| 2019 | 277,241 |
| 2020 | 444,214 |
| 2021 | 495,939 |
| 2022 | 800,255 |
| 2023 | 1,292,060 |
| 2024 | 2,734,276 |
| 2025 | 5,443,266 |
| 2026 | 3,862,654 |

首尾年份及最新月份须按日期覆盖范围判断，不应直接与完整期间比较。
记录增长不能直接解释为客户投诉率或服务质量的变化。

## Product（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| Credit reporting or other personal consumer reports | 11,065,058 | 66.88% |
| Credit reporting, credit repair services, or other personal consumer reports | 2,163,773 | 13.08% |
| Debt collection | 1,162,407 | 7.03% |
| Mortgage | 455,102 | 2.75% |
| Checking or savings account | 381,725 | 2.31% |
| Credit card | 328,289 | 1.98% |
| Credit card or prepaid card | 206,357 | 1.25% |
| Money transfer, virtual currency, or money service | 185,456 | 1.12% |
| Credit reporting | 140,426 | 0.85% |
| Student loan | 130,363 | 0.79% |

## Issue（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| Incorrect information on your report | 7,329,427 | 44.30% |
| Improper use of your report | 3,190,803 | 19.29% |
| Problem with a company's investigation into an existing problem | 2,070,772 | 12.52% |
| Problem with a credit reporting company's investigation into an existing problem | 589,318 | 3.56% |
| Attempts to collect debt not owed | 465,028 | 2.81% |
| Written notification about debt | 224,602 | 1.36% |
| Managing an account | 223,064 | 1.35% |
| Took or threatened to take negative or legal action | 145,143 | 0.88% |
| False statements or representation | 117,768 | 0.71% |
| Loan modification,collection,foreclosure | 112,294 | 0.68% |

## Company（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| TRANSUNION INTERMEDIATE HOLDINGS, INC. | 4,429,776 | 26.77% |
| EQUIFAX, INC. | 4,349,398 | 26.29% |
| Experian Information Solutions Inc. | 3,948,159 | 23.86% |
| BANK OF AMERICA, NATIONAL ASSOCIATION | 182,548 | 1.10% |
| JPMORGAN CHASE & CO. | 171,437 | 1.04% |
| WELLS FARGO & COMPANY | 171,191 | 1.03% |
| CAPITAL ONE FINANCIAL CORPORATION | 166,666 | 1.01% |
| CITIBANK, N.A. | 137,479 | 0.83% |
| SYNCHRONY FINANCIAL | 81,290 | 0.49% |
| Resurgent Capital Services L.P. | 70,651 | 0.43% |

## State（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| FL | 2,261,339 | 13.67% |
| TX | 2,251,618 | 13.61% |
| CA | 1,649,238 | 9.97% |
| GA | 1,222,083 | 7.39% |
| NY | 965,780 | 5.84% |
| IL | 708,745 | 4.28% |
| PA | 652,769 | 3.95% |
| NC | 566,596 | 3.42% |
| NJ | 529,336 | 3.20% |
| MD | 409,813 | 2.48% |

## Submitted via（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| Web | 15,913,020 | 96.18% |
| Referral | 277,047 | 1.67% |
| Phone | 218,731 | 1.32% |
| Postal mail | 110,491 | 0.67% |
| Fax | 25,644 | 0.15% |
| Email | 443 | 0.00% |

## Company response to consumer（前十）

| 原始标签 | 记录数 | 占全部记录 |
| --- | ---: | ---: |
| Closed with explanation | 9,922,403 | 59.97% |
| Closed with non-monetary relief | 5,483,473 | 33.14% |
| In progress | 582,672 | 3.52% |
| （空值） | 274,577 | 1.66% |
| Closed with monetary relief | 211,193 | 1.28% |
| Untimely response | 30,276 | 0.18% |
| Closed without relief | 17,867 | 0.11% |
| Closed | 17,611 | 0.11% |
| Closed with relief | 5,304 | 0.03% |

## 指标口径

- timely_response：16,442,371 / 16,545,376 = 99.38%。Yes / (Yes + No); not a resolution rate
- narrative_coverage：3,814,581 / 16,545,376 = 23.06%。nonempty narrative / all records

及时回应不是解决率；转交日期差不是企业处理时长；投诉记录不是独立消费者。
产品和问题保留原标签，历史分类未统一；公司排名不考虑客户量。
公开文本为空不等于消费者没有填写叙述。程序没有执行因果分析或训练AI模型。

总量与ID分区校验：21/21 项通过。
扫描耗时：358.075秒。内存测量口径及环境见summary.json。
