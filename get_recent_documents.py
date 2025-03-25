#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import requests
import datetime
import sys

def get_one_week_ago():
    """返回一周前的日期，ISO 8601格式"""
    one_week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    return one_week_ago.strftime('%Y-%m-%dT00:00:00Z')

def get_collections(api_key):
    """获取所有可用的集合信息"""
    url = f"https://api.govinfo.gov/collections?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取集合信息失败: {response.status_code}")
        return None

def get_documents_for_collection(collection_code, start_date, api_key, page_size=10):
    """获取指定集合的最近文档"""
    url = f"https://api.govinfo.gov/collections/{collection_code}/{start_date}?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取{collection_code}集合文档失败: {response.status_code}")
        return None

def get_document_details(package_id, api_key):
    """获取文档详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取文档{package_id}详情失败: {response.status_code}")
        return None

def get_granules(package_id, api_key, page_size=10):
    """获取文档的子条目"""
    url = f"https://api.govinfo.gov/packages/{package_id}/granules?offsetMark=*&pageSize={page_size}&api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取文档{package_id}的子条目失败: {response.status_code}")
        return None

def get_granule_details(package_id, granule_id, api_key):
    """获取子条目详细信息"""
    url = f"https://api.govinfo.gov/packages/{package_id}/granules/{granule_id}/summary?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取子条目{granule_id}详情失败: {response.status_code}")
        return None

def main():
    parser = argparse.ArgumentParser(description='获取GovInfo API中最近一周的文档信息')
    parser.add_argument('--api_key', required=True, help='GovInfo API密钥')
    parser.add_argument('--collections', nargs='+', default=['FR', 'BILLS', 'CREC'], 
                        help='要查询的集合代码，默认为FR, BILLS, CREC')
    parser.add_argument('--page_size', type=int, default=10, help='每页结果数，默认为10')
    parser.add_argument('--output_dir', default='recent_documents', help='输出目录，默认为recent_documents')
    
    args = parser.parse_args()
    
    # 创建输出目录
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # 获取一周前的日期
    start_date = get_one_week_ago()
    print(f"正在获取从 {start_date} 至今的文档信息...")
    
    # 获取所有集合信息（可选）
    collections_info = get_collections(args.api_key)
    if collections_info:
        with open(os.path.join(args.output_dir, 'collections.json'), 'w', encoding='utf-8') as f:
            json.dump(collections_info, f, ensure_ascii=False, indent=2)
        print(f"所有集合信息已保存到 {os.path.join(args.output_dir, 'collections.json')}")
    
    # 为每个请求的集合获取文档
    for collection in args.collections:
        print(f"正在获取 {collection} 集合的最近文档...")
        documents = get_documents_for_collection(collection, start_date, args.api_key, args.page_size)
        
        if documents and documents.get('count', 0) > 0:
            # 保存集合文档列表
            with open(os.path.join(args.output_dir, f'{collection}_documents.json'), 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            print(f"已找到 {documents.get('count')} 个 {collection} 文档，已保存到 {os.path.join(args.output_dir, f'{collection}_documents.json')}")
            
            # 为每个文档获取详细信息和子条目
            documents_dir = os.path.join(args.output_dir, collection)
            if not os.path.exists(documents_dir):
                os.makedirs(documents_dir)
            
            # 获取前3个文档的详细信息（避免API请求过多）
            for i, package in enumerate(documents.get('packages', [])[:5]):
                package_id = package.get('packageId')
                if package_id:
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
                            
                            # 获取第一个子条目的详细信息
                            if granules.get('granules') and len(granules.get('granules')) > 0:
                                granule_id = granules['granules'][0].get('granuleId')
                                if granule_id:
                                    granule_details = get_granule_details(package_id, granule_id, args.api_key)
                                    if granule_details:
                                        with open(os.path.join(documents_dir, f'{package_id}_{granule_id}_details.json'), 'w', encoding='utf-8') as f:
                                            json.dump(granule_details, f, ensure_ascii=False, indent=2)
        else:
            print(f"{collection} 集合中没有找到最近一周的文档")
    
    print("所有请求已完成。文档信息已保存到", args.output_dir)

if __name__ == "__main__":
    main() 