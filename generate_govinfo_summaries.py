#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import os
import time
import sys

def run_command(command, description=None):
    """运行命令并显示输出"""
    if description:
        print(f"\n{'=' * 80}")
        print(f"正在{description}...")
        print(f"{'=' * 80}\n")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时显示输出
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode != 0:
            print(f"命令执行失败，返回代码: {process.returncode}")
            return False
        
        return True
    
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='GovInfo文档获取与摘要生成一体化工具')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--collections', nargs='+', default=['FR', 'BILLS', 'CREC'], 
                       help='要查询的集合代码列表，默认为FR, BILLS, CREC')
    parser.add_argument('--page_size', type=int, default=5, help='每页结果数，默认为5')
    parser.add_argument('--output_dir', default='recent_documents', help='输出目录，默认为recent_documents')
    parser.add_argument('--summaries_file', default='document_summaries.json', help='摘要输出文件，默认为document_summaries.json')
    parser.add_argument('--skip_download', action='store_true', help='跳过下载步骤，直接生成摘要')
    parser.add_argument('--skip_summary', action='store_true', help='跳过摘要生成步骤，只下载文档')
    parser.add_argument('--report_only', action='store_true', help='只生成报告，不下载也不生成摘要')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    if args.report_only:
        # 只生成报告
        report_cmd = [
            'python', 'document_summarizer.py',
            '--api_key', args.api_key,
            '--input_dir', args.output_dir,
            '--output_file', args.summaries_file,
            '--report'
        ]
        run_command(report_cmd, "生成摘要报告")
        
        end_time = time.time()
        print(f"\n总耗时: {(end_time - start_time) / 60:.2f} 分钟")
        return
    
    if not args.skip_download:
        # 下载文档
        download_cmd = [
            'python', 'get_recent_documents.py',
            '--api_key', args.api_key,
            '--output_dir', args.output_dir,
            '--page_size', str(args.page_size)
        ]
        
        # 添加集合参数
        if args.collections:
            download_cmd.extend(['--collections'] + args.collections)
        
        success = run_command(download_cmd, "获取GovInfo文档")
        
        if not success:
            print("文档获取失败，程序终止")
            return
    else:
        print("已跳过文档下载步骤")
    
    if not args.skip_summary:
        # 生成摘要
        summary_cmd = [
            'python', 'document_summarizer.py',
            '--api_key', args.api_key,
            '--input_dir', args.output_dir,
            '--output_file', args.summaries_file
        ]
        
        success = run_command(summary_cmd, "生成文档摘要")
        
        if not success:
            print("摘要生成失败")
    else:
        print("已跳过摘要生成步骤")
    
    end_time = time.time()
    print(f"\n总耗时: {(end_time - start_time) / 60:.2f} 分钟")

if __name__ == "__main__":
    main() 