#!/bin/bash

# GovInfo API 文档获取与摘要生成示例脚本
# 本脚本会获取FR(联邦公报)和BILLS(国会法案)中的最近文档，并生成摘要

# GovInfo API密钥
API_KEY="VL7fREaX90y0M1hz7NcF0i2BIvIoa3MwWhbPUP9o"

# 创建一个简短的示例
echo "===== 运行简短示例 ====="
echo "获取FR和BILLS集合中的最近文档（每个集合3条）并生成摘要"
python generate_govinfo_summaries.py --api_key $API_KEY --collections FR BILLS --page_size 3

# 完成
echo ""
echo "===== 示例运行完成 ====="
echo "可以在document_summaries.json中查看摘要内容"
echo "可以在document_summaries_report.md中查看格式化的摘要报告" 