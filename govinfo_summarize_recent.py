#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import os
import time
import sys
import json
import datetime

def run_command(command, description=None):
    """运行命令并显示输出"""
    if description:
        print(f"\n{'=' * 80}")
        print(f"正在{description}...")
        print(f"{'=' * 80}\n")
        sys.stdout.flush()  # 确保描述信息立即显示
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True
        )
        
        # 实时显示输出
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end='', flush=True)  # 立即刷新输出
        
        process.wait()
        
        if process.returncode != 0:
            print(f"命令执行失败，返回代码: {process.returncode}")
            return False
        
        return True
    
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False

def ensure_dependencies():
    """确保所有依赖已安装"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("正在安装必要的依赖...")
        run_command(['pip', 'install', 'requests', 'beautifulsoup4'], "安装依赖")
        print("依赖安装完成")

def count_documents_by_collection(output_dir):
    """统计每个集合的文档数量并生成报告"""
    counts = {}
    details = {}
    
    # 计算文档数量
    for item in os.listdir(output_dir):
        if os.path.isdir(os.path.join(output_dir, item)) and not item.startswith('.'):
            collection_path = os.path.join(output_dir, item)
            detail_files = [f for f in os.listdir(collection_path) if f.endswith('_details.json') and not '_granules_' in f]
            
            # 获取每个文档的日期信息
            doc_dates = {}
            for detail_file in detail_files:
                try:
                    with open(os.path.join(collection_path, detail_file), 'r', encoding='utf-8') as f:
                        doc_info = json.load(f)
                        date_issued = doc_info.get('dateIssued')
                        if date_issued:
                            if date_issued not in doc_dates:
                                doc_dates[date_issued] = 0
                            doc_dates[date_issued] += 1
                except:
                    pass
            
            counts[item] = len(detail_files)
            details[item] = doc_dates
    
    # 获取当前日期作为文件名的一部分
    today_date = datetime.datetime.now().strftime('%Y%m%d')
    
    # 生成报告
    report_file = os.path.join(output_dir, f'document_counts_report_{today_date}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# GovInfo 文档数量统计报告\n\n")
        f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_docs = sum(counts.values())
        f.write(f"总文档数量: {total_docs}\n\n")
        
        f.write("## 按集合统计\n\n")
        f.write("| 集合 | 文档数量 |\n")
        f.write("| ---- | -------- |\n")
        
        for collection, count in counts.items():
            f.write(f"| {collection} | {count} |\n")
        
        f.write("\n## 按日期详细统计\n\n")
        
        for collection, date_counts in details.items():
            f.write(f"### {collection}\n\n")
            f.write("| 日期 | 文档数量 |\n")
            f.write("| ---- | -------- |\n")
            
            for date, count in sorted(date_counts.items(), reverse=True):
                f.write(f"| {date} | {count} |\n")
            
            f.write("\n")
    
    print(f"文档统计报告已生成: {report_file}")
    return counts, details, today_date

def main():
    parser = argparse.ArgumentParser(description='GovInfo最近两天文档获取与摘要生成一体化工具')
    parser.add_argument('--govinfo_api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--deepseek_api_key', required=True, help='DeepSeek API密钥')
    parser.add_argument('--collections', nargs='+', default=['FR', 'BILLS', 'CREC'], 
                       help='要查询的集合代码列表，默认为FR, BILLS, CREC')
    parser.add_argument('--page_size', type=int, default=100, help='每页结果数，默认为100')
    parser.add_argument('--output_dir', default='recent_documents', help='输出目录，默认为recent_documents')
    parser.add_argument('--summaries_file', default='document_summaries.json', help='摘要输出文件，默认为document_summaries.json')
    parser.add_argument('--max_documents', type=int, default=1000, help='每个集合最多处理的文档数量，默认为1000')
    parser.add_argument('--skip_download', action='store_true', help='跳过下载步骤，直接生成摘要')
    parser.add_argument('--skip_summary', action='store_true', help='跳过摘要生成步骤，只下载文档')
    parser.add_argument('--report_only', action='store_true', help='只生成报告，不下载也不生成摘要')
    parser.add_argument('--threads', type=int, default=5, help="并发线程数，默认为5")
    parser.add_argument('--chunk_size', type=int, default=8000, help="文本块大小，默认为8000字符")
    parser.add_argument('--api_delay', type=float, default=0.5, help="API调用之间的延迟时间（秒），默认为0.5秒")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 确保依赖已安装
    ensure_dependencies()
    
    # 获取当前日期作为文件名的一部分
    today_date = datetime.datetime.now().strftime('%Y%m%d')
    
    if args.report_only:
        # 只生成报告
        counts, details, _ = count_documents_by_collection(args.output_dir)
        
        report_cmd = [
            'python', 'document_summarizer.py',
            '--api_key', args.govinfo_api_key,
            '--input_dir', args.output_dir,
            '--output_file', args.summaries_file,
            '--report',
            '--threads', str(args.threads),
            '--chunk_size', str(args.chunk_size),
            '--api_delay', str(args.api_delay)
        ]
        run_command(report_cmd, "生成摘要报告")
        
        end_time = time.time()
        print(f"\n总耗时: {(end_time - start_time) / 60:.2f} 分钟")
        return
    
    if not args.skip_download:
        # 修改document_summarizer.py中的DeepSeek API密钥
        try:
            with open('document_summarizer.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换API密钥
            content = content.replace('DEEPSEEK_API_KEY = "sk-c448db32df6944eab2c8d5d9108ec158"', 
                                     f'DEEPSEEK_API_KEY = "{args.deepseek_api_key}"')
            
            with open('document_summarizer.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("已更新DeepSeek API密钥")
        except Exception as e:
            print(f"更新DeepSeek API密钥时出错: {e}")
        
        # 创建输出目录
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        
        # 下载文档
        download_cmd = [
            'python', 'get_recent_two_days_documents.py',
            '--api_key', args.govinfo_api_key,
            '--output_dir', args.output_dir,
            '--page_size', str(args.page_size),
            '--max_documents', str(args.max_documents)
        ]
        
        # 添加集合参数
        if args.collections:
            download_cmd.extend(['--collections'] + args.collections)
        
        success = run_command(download_cmd, "获取GovInfo最近两天的文档")
        
        if not success:
            print("文档获取失败，程序终止")
            return
        
        # 生成统计报告
        counts, details, _ = count_documents_by_collection(args.output_dir)
    else:
        print("已跳过文档下载步骤")
    
    if not args.skip_summary:
        # 生成摘要
        summary_cmd = [
            'python', 'document_summarizer.py',
            '--api_key', args.govinfo_api_key,
            '--input_dir', args.output_dir,
            '--output_file', args.summaries_file,
            '--threads', str(args.threads),
            '--chunk_size', str(args.chunk_size),
            '--api_delay', str(args.api_delay)
        ]
        
        success = run_command(summary_cmd, "生成文档摘要")
        
        if not success:
            print("摘要生成失败")
        else:
            print(f"摘要文件已保存为: {args.summaries_file}")
            
            # 获取摘要报告文件名
            summary_report = os.path.splitext(args.summaries_file)[0] + "_report.md"
            print(f"摘要报告已保存为: {summary_report}")
    else:
        print("已跳过摘要生成步骤")
    
    end_time = time.time()
    print(f"\n总耗时: {(end_time - start_time) / 60:.2f} 分钟")
    
    # 打印文件名信息
    print("\n===== 输出文件信息 =====")
    print(f"1. 文档目录: {args.output_dir}")
    print(f"2. 摘要文件: {args.summaries_file}")
    print(f"3. 摘要报告: {os.path.splitext(args.summaries_file)[0]}_report.md")
    print(f"4. 文档统计报告: {args.output_dir}/document_counts_report_{today_date}.md")

if __name__ == "__main__":
    main() 
