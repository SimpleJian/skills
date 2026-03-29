#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本

用法:
    python tests/run_tests.py              # 运行所有测试
    python tests/run_tests.py -v           # 详细输出
    python tests/run_tests.py -q           # 简洁输出
    python tests/run_tests.py --tb=short   # 简短错误回溯
"""

import sys
import os
import argparse

# 确保 skills 目录在路径中
_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

def main():
    parser = argparse.ArgumentParser(description='运行技能测试')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-q', '--quiet', action='store_true', help='简洁输出')
    parser.add_argument('--tb', default='long', choices=['long', 'short', 'line', 'no'],
                       help='错误回溯格式')
    parser.add_argument('-k', '--keyword', help='只运行匹配的测试')
    parser.add_argument('--no-coverage', action='store_true', help='不生成覆盖率报告')
    
    args = parser.parse_args()
    
    # 构建 pytest 参数
    pytest_args = ['-xvs' if args.verbose else '-v' if not args.quiet else '-q']
    pytest_args.append(f'--tb={args.tb}')
    
    if args.keyword:
        pytest_args.append(f'-k={args.keyword}')
    
    # 添加测试目录
    test_dir = os.path.dirname(os.path.abspath(__file__))
    pytest_args.append(test_dir)
    
    # 运行测试
    try:
        import pytest
        exit_code = pytest.main(pytest_args)
    except ImportError:
        print("错误: 未安装 pytest，使用 unittest 运行测试")
        print("安装: pip install pytest")
        print()
        
        # 使用 unittest 作为备选
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover(test_dir, pattern='test_*.py')
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)
        exit_code = 0 if result.wasSuccessful() else 1
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
