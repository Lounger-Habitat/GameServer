#!/usr/bin/env python3
"""
API Key生成工具

用法:
    python generate_api_key.py <username>
"""

import os
import sys
import yaml
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gameserver.utils.auth import create_api_key, API_KEY_FILE


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="生成API Key")
    parser.add_argument("username", help="用户名")
    parser.add_argument("--save", action="store_true", help="是否保存到api_keys.yaml文件", default=True)
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 生成API Key (永久有效，不使用权限)
    api_key = create_api_key(args.username)
    
    # 打印API Key
    print(f"\n生成的API Key:")
    print(f"{api_key}\n")
    
    # 如果需要保存
    if args.save:
        # 确保目录存在
        os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
        
        # 加载现有API Keys
        api_keys = {}
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
                api_keys = yaml.safe_load(f) or {}
        
        # 添加新的API Key
        api_keys[api_key] = {
            "username": args.username
        }
        
        # 保存到文件
        with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(api_keys, f, allow_unicode=True)
        
        print(f"API Key已保存到 {API_KEY_FILE}")
    
    print(f"用户: {args.username}")
    print(f"有效期: 永久")


if __name__ == "__main__":
    main()