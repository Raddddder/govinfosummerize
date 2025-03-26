#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import requests
import datetime
import sys
import time
from bs4 import BeautifulSoup
import concurrent.futures
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 全局变量声明
MAX_WORKERS = 10  # 用于多线程API请求的并发数量
BATCH_SIZE = 5    # 每批处理的文档数量
API_DELAY = 0.2   # API调用之间的延迟时间（秒）
DEEPSEEK_API_KEY = "sk-c448db32df6944eab2c8d5d9108ec158"  # DeepSeek API密钥
file_lock = threading.Lock()  # 线程锁，用于保护文件写入

def get_html_content(package_id, granule_id, api_key):
    """获取文档的HTML内容"""
    url = f"https://api.govinfo.gov/packages/{package_id}/granules/{granule_id}/htm?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"获取HTML内容失败: {response.status_code}")
        return None

def clean_html_content(html_content):
    """清理HTML内容，提取纯文本"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    # 移除script和style元素
    for script in soup(["script", "style"]):
        script.extract()
    
    # 获取文本
    text = soup.get_text()
    
    # 清理文本
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def split_text_into_chunks(text, max_chunk_size=8000):
    """将文本分割成适合AI处理的小块（增大到8000字符）"""
    if not text:
        return []
    
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        if current_size + len(word) + 1 > max_chunk_size:  # +1 for the space
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for the space
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def call_deepseek_api(prompt, temperature=0.3, max_tokens=800):
    """调用DeepSeek API生成摘要"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"DeepSeek API调用失败: {response.status_code}")
            print(response.text)
            return f"无法生成摘要，API错误: {response.status_code}"
    
    except Exception as e:
        print(f"调用DeepSeek API时出错: {e}")
        return f"无法生成摘要，错误: {str(e)}"

def process_chunk(i, chunk, total_chunks, doc_info_text=""):
    """处理单个文本块，生成摘要"""
    print(f"处理第 {i+1}/{total_chunks} 块内容...")
    
    # 构建每个块的提示
    if i == 0 and doc_info_text:
        # 第一个块包含文档信息
        prompt = f"{doc_info_text}请对以下政府文档内容生成一个简洁但详实的摘要。这是文档的第 {i+1}/{total_chunks} 部分：\n\n{chunk}"
    else:
        # 后续块
        prompt = f"请继续分析这个政府文档的第 {i+1}/{total_chunks} 部分并生成摘要：\n\n{chunk}"
    
    # 调用DeepSeek API
    summary = call_deepseek_api(prompt)
    
    # 延迟以避免API限制
    time.sleep(API_DELAY)
    
    return summary

def get_deepseek_summary(text_chunks, document_info):
    """使用DeepSeek API生成摘要（多线程版本）"""
    # 构建提示
    if not text_chunks:
        return "无法生成摘要：没有有效的文本内容。"
    
    # 构建文档信息描述
    doc_info_text = f"文档标题: {document_info.get('title', '未知')}\n"
    doc_info_text += f"文档ID: {document_info.get('packageId', '未知')}\n"
    doc_info_text += f"发布日期: {document_info.get('dateIssued', '未知')}\n"
    doc_info_text += f"集合: {document_info.get('collectionName', '未知')}\n\n"
    
    # 如果只有一个文本块，直接处理
    if len(text_chunks) == 1:
        return process_chunk(0, text_chunks[0], 1, doc_info_text)
    
    # 使用线程池并行生成摘要
    all_summaries = [None] * len(text_chunks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(text_chunks))) as executor:
        # 提交任务到线程池
        futures = []
        for i, chunk in enumerate(text_chunks):
            future = executor.submit(
                process_chunk, 
                i, 
                chunk, 
                len(text_chunks),
                doc_info_text if i == 0 else ""
            )
            futures.append((future, i))
        
        # 获取结果
        for future, i in futures:
            try:
                all_summaries[i] = future.result()
            except Exception as e:
                print(f"处理第 {i+1} 块时出错: {e}")
                all_summaries[i] = f"无法生成此部分的摘要，错误: {str(e)}"
    
    # 移除None值
    all_summaries = [s for s in all_summaries if s]
    
    # 如果有多个块，再生成一个综合摘要
    if len(all_summaries) > 1:
        print("生成综合摘要...")
        combined_summary = "\n\n".join(all_summaries)
        
        # 如果综合摘要太长，可能需要再次分块处理
        combined_chunks = split_text_into_chunks(combined_summary, 10000)
        
        # 并行处理综合摘要
        final_summaries = [None] * len(combined_chunks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(combined_chunks))) as executor:
            futures = []
            for i, c_chunk in enumerate(combined_chunks):
                prompt = f"请基于以下多个摘要片段，为这份政府文档生成一个连贯、全面但简洁的整体摘要。这是第 {i+1}/{len(combined_chunks)} 部分的摘要集合：\n\n{c_chunk}"
                future = executor.submit(call_deepseek_api, prompt, 0.3, 1000)
                futures.append((future, i))
            
            for future, i in futures:
                try:
                    final_summaries[i] = future.result()
                    time.sleep(API_DELAY)
                except Exception as e:
                    print(f"处理综合摘要第 {i+1} 块时出错: {e}")
                    final_summaries[i] = f"无法生成综合摘要，错误: {str(e)}"
        
        # 移除None值
        final_summaries = [s for s in final_summaries if s]
        return "\n\n".join(final_summaries)
    else:
        return all_summaries[0] if all_summaries else "无法生成摘要"

def load_existing_summaries(output_file):
    """加载已有的摘要数据，用于断点续传"""
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"无法解析已有的摘要文件 {output_file}，将创建新文件")
            return []
    return []

def get_processed_ids(summaries):
    """获取已处理过的文档ID列表"""
    return [(summary.get('packageId'), summary.get('granuleId')) for summary in summaries]

def save_summaries(summaries, output_file, backup=False):
    """保存摘要到文件（线程安全）"""
    with file_lock:
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            
            if backup:
                backup_file = f"{output_file}.bak"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存摘要文件时出错: {e}")
            return False

def process_document(package_id, granule_id, document_details, granule, collection, directory, api_key):
    """处理单个文档，生成摘要"""
    try:
        # 获取HTML内容
        html_content = get_html_content(package_id, granule_id, api_key)
        if not html_content:
            return None
        
        # 缓存HTML内容到文件，以便出错时不需要重新下载
        html_cache_dir = os.path.join(directory, '.cache', collection)
        os.makedirs(html_cache_dir, exist_ok=True)
        html_cache_file = os.path.join(html_cache_dir, f"{package_id}_{granule_id}.html")
        
        # 检查缓存文件是否已存在
        if not os.path.exists(html_cache_file):
            with open(html_cache_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        # 清理HTML内容
        text_content = clean_html_content(html_content)
        
        # 将文本分块（更大的块）
        text_chunks = split_text_into_chunks(text_content)
        
        # 使用DeepSeek生成摘要
        summary = get_deepseek_summary(text_chunks, document_details)
        
        document_summary = {
            "packageId": package_id,
            "granuleId": granule_id,
            "title": document_details.get('title', ''),
            "granuleTitle": granule.get('title', ''),
            "dateIssued": document_details.get('dateIssued', ''),
            "collection": collection,
            "collectionName": document_details.get('collectionName', ''),
            "summary": summary,
            "processingTime": datetime.datetime.now().isoformat()
        }
        
        return document_summary
    
    except Exception as e:
        print(f"处理文档 {package_id}, 子条目 {granule_id} 时出错: {e}")
        return None

def process_batch(batch_tasks, directory, api_key):
    """批量处理文档"""
    results = []
    for package_id, granule_id, document_details, granule, collection in batch_tasks:
        try:
            document_summary = process_document(
                package_id, granule_id, document_details, granule, collection, directory, api_key
            )
            if document_summary:
                results.append(document_summary)
        except Exception as e:
            print(f"处理文档 {package_id}, 子条目 {granule_id} 时出错: {e}")
    return results

def process_documents_directory(directory, api_key, output_file):
    """处理文档目录，为每个文档生成摘要（优化版本）"""
    # 加载已有摘要，实现断点续传
    summaries = load_existing_summaries(output_file)
    processed_ids = get_processed_ids(summaries)
    
    if processed_ids:
        print(f"已找到 {len(processed_ids)} 个已处理的文档，将继续处理未完成的文档")
    
    # 获取所有需要处理的文档
    tasks = []
    collection_dirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)) and not d.startswith('.')]
    
    for collection in collection_dirs:
        collection_path = os.path.join(directory, collection)
        print(f"分析集合: {collection}")
        
        # 查找所有详情文件
        detail_files = [f for f in os.listdir(collection_path) if f.endswith('_details.json') and not '_granules_' in f]
        
        for detail_file in detail_files:
            try:
                with open(os.path.join(collection_path, detail_file), 'r', encoding='utf-8') as f:
                    document_details = json.load(f)
                
                package_id = document_details.get('packageId')
                if not package_id:
                    continue
                
                # 查找相应的granules文件
                granules_file = f"{package_id}_granules.json"
                if not os.path.exists(os.path.join(collection_path, granules_file)):
                    continue
                
                with open(os.path.join(collection_path, granules_file), 'r', encoding='utf-8') as f:
                    granules_data = json.load(f)
                
                if not granules_data.get('granules') or len(granules_data['granules']) == 0:
                    continue
                
                # 将每个子条目添加到任务列表
                for granule in granules_data['granules']:
                    granule_id = granule.get('granuleId')
                    
                    if not granule_id:
                        continue
                    
                    # 检查是否已处理过
                    if (package_id, granule_id) in processed_ids:
                        print(f"跳过已处理的文档: {package_id}, 子条目: {granule_id}")
                        continue
                    
                    # 添加到任务列表
                    tasks.append((package_id, granule_id, document_details, granule, collection))
            
            except Exception as e:
                print(f"分析文档 {detail_file} 时出错: {e}")
    
    if not tasks:
        print("没有找到需要处理的文档")
        return summaries
    
    print(f"发现 {len(tasks)} 个文档需要处理")
    
    # 将任务分成多个批次
    batches = [tasks[i:i + BATCH_SIZE] for i in range(0, len(tasks), BATCH_SIZE)]
    total_batches = len(batches)
    
    # 使用线程池并行处理批次
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, batch in enumerate(batches):
            future = executor.submit(process_batch, batch, directory, api_key)
            futures.append((future, i))
        
        # 处理结果
        for future, batch_index in futures:
            try:
                batch_results = future.result()
                summaries.extend(batch_results)
                
                # 更新已处理的ID
                for summary in batch_results:
                    processed_ids.append((summary.get('packageId'), summary.get('granuleId')))
                
                # 定期保存进度
                if (batch_index + 1) % 2 == 0 or batch_index == total_batches - 1:
                    save_summaries(summaries, output_file, backup=True)
                    print(f"已处理 {batch_index + 1}/{total_batches} 批次，当前进度: {(batch_index + 1) / total_batches * 100:.1f}%")
                
            except Exception as e:
                print(f"处理批次 {batch_index + 1} 时出错: {e}")
    
    # 最后确保保存一次
    save_summaries(summaries, output_file, backup=True)
    
    return summaries

def generate_combined_report(summaries, output_file):
    """生成一个汇总报告，简单展示所有文档的摘要"""
    report_file = f"{os.path.splitext(output_file)[0]}_report.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# GovInfo 文档摘要报告\n\n")
        f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"共收集了 {len(summaries)} 个文档的摘要\n\n")
        
        # 按集合分组
        collections = {}
        for summary in summaries:
            collection = summary.get('collection')
            if collection not in collections:
                collections[collection] = []
            collections[collection].append(summary)
        
        # 按集合输出摘要
        for collection, items in collections.items():
            f.write(f"## {collection} ({items[0].get('collectionName', '')})\n\n")
            f.write(f"该集合包含 {len(items)} 个文档\n\n")
            
            for item in items:
                f.write(f"### {item.get('title')}\n\n")
                f.write(f"- 文档ID: {item.get('packageId')}\n")
                f.write(f"- 子条目ID: {item.get('granuleId')}\n")
                f.write(f"- 子条目标题: {item.get('granuleTitle', '无标题')}\n")
                f.write(f"- 发布日期: {item.get('dateIssued')}\n\n")
                f.write("#### 摘要\n\n")
                f.write(f"{item.get('summary')}\n\n")
                f.write("---\n\n")
    
    print(f"汇总报告已生成: {report_file}")
    return report_file

def main():
    # 先声明全局变量
    global MAX_WORKERS, BATCH_SIZE, API_DELAY
    
    parser = argparse.ArgumentParser(description='GovInfo文档摘要生成工具')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--input_dir', required=True, help='输入目录，包含文档JSON文件')
    parser.add_argument('--output_file', required=True, help='输出文件路径，用于保存摘要')
    parser.add_argument('--report', action='store_true', help='生成摘要报告')
    # 使用变量而不是全局变量作为默认值
    parser.add_argument('--threads', type=int, help="并发线程数", default=10)
    parser.add_argument('--batch_size', type=int, help="每批处理的文档数量", default=5)
    parser.add_argument('--chunk_size', type=int, help="文本块大小", default=8000)
    parser.add_argument('--api_delay', type=float, help="API调用之间的延迟时间（秒）", default=0.2)
    
    args = parser.parse_args()
    
    # 更新全局设置
    MAX_WORKERS = args.threads
    BATCH_SIZE = args.batch_size
    API_DELAY = args.api_delay
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # 处理文档
    summaries = process_documents_directory(args.input_dir, args.api_key, args.output_file)
    
    # 生成报告
    if args.report and summaries:
        report_file = os.path.splitext(args.output_file)[0] + "_report.md"
        generate_combined_report(summaries, args.output_file)
        print(f"汇总报告已生成: {report_file}")
    
    return summaries

if __name__ == "__main__":
    main() 