#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品期货价值抄底选股策略 - 运行入口

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
    parser = argparse.ArgumentParser(description='商品期货价值抄底选股策略')
    parser.add_argument('-c', '--capital', type=float, default=100,
                       help='资金规模(万元) (默认: 100)')
    parser.add_argument('--tech-score', type=int, default=60,
                       help='技术面最低评分 (默认: 60)')
    parser.add_argument('--fund-score', type=int, default=50,
                       help='基本面最低评分 (默认: 50)')
    parser.add_argument('--sent-score', type=int, default=50,
                       help='情绪资金最低评分 (默认: 50)')
    parser.add_argument('--code', type=str, help='分析指定合约代码')
    
    args = parser.parse_args()
    
    # 检查环境
    check_environment()
    
    # 导入模块
    import tushare as ts
    from futures_value_selector import FuturesValueSelector
    from value_scorer import FuturesValueScorer
    
    # 初始化 Tushare
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    # 分析指定合约
    if args.code:
        print(f"\n【合约深度分析】{args.code}")
        print()
        
        scorer = FuturesValueScorer(pro)
        result = scorer.calculate_comprehensive_score(args.code)
        
        print(f"综合评分: {result['total_score']}分")
        print(f"分级: {result['level']}")
        print(f"建议: {result['suggestion']}")
        print()
        print("【分项评分】")
        print(f"  技术面超卖: {result['tech_score']}/100 (权重25%)")
        print(f"  基本面价值: {result['fund_score']}/100 (权重40%)")
        print(f"  情绪资金: {result['sent_score']}/100 (权重25%)")
        print(f"  跨市场验证: {result['cross_score']}/10 (权重10%)")
        print()
        
        if 'details' in result:
            print("【详细信号】")
            print(f"  技术信号: {', '.join(result['details'].get('tech_signals', []))}")
            print(f"  基本面: {result['details'].get('fund_status', '')}")
            print(f"  情绪: {result['details'].get('sent_status', '')}")
        
        return
    
    # 执行选股流程
    print("=" * 80)
    print("商品期货价值抄底选股策略")
    print("=" * 80)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"资金规模: {args.capital}万")
    print(f"技术面最低评分: {args.tech_score}")
    print(f"基本面最低评分: {args.fund_score}")
    print(f"情绪资金最低评分: {args.sent_score}")
    print("=" * 80)
    print()
    
    selector = FuturesValueSelector(pro, total_capital=args.capital * 10000)
    result = selector.select_contracts(
        tech_min_score=args.tech_score,
        fund_min_score=args.fund_score,
        sent_min_score=args.sent_score
    )
    
    print("\n" + "=" * 80)
    print("运行完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
