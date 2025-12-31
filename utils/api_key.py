#!/usr/bin/env python3
"""API Key 管理脚本

使用方法:
    # 创建 Key（永久有效）
    uv run python manage_keys.py create my-app
    
    # 创建 Key（30天有效）
    uv run python manage_keys.py create my-app --days 30
    
    # 列出所有 Keys
    uv run python manage_keys.py list
    
    # 删除 Key
    uv run python manage_keys.py delete my-app
"""
import argparse
import sys
from datetime import datetime

# 确保可以导入项目模块
sys.path.insert(0, ".")

from api.auth.models import ApiKeyCreate
from api.auth.storage import ApiKeyStore


def create_key(args):
    """创建新的 API Key"""
    store = ApiKeyStore(args.keys_file)
    
    try:
        request = ApiKeyCreate(name=args.name, expires_in_days=args.days)
        api_key = store.create_key(request)
        
        print("=" * 60)
        print("✅ API Key 创建成功")
        print("=" * 60)
        print(f"名称:     {api_key.name}")
        print(f"Key:      {api_key.key}")
        print(f"创建时间: {api_key.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if api_key.expires_at:
            print(f"过期时间: {api_key.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("过期时间: 永久有效")
        print("=" * 60)
        print("⚠️  请妥善保存此 Key，它只会显示一次！")
        print()
    except ValueError as e:
        print(f"❌ 创建失败: {e}")
        sys.exit(1)


def list_keys(args):
    """列出所有 API Keys"""
    store = ApiKeyStore(args.keys_file)
    keys = store.list_keys()
    
    if not keys:
        print("📭 暂无 API Keys")
        return
    
    print("=" * 70)
    print(f"{'名称':<20} {'Key 预览':<18} {'过期时间':<20} {'状态':<10}")
    print("-" * 70)
    
    for key in keys:
        expires = key.expires_at.strftime('%Y-%m-%d %H:%M') if key.expires_at else "永久"
        
        if not key.is_active:
            status = "🚫 已禁用"
        elif key.is_expired:
            status = "⏰ 已过期"
        else:
            status = "✅ 有效"
        
        print(f"{key.name:<20} {key.key_preview:<18} {expires:<20} {status:<10}")
    
    print("=" * 70)
    print(f"共 {len(keys)} 个 Key")


def delete_key(args):
    """删除指定的 API Key"""
    store = ApiKeyStore(args.keys_file)
    
    if store.delete_key(args.name):
        print(f"✅ 已删除 API Key: {args.name}")
    else:
        print(f"❌ 未找到名为 '{args.name}' 的 API Key")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="API Key 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--keys-file", 
        default="api_keys.json",
        help="Keys 存储文件路径 (默认: api_keys.json)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # create 命令
    create_parser = subparsers.add_parser("create", help="创建新的 API Key")
    create_parser.add_argument("name", help="Key 名称（唯一标识）")
    create_parser.add_argument(
        "--days", "-d", 
        type=int, 
        default=None,
        help="有效天数（不设置则永久有效）"
    )
    create_parser.set_defaults(func=create_key)
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有 API Keys")
    list_parser.set_defaults(func=list_keys)
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除指定的 API Key")
    delete_parser.add_argument("name", help="要删除的 Key 名称")
    delete_parser.set_defaults(func=delete_key)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
