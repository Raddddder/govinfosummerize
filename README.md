# GovInfo API 文档获取工具

这个工具可以帮助您获取GovInfo API中最近两天的文档信息，并保存为JSON格式。此外，还能使用DeepSeek AI为这些文档生成摘要。
### FR (Federal Register)：联邦公报
这是美国联邦政府的官方日报
相关链接：https://www.federalregister.gov/
用于发布行政命令、政府机构规章制度和其他联邦机构的官方文件
### BILLS：国会法案
这是美国国会提出的法案
相关链接
包含由国会议员提出的各种立法提案
这两个集合代表了美国联邦政府两个不同层面的法律文件：
FR反映的是行政部门的规章制度和行政命令
BILLS反映的是立法部门（国会）的立法活动
这些都是GovInfo API中最常用的文档集合之一，对于跟踪美国联邦政府的政策变化和立法动态非常重要。
## 功能

- 获取GovInfo API中的所有集合信息
- 查询指定集合中最近两天更新的文档（特别是FR和BILLS）
- 获取文档的详细信息和子条目
- 将所有信息保存为JSON文件
- 使用DeepSeek AI为文档生成摘要
- 支持断点续传和进度保存
- 生成可读性强的摘要报告
- 所有输出文件名自动添加日期标记
# 「TODO」
1.修改获取的时间窗口（2天改为1天）
2.针对生成的5000页的法案内容进行【基于prompt】的筛选
3.【基于prompt】内容包括：
（待验证）居于单一文本的：
```
As an analyst, evaluate the given text source regarding its relationship to US data restrictions based on three dimensions. Please analyze the content and provide a structured assessment in the following format:

1. Urgency Level (P0/P1/P2):
- Analyze the text's immediacy and criticality regarding data restrictions
- P0: Immediate/Critical
- P1: Medium Priority
- P2: Low Priority/Long-term

2. Impact Scope:
- Assess whether the impact is:
  * US Internal
  * Global Range
  * China Specific

3. Domain Area:
- Identify which sector is primarily affected:
  * Healthcare & Medical
  * Economy & Industry
  * Society & Human Factors

Additionally, scan for key terminology related to data restrictions:
- Data/Data Security
- Data Limit
- AI Safety
- Digital Security
- Data Protection
- Intellectual Property

Please provide the analysis results in the following JSON format:

{
    "urgency_level": "P0/P1/P2",
    "impact_scope": "US_Internal/Global/China_Specific",
    "domain_area": "Healthcare/Economy/Society",
    "key_terms_detected": [
        {
            "term": "term_name",
            "frequency": number,
            "context": "brief_context"
        }
    ],
    "summary": "brief_analysis_of_data_restriction_implications"
}

Note: Only include key terms if they are actually present in the text.
 ```
(待验证)基于多信源在内需要筛选的：
```
As an analyst, evaluate a collection of text sources and identify those specifically related to US data restrictions. For each relevant source within the input text:

1. First, determine if the source contains content related to data restrictions by checking:
- Data control or limitation policies
- Data security measures
- Cross-border data flow restrictions
- Technology access controls
- Digital sovereignty issues

For each RELEVANT source only, provide a detailed analysis based on three dimensions:

1. Urgency Level (P0/P1/P2):
- P0: Immediate/Critical impact on data access/control
- P1: Medium-term implications for data policies
- P2: Long-term/potential future impacts

2. Impact Scope:
- US Internal
- Global Range
- China Specific

3. Domain Area:
- Healthcare & Medical
- Economy & Industry
- Society & Human Factors

Key terminology scan for each source:
- Data/Data Security
- Data Limit
- AI Safety
- Digital Security
- Data Protection
- Intellectual Property

Please provide the results in the following JSON format:

{
    "relevant_sources": [
        {
            "source_id": "sequential_number",
            "source_excerpt": "brief_quote_or_identifier",
            "analysis": {
                "urgency_level": "P0/P1/P2",
                "impact_scope": "US_Internal/Global/China_Specific",
                "domain_area": "Healthcare/Economy/Society",
                "key_terms_detected": [
                    {
                        "term": "term_name",
                        "frequency": number,
                        "context": "brief_context"
                    }
                ]
            },
            "summary": "brief_analysis_of_data_restriction_implications"
        }
    ],
    "total_relevant_sources": number,
    "analysis_timestamp": "timestamp"
}

Important notes:
1. Only include sources that specifically relate to data restrictions or controls
2. Exclude sources that don't contain relevant content
3. Maintain clear separation between different sources in the analysis
4. Provide context for why each included source is relevant

```
## 安装依赖

```bash
pip install requests beautifulsoup4
```

## 快速启动（推荐）

直接运行提供的shell脚本即可一键获取最近两天的FR和BILLS文档，并生成摘要：

```bash
./run_full_pipeline.sh
```

该脚本会自动：
1. 获取最近两天的FR和BILLS文档
2. 生成摘要和报告
3. 所有输出文件名中加入当天日期，方便管理

## 输出文件

脚本运行后会生成以下带日期标记的文件（YYYYMMDD表示运行日期）：

- `recent_documents_YYYYMMDD/`：包含所有下载的文档和子条目信息
- `document_summaries_YYYYMMDD.json`：包含所有文档摘要的JSON文件
- `document_summaries_YYYYMMDD_report.md`：格式化的摘要报告
- `recent_documents_YYYYMMDD/document_counts_report_YYYYMMDD.md`：文档数量统计报告

## 文档摘要处理流程

document_summarizer.py 脚本的处理流程如下：

1. 读取文档目录中的信息
2. 获取每个文档的HTML内容
3. 清理HTML，提取纯文本
4. 将文本分成适合AI处理的小块
5. 使用DeepSeek AI为每个块生成摘要
6. 如果文档有多个块，再生成一个综合摘要
7. 将所有文档的摘要保存到JSON文件
8. 生成可读性强的Markdown格式摘要报告

## 断点续传

本工具支持断点续传，即使处理过程中中断，重新运行时会自动跳过已处理的文档，继续处理未完成的文档。同时，脚本会定期保存处理进度，确保不会丢失已完成的工作。

## 高级用法

如果需要更精细的控制，可以直接使用以下脚本：

### 获取最近两天文档

```bash
python get_recent_two_days_documents.py --api_key YOUR_API_KEY --collections FR BILLS --page_size 100 --max_documents 200
```

### 生成摘要

```bash
python document_summarizer.py --api_key YOUR_API_KEY --input_dir recent_documents_YYYYMMDD --output_file document_summaries_YYYYMMDD.json
```

### 一体化执行

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --collections FR BILLS --page_size 100 --max_documents 200
```

### 只生成报告

如果您已经生成了摘要，但只想重新生成报告：

```bash
python document_summarizer.py --api_key YOUR_API_KEY --input_dir recent_documents_YYYYMMDD --output_file document_summaries_YYYYMMDD.json --report
```

### 只更新统计报告

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --report_only
```

## 参数说明

### get_recent_two_days_documents.py 参数

- `--api_key`：（必需）您的GovInfo API密钥
- `--collections`：（可选）要查询的集合代码列表，默认为`FR, BILLS, CREC`
- `--page_size`：（可选）每页结果数，默认为100
- `--output_dir`：（可选）输出目录，默认为`recent_documents`
- `--max_documents`：（可选）每个集合最多处理的文档数量，默认为1000

### document_summarizer.py 参数

- `--api_key`：（必需）您的GovInfo API密钥
- `--input_dir`：（可选）输入目录，默认为`recent_documents`
- `--output_file`：（可选）输出文件，默认为`document_summaries.json`
- `--report`：（可选）是否只生成报告而不处理新文档

### govinfo_summarize_recent.py 参数

- `--govinfo_api_key`：（必需）您的GovInfo API密钥
- `--deepseek_api_key`：（必需）您的DeepSeek API密钥
- `--collections`：（可选）要查询的集合代码列表，默认为`FR, BILLS, CREC`
- `--page_size`：（可选）每页结果数，默认为100
- `--output_dir`：（可选）输出目录，默认为`recent_documents`（会自动添加日期）
- `--summaries_file`：（可选）摘要输出文件，默认为`document_summaries.json`（会自动添加日期）
- `--max_documents`：（可选）每个集合最多处理的文档数量，默认为1000
- `--skip_download`：（可选）跳过下载步骤，直接生成摘要
- `--skip_summary`：（可选）跳过摘要生成步骤，只下载文档
- `--report_only`：（可选）只生成报告，不下载也不生成摘要

## 集合代码说明

GovInfo API包含多个集合，常用的集合代码包括：

- `FR`：联邦公报 (Federal Register)
- `BILLS`：国会法案 (Congressional Bills)
- `CREC`：国会记录 (Congressional Record)
- `USCOURTS`：美国法院意见 (United States Courts Opinions)
- `GAOREPORTS`：政府问责局报告 (Government Accountability Office Reports)

完整的集合列表可以通过`collections.json`文件查看。

## 注意事项

- GovInfo API可能有请求频率限制，脚本设置了延迟避免超出限制
- DeepSeek API也有使用限制，脚本设置了1秒的延迟
- 处理大型文档可能需要较长时间，脚本会定期保存进度，即使中断也可以从中断处恢复
- 脚本会缓存下载的HTML内容，以便于出错时不需要重新下载
- 所有输出文件都带有日期标记，方便管理不同日期生成的文件

## 示例用法

### 获取FR和BILLS两天内的全部文档并生成摘要

```bash
./run_recent_summarize.sh
```

### 自定义处理特定集合

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --collections FR CREC --page_size 50 --max_documents 100
```

### 跳过下载，只为已有文档生成摘要

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --skip_download
```

### 只下载文档，不生成摘要

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --skip_summary
```

### 只生成统计和摘要报告

```bash
python govinfo_summarize_recent.py --govinfo_api_key YOUR_GOVINFO_API_KEY --deepseek_api_key YOUR_DEEPSEEK_API_KEY --report_only
``` 
example：
python document_summarizer.py --api_key sk-c448db32df6944eab2c8d5d9108ec158 --input_dir recent_documents_20250325 --output_file document_summaries_20250325.json --report
