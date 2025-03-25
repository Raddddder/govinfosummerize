# GovInfo API 文档获取工具

这个工具可以帮助您获取GovInfo API中最近一周的文档信息，并保存为JSON格式。此外，还能使用DeepSeek AI为这些文档生成摘要。

## 功能

- 获取GovInfo API中的所有集合信息
- 查询指定集合中最近一周更新的文档
- 获取文档的详细信息和子条目
- 将所有信息保存为JSON文件
- 使用DeepSeek AI为文档生成摘要
- 支持断点续传和进度保存
- 生成可读性强的摘要报告

## 安装依赖

```bash
pip install requests beautifulsoup4
```

## 使用方法

### 快速开始(推荐)

使用集成脚本一次性完成所有操作：

```bash
python generate_govinfo_summaries.py --api_key YOUR_API_KEY
```

### 分步执行

如果您希望分步执行，可以按以下步骤操作：

#### 1. 获取文档

首先获取最近一周的文档信息：

```bash
python get_recent_documents.py --api_key YOUR_API_KEY
```

#### 2. 生成摘要

然后使用DeepSeek AI为获取的文档生成摘要：

```bash
python document_summarizer.py --api_key YOUR_API_KEY
```

#### 3. 只生成报告

如果您已经生成了摘要，但只想重新生成报告：

```bash
python document_summarizer.py --api_key YOUR_API_KEY --report
```

### 参数说明

#### generate_govinfo_summaries.py 参数(集成脚本)：

- `--api_key`：（必需）您的GovInfo API密钥
- `--collections`：（可选）要查询的集合代码列表，默认为`FR BILLS CREC`
- `--page_size`：（可选）每页结果数，默认为5
- `--output_dir`：（可选）输出目录，默认为`recent_documents`
- `--summaries_file`：（可选）摘要输出文件，默认为`document_summaries.json`
- `--skip_download`：（可选）跳过下载步骤，直接生成摘要
- `--skip_summary`：（可选）跳过摘要生成步骤，只下载文档
- `--report_only`：（可选）只生成报告，不下载也不生成摘要

#### get_recent_documents.py 参数：

- `--api_key`：（必需）您的GovInfo API密钥
- `--collections`：（可选）要查询的集合代码列表，默认为`FR BILLS CREC`
- `--page_size`：（可选）每页结果数，默认为10
- `--output_dir`：（可选）输出目录，默认为`recent_documents`

#### document_summarizer.py 参数：

- `--api_key`：（必需）您的GovInfo API密钥
- `--input_dir`：（可选）输入目录，默认为`recent_documents`
- `--output_file`：（可选）输出文件，默认为`document_summaries.json`
- `--report`：（可选）是否只生成报告而不处理新文档

### 示例

一次性完成所有操作，获取联邦公报(FR)和国会记录(CREC)的最近文档并生成摘要：

```bash
python generate_govinfo_summaries.py --api_key YOUR_API_KEY --collections FR CREC
```

跳过下载，只为已有文档生成摘要：

```bash
python generate_govinfo_summaries.py --api_key YOUR_API_KEY --skip_download
```

只下载文档，不生成摘要：

```bash
python generate_govinfo_summaries.py --api_key YOUR_API_KEY --skip_summary
```

只生成摘要报告：

```bash
python generate_govinfo_summaries.py --api_key YOUR_API_KEY --report_only
```

## 文档摘要处理流程

document_summarizer.py 脚本的处理流程如下：

1. 读取get_recent_documents.py生成的文档信息
2. 获取每个文档的HTML内容
3. 清理HTML，提取纯文本
4. 将文本分成适合AI处理的小块
5. 使用DeepSeek AI为每个块生成摘要
6. 如果文档有多个块，再生成一个综合摘要
7. 将所有文档的摘要保存到JSON文件
8. 生成可读性强的Markdown格式摘要报告

## 断点续传

本工具支持断点续传，即使处理过程中中断，重新运行时会自动跳过已处理的文档，继续处理未完成的文档。同时，脚本会定期保存处理进度，确保不会丢失已完成的工作。

## 输出文件

### get_recent_documents.py 输出:

- `collections.json`：所有可用的集合信息
- `{集合代码}_documents.json`：每个集合的文档列表
- `{集合代码}/{包ID}_details.json`：每个文档的详细信息
- `{集合代码}/{包ID}_granules.json`：每个文档的子条目列表
- `{集合代码}/{包ID}_{子条目ID}_details.json`：每个子条目的详细信息

### document_summarizer.py 输出:

- `document_summaries.json`：包含所有文档摘要的JSON文件
- `document_summaries_report.md`：可读性强的摘要报告，包含所有文档的摘要信息
- `.cache/`：缓存目录，包含下载的HTML内容，便于出错时恢复

## 集合代码说明

GovInfo API包含多个集合，常用的集合代码包括：

- `FR`：联邦公报 (Federal Register)
- `BILLS`：国会法案 (Congressional Bills)
- `CREC`：国会记录 (Congressional Record)
- `USCOURTS`：美国法院意见 (United States Courts Opinions)
- `GAOREPORTS`：政府问责局报告 (Government Accountability Office Reports)

完整的集合列表可以通过`collections.json`文件查看。

## 注意事项

- 为了减少API请求次数，get_recent_documents.py脚本默认只获取每个集合中的前3个文档的详细信息
- GovInfo API可能有请求频率限制，如果遇到限制，请减少请求频率或使用更小的`page_size`
- DeepSeek API也有使用限制，脚本设置了1秒的延迟，但可能仍需调整
- 处理大型文档可能需要较长时间，脚本会定期保存进度，即使中断也可以从中断处恢复
- 脚本会缓存下载的HTML内容，以便于出错时不需要重新下载 