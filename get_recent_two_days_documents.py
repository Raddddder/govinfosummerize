#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import requests
import datetime
import sys
import time

def get_two_days_ago():
    """返回两天前的日期，ISO 8601格式"""
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
    return two_days_ago.strftime('%Y-%m-%dT00:00:00Z')

def get_collections(api_key):
    """获取所有可用的集合信息"""
    url = f"https://api.govinfo.gov/collections?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取集合信息失败: {response.status_code}")
        return None

def get_documents_for_collection(collection_code, start_date, api_key, page_size=100):
    """获取指定集合的最近文档"""
    all_packages = []
    url = f"https://api.govinfo.gov/collections/{collection_code}/{start_date}?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    
    while url:
        print(f"正在请求: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('packages'):
                all_packages.extend(data.get('packages', []))
                print(f"已获取 {len(all_packages)}/{data.get('count', 0)} 个文档")
                
                # 获取下一页的URL
                next_page = data.get('nextPage')
                if next_page:
                    url = next_page + f"&api_key={api_key}"
                else:
                    url = None
                
                # 避免API限制
                time.sleep(0.5)
            else:
                url = None
        else:
            print(f"获取{collection_code}集合文档失败: {response.status_code}")
            url = None
    
    return {"count": len(all_packages), "packages": all_packages}

def get_document_details(package_id, api_key):
    """获取文档详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取文档{package_id}详情失败: {response.status_code}")
        return None

def get_granules(package_id, api_key, page_size=100):
    """获取文档的子条目"""
    all_granules = []
    url = f"https://api.govinfo.gov/packages/{package_id}/granules?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    
    while url:
        print(f"正在获取子条目: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('granules'):
                all_granules.extend(data.get('granules', []))
                print(f"已获取 {len(all_granules)}/{data.get('count', 0)} 个子条目")
                
                # 获取下一页的URL
                next_page = data.get('nextPage')
                if next_page:
                    url = next_page + f"&api_key={api_key}"
                else:
                    url = None
                
                # 避免API限制
                time.sleep(0.5)
            else:
                url = None
        else:
            print(f"获取文档{package_id}的子条目失败: {response.status_code}")
            url = None
    
    return {"count": len(all_granules), "granules": all_granules}

def get_granule_details(package_id, granule_id, api_key):
    """获取子条目详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/granules/{granule_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取子条目{granule_id}详情失败: {response.status_code}")
        return None

def count_documents_by_collection(output_dir):
    """统计每个集合的文档数量"""
    counts = {}
    for item in os.listdir(output_dir):
        if os.path.isdir(os.path.join(output_dir, item)) and not item.startswith('.'):
            num_files = len([f for f in os.listdir(os.path.join(output_dir, item)) if f.endswith('_details.json') and not '_granules_' in f])
            counts[item] = num_files
    return counts

def main():
    parser = argparse.ArgumentParser(description='获取GovInfo API中最近两天的所有文档信息')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--collections', nargs='+', default=['FR', 'BILLS', 'CREC'], 
                        help='要查询的集合代码，默认为FR, BILLS, CREC')
    parser.add_argument('--page_size', type=int, default=100, help='每页结果数，默认为100')
    parser.add_argument('--output_dir', default='recent_documents', help='输出目录，默认为recent_documents')
    parser.add_argument('--max_documents', type=int, default=1000, help='每个集合最多处理的文档数量，默认为1000')
    
    args = parser.parse_args()
    
    # 创建输出目录
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # 获取两天前的日期
    start_date = get_two_days_ago()
    print(f"正在获取从 {start_date} 至今的文档信息...")
    
    # 获取所有集合信息（可选）
    collections_info = get_collections(args.api_key)
    if collections_info:
        with open(os.path.join(args.output_dir, 'collections.json'), 'w', encoding='utf-8') as f:
            json.dump(collections_info, f, ensure_ascii=False, indent=2)
        print(f"所有集合信息已保存到 {os.path.join(args.output_dir, 'collections.json')}")
    
    collection_counts = {}
    
    # 为每个请求的集合获取文档
    for collection in args.collections:
        print(f"正在获取 {collection} 集合的最近文档...")
        documents = get_documents_for_collection(collection, start_date, args.api_key, args.page_size)
        
        if documents and documents.get('count', 0) > 0:
            # 保存集合文档列表
            with open(os.path.join(args.output_dir, f'{collection}_documents.json'), 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            print(f"已找到 {documents.get('count')} 个 {collection} 文档，已保存到 {os.path.join(args.output_dir, f'{collection}_documents.json')}")
            
            collection_counts[collection] = documents.get('count', 0)
            
            # 为每个文档获取详细信息和子条目
            documents_dir = os.path.join(args.output_dir, collection)
            if not os.path.exists(documents_dir):
                os.makedirs(documents_dir)
            
            # 获取所有文档的详细信息（限制最大数量）
            max_docs = min(args.max_documents, len(documents.get('packages', [])))
            
            # 跟踪已处理的文档
            processed_packages = {}
            processed_file = os.path.join(args.output_dir, f'{collection}_processed.json')
            
            # 加载已处理的文档
            if os.path.exists(processed_file):
                try:
                    with open(processed_file, 'r', encoding='utf-8') as f:
                        processed_packages = json.load(f)
                except:
                    processed_packages = {}
            
            print(f"将处理 {max_docs} 个 {collection} 文档")
            
            for i, package in enumerate(documents.get('packages', [])[:max_docs]):
                package_id = package.get('packageId')
                if not package_id:
                    continue
                
                # 检查是否已处理
                if package_id in processed_packages:
                    print(f"跳过已处理的文档 {package_id} ({i+1}/{max_docs})")
                    continue
                
                print(f"处理文档 {package_id} ({i+1}/{max_docs})")
                
                # 获取文档详情
                details = get_document_details(package_id, args.api_key)
                if details:
                    with open(os.path.join(documents_dir, f'{package_id}_details.json'), 'w', encoding='utf-8') as f:
                        json.dump(details, f, ensure_ascii=False, indent=2)
                    
                    # 获取文档子条目
                    granules = get_granules(package_id, args.api_key, args.page_size)
                    if granules and granules.get('count', 0) > 0:
                        with open(os.path.join(documents_dir, f'{package_id}_granules.json'), 'w', encoding='utf-8') as f:
                            json.dump(granules, f, ensure_ascii=False, indent=2)
                        
                        # 获取每个子条目的详细信息
                        for g_index, granule in enumerate(granules.get('granules', [])):
                            granule_id = granule.get('granuleId')
                            if granule_id:
                                # 检查是否已处理
                                if package_id in processed_packages and granule_id in processed_packages[package_id]:
                                    print(f"跳过已处理的子条目 {granule_id} ({g_index+1}/{granules.get('count', 0)})")
                                    continue
                                
                                print(f"处理子条目 {granule_id} ({g_index+1}/{granules.get('count', 0)})")
                                
                                granule_details = get_granule_details(package_id, granule_id, args.api_key)
                                if granule_details:
                                    with open(os.path.join(documents_dir, f'{package_id}_{granule_id}_details.json'), 'w', encoding='utf-8') as f:
                                        json.dump(granule_details, f, ensure_ascii=False, indent=2)
                                
                                # 记录已处理的子条目
                                if package_id not in processed_packages:
                                    processed_packages[package_id] = []
                                processed_packages[package_id].append(granule_id)
                                
                                # 更新处理记录
                                with open(processed_file, 'w', encoding='utf-8') as f:
                                    json.dump(processed_packages, f, ensure_ascii=False, indent=2)
                                
                                # 避免API限制
                                time.sleep(0.5)
                    
                    # 记录已处理的文档
                    processed_packages[package_id] = processed_packages.get(package_id, [])
                    
                    # 更新处理记录
                    with open(processed_file, 'w', encoding='utf-8') as f:
                        json.dump(processed_packages, f, ensure_ascii=False, indent=2)
                
                # 避免API限制
                time.sleep(0.5)
        else:
            print(f"{collection} 集合中没有找到最近两天的文档")
            collection_counts[collection] = 0
    
    print("所有请求已完成。文档信息已保存到", args.output_dir)
    
    # 统计每个集合的实际下载文档数量
    actual_counts = count_documents_by_collection(args.output_dir)
    
    print("\n===== 文档统计 =====")
    print("集合\t请求数量\t实际下载数量")
    for collection in args.collections:
        print(f"{collection}\t{collection_counts.get(collection, 0)}\t{actual_counts.get(collection, 0)}")

if __name__ == "__main__":
    main() 