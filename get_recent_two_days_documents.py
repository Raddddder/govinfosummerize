#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import requests
import datetime
import sys
import time

def print_status(message):
    """打印状态信息并立即刷新"""
    print(message, flush=True)

def get_two_days_ago():
    """返回两天前的日期，ISO 8601格式"""
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
    return two_days_ago.strftime('%Y-%m-%dT00:00:00Z')

def get_two_days_ago_date():
    """返回两天前的日期，YYYY-MM-DD格式，用于过滤文档"""
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
    return two_days_ago.strftime('%Y-%m-%d')

def get_collections(api_key):
    """获取所有可用的集合信息"""
    url = f"https://api.govinfo.gov/collections?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # 确保返回的是列表格式
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'collections' in data:
            return data['collections']
        else:
            print_status(f"获取集合信息失败: 返回数据格式不正确")
            return None
    else:
        print_status(f"获取集合信息失败: {response.status_code}")
        return None

def get_documents_for_collection(collection_code, start_date, api_key, page_size=100):
    """获取指定集合的最近文档"""
    all_packages = []
    cutoff_date = get_two_days_ago_date()
    
    # 使用lastModifiedStartDate参数
    start_date = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime('%Y-%m-%dT00:00:00Z')
    end_date = datetime.datetime.now().strftime('%Y-%m-%dT23:59:59Z')
    url = f"https://api.govinfo.gov/collections/{collection_code}/{start_date}/{end_date}?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    
    while url:
        print_status(f"正在请求: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('packages'):
                # 只过滤dateIssued在最近两天内的文档
                filtered_packages = [
                    package for package in data.get('packages', [])
                    if package.get('dateIssued', '').split('T')[0] >= cutoff_date
                ]
                all_packages.extend(filtered_packages)
                print_status(f"已获取 {len(all_packages)} 个最近两天的文档")
                
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
            print_status(f"获取{collection_code}集合文档失败: {response.status_code}")
            url = None
    
    return {"count": len(all_packages), "packages": all_packages}

def get_document_details(package_id, api_key):
    """获取文档详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print_status(f"获取文档{package_id}详情失败: {response.status_code}")
        return None

def get_granules(package_id, api_key, page_size=100):
    """获取文档的子条目"""
    all_granules = []
    url = f"https://api.govinfo.gov/packages/{package_id}/granules?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    
    while url:
        print_status(f"正在获取子条目: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('granules'):
                all_granules.extend(data.get('granules', []))
                print_status(f"已获取 {len(all_granules)} 个子条目")
                
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
            print_status(f"获取文档{package_id}的子条目失败: {response.status_code}")
            url = None
    
    return {"count": len(all_granules), "granules": all_granules}

def get_granule_details(package_id, granule_id, api_key):
    """获取子条目详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/granules/{granule_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print_status(f"获取子条目{granule_id}详情失败: {response.status_code}")
        return None

def main():
    parser = argparse.ArgumentParser(description='获取GovInfo最近两天的文档')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--collections', nargs='+', default=['FR', 'BILLS', 'CREC'], 
                       help='要查询的集合代码列表，默认为FR, BILLS, CREC')
    parser.add_argument('--page_size', type=int, default=100, help='每页结果数，默认为100')
    parser.add_argument('--output_dir', default='recent_documents', help='输出目录，默认为recent_documents')
    parser.add_argument('--max_documents', type=int, default=1000, help='每个集合最多处理的文档数量，默认为1000')
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 获取所有集合信息
    print_status("\n正在获取集合信息...")
    collections = get_collections(args.api_key)
    if not collections:
        print_status("无法获取集合信息，程序终止")
        return
    
    # 记录已处理的文档
    processed_packages = {}
    
    # 处理每个集合
    for collection in collections:
        # 确保collection是字典类型
        if isinstance(collection, str):
            collection = {'collectionCode': collection, 'collectionName': collection}
        
        collection_code = collection.get('collectionCode')
        if not collection_code or collection_code not in args.collections:
            continue
        
        print_status(f"\n{'=' * 80}")
        print_status(f"处理集合: {collection_code}")
        print_status(f"集合名称: {collection.get('collectionName', '未知')}")
        print_status(f"{'=' * 80}\n")
        
        # 获取该集合的文档
        documents = get_documents_for_collection(collection_code, get_two_days_ago(), args.api_key, args.page_size)
        
        if not documents or not documents.get('packages'):
            print_status(f"未找到{collection_code}集合的文档")
            continue
        
        # 限制文档数量
        max_docs = min(len(documents['packages']), args.max_documents)
        print_status(f"将处理 {max_docs} 个文档")
        
        # 创建集合目录
        collection_dir = os.path.join(args.output_dir, collection_code)
        os.makedirs(collection_dir, exist_ok=True)
        
        # 处理每个文档
        for i, package in enumerate(documents['packages']):
            package_id = package.get('packageId')
            
            if not package_id:
                continue
            
            # 检查是否已处理
            if package_id in processed_packages:
                print_status(f"跳过已处理的文档 {package_id} ({i+1}/{max_docs})")
                continue
            
            print_status(f"\n处理文档 {package_id} ({i+1}/{max_docs})")
            
            # 获取文档详情
            details = get_document_details(package_id, args.api_key)
            if details:
                # 检查文档日期是否在最近两天内
                date_issued = details.get('dateIssued', '').split('T')[0]
                if date_issued < get_two_days_ago_date():
                    print_status(f"跳过非最近两天的文档 {package_id}")
                    continue
                
                with open(os.path.join(collection_dir, f'{package_id}_details.json'), 'w', encoding='utf-8') as f:
                    json.dump(details, f, ensure_ascii=False, indent=2)
                
                # 获取文档子条目
                granules = get_granules(package_id, args.api_key, args.page_size)
                if granules and granules.get('count', 0) > 0:
                    with open(os.path.join(collection_dir, f'{package_id}_granules.json'), 'w', encoding='utf-8') as f:
                        json.dump(granules, f, ensure_ascii=False, indent=2)
                    
                    # 获取每个子条目的详细信息
                    for g_index, granule in enumerate(granules.get('granules', [])):
                        granule_id = granule.get('granuleId')
                        if granule_id:
                            # 检查是否已处理
                            if package_id in processed_packages and granule_id in processed_packages[package_id]:
                                print_status(f"跳过已处理的子条目 {granule_id} ({g_index+1}/{granules.get('count', 0)})")
                                continue
                            
                            print_status(f"处理子条目 {granule_id} ({g_index+1}/{granules.get('count', 0)})")
                            
                            granule_details = get_granule_details(package_id, granule_id, args.api_key)
                            if granule_details:
                                with open(os.path.join(collection_dir, f'{package_id}_{granule_id}_details.json'), 'w', encoding='utf-8') as f:
                                    json.dump(granule_details, f, ensure_ascii=False, indent=2)
                            
                            # 记录已处理的子条目
                            if package_id not in processed_packages:
                                processed_packages[package_id] = []
                            processed_packages[package_id].append(granule_id)
            
            # 避免API限制
            time.sleep(0.5)
    
    print_status("\n文档获取完成！")
    print_status(f"输出目录: {args.output_dir}")

if __name__ == "__main__":
    main() 