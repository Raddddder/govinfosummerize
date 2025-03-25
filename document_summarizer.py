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

# DeepSeek API密钥
DEEPSEEK_API_KEY = "sk-c448db32df6944eab2c8d5d9108ec158"

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

def split_text_into_chunks(text, max_chunk_size=3000):
    """将文本分割成适合AI处理的小块"""
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

def get_deepseek_summary(text_chunks, document_info):
    """使用DeepSeek API生成摘要"""
    # 构建提示
    if not text_chunks:
        return "无法生成摘要：没有有效的文本内容。"
    
    all_summaries = []
    
    # 构建文档信息描述
    doc_info_text = f"文档标题: {document_info.get('title', '未知')}\n"
    doc_info_text += f"文档ID: {document_info.get('packageId', '未知')}\n"
    doc_info_text += f"发布日期: {document_info.get('dateIssued', '未知')}\n"
    doc_info_text += f"集合: {document_info.get('collectionName', '未知')}\n\n"
    
    # 为每个文本块生成摘要
    for i, chunk in enumerate(text_chunks):
        print(f"处理第 {i+1}/{len(text_chunks)} 块内容...")
        
        # 构建每个块的提示
        if i == 0:
            # 第一个块包含文档信息
            prompt = f"{doc_info_text}请对以下政府文档内容生成一个简洁但详实的摘要。这是文档的第 {i+1}/{len(text_chunks)} 部分：\n\n{chunk}"
        else:
            # 后续块
            prompt = f"请继续分析这个政府文档的第 {i+1}/{len(text_chunks)} 部分并生成摘要：\n\n{chunk}"
        
        # 调用DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"]
                all_summaries.append(summary)
            else:
                print(f"DeepSeek API调用失败: {response.status_code}")
                print(response.text)
                all_summaries.append(f"无法生成此部分的摘要，API错误: {response.status_code}")
        
        except Exception as e:
            print(f"调用DeepSeek API时出错: {e}")
            all_summaries.append(f"无法生成此部分的摘要，错误: {str(e)}")
        
        # 避免API限制
        time.sleep(1)
    
    # 如果有多个块，再生成一个综合摘要
    if len(all_summaries) > 1:
        print("生成综合摘要...")
        combined_summary = "\n\n".join(all_summaries)
        
        # 如果综合摘要太长，可能需要再次分块处理
        combined_chunks = split_text_into_chunks(combined_summary, 4000)
        final_summaries = []
        
        for i, c_chunk in enumerate(combined_chunks):
            prompt = f"请基于以下多个摘要片段，为这份政府文档生成一个连贯、全面但简洁的整体摘要。这是第 {i+1}/{len(combined_chunks)} 部分的摘要集合：\n\n{c_chunk}"
            
            try:
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    final_summary = result["choices"][0]["message"]["content"]
                    final_summaries.append(final_summary)
                else:
                    print(f"DeepSeek API调用失败: {response.status_code}")
                    print(response.text)
                    final_summaries.append(f"无法生成综合摘要，API错误: {response.status_code}")
            
            except Exception as e:
                print(f"调用DeepSeek API时出错: {e}")
                final_summaries.append(f"无法生成综合摘要，错误: {str(e)}")
            
            time.sleep(1)
        
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

def process_documents_directory(directory, api_key, output_file):
    """处理文档目录，为每个文档生成摘要"""
    # 加载已有摘要，实现断点续传
    summaries = load_existing_summaries(output_file)
    processed_ids = get_processed_ids(summaries)
    
    if processed_ids:
        print(f"已找到 {len(processed_ids)} 个已处理的文档，将继续处理未完成的文档")
    
    collection_dirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)) and not d.startswith('.')]
    
    for collection in collection_dirs:
        collection_path = os.path.join(directory, collection)
        print(f"处理集合: {collection}")
        
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
                
                # 处理每个子条目
                for granule_index, granule in enumerate(granules_data['granules']):
                    granule_id = granule.get('granuleId')
                    
                    if not granule_id:
                        continue
                    
                    # 检查是否已处理过
                    if (package_id, granule_id) in processed_ids:
                        print(f"跳过已处理的文档: {package_id}, 子条目: {granule_id}")
                        continue
                    
                    print(f"处理文档: {package_id}, 子条目: {granule_id} ({granule_index+1}/{len(granules_data['granules'])})")
                    
                    # 获取HTML内容
                    html_content = get_html_content(package_id, granule_id, api_key)
                    if not html_content:
                        continue
                    
                    # 缓存HTML内容到文件，以便出错时不需要重新下载
                    html_cache_dir = os.path.join(directory, '.cache', collection)
                    os.makedirs(html_cache_dir, exist_ok=True)
                    html_cache_file = os.path.join(html_cache_dir, f"{package_id}_{granule_id}.html")
                    
                    with open(html_cache_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # 清理HTML内容
                    text_content = clean_html_content(html_content)
                    
                    # 将文本分块
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
                    
                    summaries.append(document_summary)
                    processed_ids.append((package_id, granule_id))
                    
                    # 写入当前进度到输出文件
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(summaries, f, ensure_ascii=False, indent=2)
                    
                    print(f"已完成文档 {package_id} 的子条目 {granule_id} 的摘要")
                    print("-" * 80)
                    
                    # 每处理完一个子条目，备份一次输出文件
                    backup_file = f"{output_file}.bak"
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(summaries, f, ensure_ascii=False, indent=2)
            
            except Exception as e:
                print(f"处理文档 {detail_file} 时出错: {e}")
                # 出错时也保存当前进度
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, ensure_ascii=False, indent=2)
    
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
    parser = argparse.ArgumentParser(description='为GovInfo文档生成摘要')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--input_dir', default='recent_documents', help='输入目录，默认为recent_documents')
    parser.add_argument('--output_file', default='document_summaries.json', help='输出文件，默认为document_summaries.json')
    parser.add_argument('--report', action='store_true', help='是否只生成报告而不处理新文档')
    
    args = parser.parse_args()
    
    if args.report:
        # 只生成报告模式
        if os.path.exists(args.output_file) and os.path.getsize(args.output_file) > 0:
            try:
                with open(args.output_file, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
                
                report_file = generate_combined_report(summaries, args.output_file)
                print(f"报告已生成: {report_file}")
                return
            except Exception as e:
                print(f"生成报告时出错: {e}")
                return
        else:
            print(f"找不到摘要文件 {args.output_file}，请先运行摘要生成")
            return
    
    print(f"开始处理目录: {args.input_dir}")
    
    summaries = process_documents_directory(args.input_dir, args.api_key, args.output_file)
    
    print(f"处理完成，摘要已保存到 {args.output_file}")
    print(f"总共生成了 {len(summaries)} 个文档摘要")
    
    # 生成汇总报告
    generate_combined_report(summaries, args.output_file)

if __name__ == "__main__":
    main() 