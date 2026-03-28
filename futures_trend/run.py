#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品期货趋势跟踪选股策略 - 运行入口

使用方法:
    python run.py
    
环境变量:
    TUSHARE_TOKEN - Tushare API Token (必需)
"""

import os
import sys
import argparse
from datetime import datetime


def check_environment():
    """检查运行环境"""
    try:
        import tushare
        import pandas
        import numpy
    except ImportError as e:
        print(f"错误: 缺少必要的依赖包 - {e}")
        print("\n请安装依赖:")
        print("  pip install tushare pandas numpy -i https://pypi.tuna.tsinghua.edu.cn/simple")
        sys.exit(1)
    
    # 检查 Tushare Token
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("错误: 未设置 TUSHARE_TOKEN 环境变量")
        print("\n请设置环境变量:")
        print("  export TUSHARE_TOKEN=your_token_here")
        print("\n获取 Token: https://tushare.pro/register")
        sys.exit(1)
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='商品期货趋势跟踪选股策略')
    parser.add_argument('-c', '--capital', type=float, default=100, 
                       help='资金规模(万元) (默认: 100)')
    parser.add_argument('-e', '--env', type=str, 
                       choices=['强牛', '弱牛', '震荡', '弱熊', '强熊'],
                       default='震荡', help='市场环境 (默认: 震荡)')
    parser.add_argument('-a', '--adx', type=float, default=25,
                       help='ADX阈值 (默认: 25)')
    parser.add_argument('--code', type=str, help='分析指定合约代码')
    
    args = parser.parse_args()
    
    # 检查环境
    check_environment()
    
    # 导入模块
    import tushare as ts
    from futures_selector import FuturesSelector
    from trend_strength import TrendStrength
    
    # 初始化 Tushare
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    # 分析指定合约
    if args.code:
        print(f"\n【合约深度分析】{args.code}")
        print()
        
        ts_analyzer = TrendStrength(pro)
        
        # 多头评分
        result_long = ts_analyzer.calculate_comprehensive_score(args.code, '多头')
        print(f"多头方向评分: {result_long['total_score']}/100")
        if result_long['total_score'] > 0:
            print(f"  分项得分: {result_long['scores']}")
            print(f"  关键指标: {result_long['indicators']}")
        
        print()
        
        # 空头评分
        result_short = ts_analyzer.calculate_comprehensive_score(args.code, '空头')
        print(f"空头方向评分: {result_short['total_score']}/100")
        if result_short['total_score'] > 0:
            print(f"  分项得分: {result_short['scores']}")
            print(f"  关键指标: {result_short['indicators']}")
        
        # 建议方向
        if result_long['total_score'] > result_short['total_score']:
            print(f"\n【建议方向】多头 (优势{result_long['total_score'] - result_short['total_score']}分)")
        elif result_short['total_score'] > result_long['total_score']:
            print(f"\n【建议方向】空头 (优势{result_short['total_score'] - result_long['total_score']}分)")
        else:
            print(f"\n【建议方向】观望 (多空评分相当)")
        
        return
    
    # 执行选股流程
    print("=" * 80)
    print("商品期货趋势跟踪选股策略")
    print("=" * 80)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"资金规模: {args.capital}万")
    print(f"市场环境: {args.env}")
    print(f"ADX阈值: {args.adx}")
    print("=" * 80)
    print()
    
    selector = FuturesSelector(pro, total_capital=args.capital * 10000)
    result = selector.select_contracts(
        market_env=args.env,
        adx_threshold=args.adx
    )
    
    print("\n" + "=" * 80)
    print("运行完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
