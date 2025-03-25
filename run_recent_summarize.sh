#!/bin/bash

# GovInfo 最近两天文档获取与摘要生成脚本
# 本脚本会获取FR(联邦公报)和BILLS(国会法案)中的最近两天文档，并生成摘要

# API密钥
GOVINFO_API_KEY="VL7fREaX90y0M1hz7NcF0i2BIvIoa3MwWhbPUP9o"
DEEPSEEK_API_KEY="sk-c448db32df6944eab2c8d5d9108ec158"

# 获取当前日期
TODAY_DATE=$(date +%Y%m%d)

# 为所有脚本添加执行权限
echo "为脚本添加执行权限..."
chmod +x get_recent_two_days_documents.py document_summarizer.py govinfo_summarize_recent.py

# 运行一体化工具
echo "===== 开始运行 ====="
echo "获取FR和BILLS集合中的最近两天文档并生成摘要"
python govinfo_summarize_recent.py --govinfo_api_key $GOVINFO_API_KEY --deepseek_api_key $DEEPSEEK_API_KEY --collections FR BILLS --page_size 100 --max_documents 200

# 完成
echo ""
echo "===== 运行完成 ====="
echo "1. 文档已保存到 recent_documents_${TODAY_DATE} 目录"
echo "2. 可以在document_summaries_${TODAY_DATE}.json中查看摘要内容"
echo "3. 可以在document_summaries_${TODAY_DATE}_report.md中查看格式化的摘要报告"
echo "4. 可以在recent_documents_${TODAY_DATE}/document_counts_report_${TODAY_DATE}.md中查看文档数量统计" 