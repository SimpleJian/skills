#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一运行入口 - 执行所有策略

使用方法:
    python run_all.py --mode a_share      # 只运行A股策略
    python run_all.py --mode futures      # 只运行期货策略
    python run_all.py --mode all          # 运行所有策略（默认）
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime


def run_skill(skill_path: str, name: str, extra_args: list = None):
    """运行单个 skill"""
    print(f"\n{'='*70}")
    print(f"运行 {name}")
    print('='*70)
    
    cmd = ['python3', 'run.py']
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=skill_path,
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"运行 {name} 失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='运行所有投资策略')
    parser.add_argument('--mode', type=str, choices=['all', 'a_share', 'futures'],
                       default='all', help='运行模式')
    parser.add_argument('--skip-trend', action='store_true', help='跳过趋势策略')
    parser.add_argument('--skip-value', action='store_true', help='跳过价值策略')
    
    args = parser.parse_args()
    
    # 检查环境
    if not os.getenv('TUSHARE_TOKEN'):
        print("错误: 请设置 TUSHARE_TOKEN 环境变量")
        sys.exit(1)
    
    # 动态获取 skills 目录路径（本文件位于 skills 目录下）
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    skills_to_run = []
    
    # 选择要运行的策略
    if args.mode in ['all', 'a_share']:
        if not args.skip_trend:
            skills_to_run.append(('a_share_trend', 'A股趋势跟踪策略'))
        if not args.skip_value:
            skills_to_run.append(('a_share_value', 'A股价值抄底策略'))
    
    if args.mode in ['all', 'futures']:
        if not args.skip_trend:
            skills_to_run.append(('futures_trend', '期货趋势跟踪策略'))
        if not args.skip_value:
            skills_to_run.append(('futures_value', '期货价值抄底策略'))
    
    print("="*70)
    print("投资策略批量运行")
    print("="*70)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"运行模式: {args.mode}")
    print(f"策略数量: {len(skills_to_run)}")
    print("="*70)
    
    # 执行所有选中的策略
    results = []
    for skill_dir, skill_name in skills_to_run:
        skill_path = os.path.join(base_path, skill_dir)
        if os.path.exists(skill_path):
            success = run_skill(skill_path, skill_name)
            results.append((skill_name, success))
        else:
            print(f"警告: {skill_path} 不存在，跳过")
            results.append((skill_name, False))
    
    # 汇总结果
    print("\n" + "="*70)
    print("运行结果汇总")
    print("="*70)
    
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{name}: {status}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\n总计: {success_count}/{len(results)} 个策略运行成功")
    print("="*70)


if __name__ == '__main__':
    main()
