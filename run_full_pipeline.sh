#!/bin/bash

# GovInfo 文档获取与摘要生成全流程脚本
# 本脚本会获取指定集合中的最近文档，生成摘要，并创建日期文件夹存放所有输出

# API密钥
GOVINFO_API_KEY="VL7fREaX90y0M1hz7NcF0i2BIvIoa3MwWhbPUP9o"
DEEPSEEK_API_KEY="sk-c448db32df6944eab2c8d5d9108ec158"

# 获取当前日期
TODAY_DATE=$(date +%Y%m%d)

# 创建日期文件夹
echo "创建日期文件夹: ${TODAY_DATE}"
mkdir -p "${TODAY_DATE}"

# 为所有脚本添加执行权限
echo "为脚本添加执行权限..."
chmod +x get_recent_two_days_documents.py document_summarizer.py govinfo_summarize_recent.py

# 运行一体化工具
echo "===== 开始运行 ====="
echo "获取FR和BILLS集合中的最近两天文档并生成摘要"
python govinfo_summarize_recent.py \
    --govinfo_api_key $GOVINFO_API_KEY \
    --deepseek_api_key $DEEPSEEK_API_KEY \
    --collections FR BILLS \
    --page_size 100 \
    --max_documents 200 \
    --output_dir "${TODAY_DATE}/recent_documents" \
    --summaries_file "${TODAY_DATE}/document_summaries.json"

# 完成
echo ""
echo "===== 运行完成 ====="
echo "所有输出文件已保存到 ${TODAY_DATE} 文件夹："
echo "1. 文档目录: ${TODAY_DATE}/recent_documents"
echo "2. 摘要文件: ${TODAY_DATE}/document_summaries.json"
echo "3. 摘要报告: ${TODAY_DATE}/document_summaries_report.md" 