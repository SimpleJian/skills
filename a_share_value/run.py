#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股价值抄底选股策略 - 运行入口

使用方法:
    python run.py
    
环境变量:
    TUSHARE_TOKEN - Tushare API Token (必需)
"""

import os
import sys
import argparse
import time
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
    parser = argparse.ArgumentParser(description='A股价值抄底选股策略')
    parser.add_argument('-p', '--max-pe', type=float, default=15, help='最大市盈率 (默认: 15)')
    parser.add_argument('-b', '--max-pb', type=float, default=1.5, help='最大市净率 (默认: 1.5)')
    parser.add_argument('-d', '--min-dividend', type=float, default=3.0, help='最小股息率%% (默认: 3.0)')
    parser.add_argument('-n', '--top-n', type=int, default=30, help='选出股票数量 (默认: 30)')
    parser.add_argument('--code', type=str, help='分析指定股票代码')
    
    args = parser.parse_args()
    
    # 检查环境
    check_environment()
    
    # 导入模块
    import tushare as ts
    from value_selector import ValueSelector
    from value_scorer import ValueScorer
    
    # 初始化 Tushare
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    print("=" * 80)
    print("A股价值抄底选股策略")
    print("=" * 80)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"参数: PE<{args.max_pe}, PB<{args.max_pb}, 股息率>{args.min_dividend}%")
    print("=" * 80)
    
    # 分析指定股票
    if args.code:
        print(f"\n【个股深度分析】{args.code}")
        
        scorer = ValueScorer(pro)
        result = scorer.calculate_total_score(args.code)
        
        # 获取基本信息
        df_basic = pro.stock_basic(ts_code=args.code)
        if df_basic is not None and len(df_basic) > 0:
            name = df_basic.iloc[0]['name']
            industry = df_basic.iloc[0]['industry']
            print(f"\n股票名称: {name}")
            print(f"所属行业: {industry}")
        
        print(f"\n综合评分: {result['total_score']}分")
        print(f"分级: {result['level']}")
        print(f"建议: {result['suggestion']}")
        
        print(f"\n【分项评分】")
        print(f"  估值安全: {result['valuation']['score']}/40分")
        print(f"    - PE: {result['valuation'].get('pe', 'N/A')}")
        print(f"    - PB: {result['valuation'].get('pb', 'N/A')}")
        print(f"    - 股息率: {result['valuation'].get('dv_ratio', 'N/A')}%")
        
        print(f"\n  盈利质量: {result['quality']['score']}/25分")
        if 'roe' in result['quality']:
            print(f"    - ROE: {result['quality']['roe'].get('avg_roe', 'N/A')}%")
        
        print(f"\n  财务健康: {result['financial']['score']}/20分")
        if 'risk' in result['financial']:
            print(f"    - 资产负债率: {result['financial']['risk'].get('debt_ratio', 'N/A')}%")
        
        print(f"\n  成长潜力: {result['growth']['score']}/15分")
        if 'growth' in result['growth']:
            gr = result['growth']['growth']
            if 'growth_rates' in gr:
                print(f"    - 净利润CAGR: {gr['growth_rates'].get('profit_cagr', 'N/A')}%")
        
        # 仓位建议
        recommendation = scorer.get_pool_recommendation(result)
        print(f"\n【仓位建议】{recommendation}")
        
        return
    
    # 执行选股流程
    print("\n注意：由于 Tushare API 频率限制，选股过程可能需要几分钟时间，请耐心等待...")
    print("      如果遇到频率限制，程序会自动等待并重试。\n")
    
    start_time = datetime.now()
    selector = ValueSelector(pro)
    result = selector.select_stocks(
        max_pe=args.max_pe,
        max_pb=args.max_pb,
        min_dividend_yield=args.min_dividend,
        top_n=args.top_n
    )
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n总耗时: {elapsed:.1f} 秒")
    
    # 保存结果到文件
    if len(result['selected_stocks']) > 0:
        output_file = f"value_stock_selection_{datetime.now().strftime('%Y%m%d')}.csv"
        result['selected_stocks'].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n选股结果已保存到: {output_file}")
    
    print("\n" + "=" * 80)
    print("运行完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
