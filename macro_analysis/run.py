#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观分析运行入口

使用方法:
    python run.py
"""

import sys
import os

# 动态获取 skills 目录路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

import tushare as ts
from macro_analysis.macro_analyzer import MacroAnalyzer


def main():
    """主函数"""
    # 检查环境
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("错误: 请设置 TUSHARE_TOKEN 环境变量")
        print("获取方式: https://tushare.pro/register")
        sys.exit(1)
    
    # 初始化Tushare
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 创建分析器并运行
    analyzer = MacroAnalyzer(pro)
    
    try:
        result = analyzer.full_analysis()
        
        # 返回码：0=正常，1=数据不足
        if result['phase'] == "数据不足":
            sys.exit(1)
        
    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
