#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股趋势跟踪主线选股策略 - 运行入口

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
    parser = argparse.ArgumentParser(description='A股趋势跟踪主线选股策略')
    parser.add_argument('-n', '--top-n', type=int, default=30, help='选出股票数量 (默认: 30)')
    parser.add_argument('-a', '--min-amount', type=float, default=1.0, help='最小日均成交额(亿元) (默认: 1.0)')
    parser.add_argument('--max-stocks', type=int, default=None, help='最大分析股票数量 (默认: 分析全部)')
    parser.add_argument('--step', type=int, choices=[1, 2, 3], help='只执行指定步骤')
    parser.add_argument('--industry', action='store_true', help='只显示行业集中度')
    parser.add_argument('--code', type=str, help='分析指定股票代码')
    
    args = parser.parse_args()
    
    # 检查环境
    check_environment()
    
    # 导入模块
    import tushare as ts
    from stock_selector import StockSelector
    from market_concentration import MarketConcentration
    from technical_indicators import TechnicalIndicators
    from multi_factor_scorer import MultiFactorScorer
    
    # 初始化 Tushare
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    print("=" * 80)
    print("A股趋势跟踪主线选股策略")
    print("=" * 80)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"参数: top_n={args.top_n}, min_amount={args.min_amount}亿, max_stocks={args.max_stocks or '全部'}")
    print("=" * 80)
    
    # 只显示行业集中度
    if args.industry:
        print("\n【行业集中度排名】")
        mc = MarketConcentration(pro)
        industries = mc.calculate_industry_concentration()
        if len(industries) > 0:
            print(industries.to_string(index=False))
        return
    
    # 分析指定股票
    if args.code:
        print(f"\n【个股分析】{args.code}")
        
        # 技术面分析
        ti = TechnicalIndicators(pro)
        tech = ti.get_technical_score(args.code)
        print(f"\n技术面评分: {tech['score']}/100")
        print(f"详细评分: {tech['detail_scores']}")
        print(f"MACD: DIF={tech['macd_info']['dif']}, DEA={tech['macd_info']['dea']}")
        print(f"均线排列: {tech['ma_info'].get('arrangement', 'unknown')}")
        print(f"风险信号: {tech['risks']}")
        
        # 综合评分
        scorer = MultiFactorScorer(pro)
        score = scorer.calculate_total_score(args.code)
        print(f"\n综合评分: {score['total_score']}/100")
        print(f"  - 趋势强度: {score['trend_score']['score']}/40")
        print(f"  - 资金认可: {score['fund_score']['score']}/30")
        print(f"  - 主线契合: {score['theme_score']['score']}/20")
        print(f"  - 风险调整: {score['risk_score']['score']}/10")
        return
    
    # 执行选股流程
    selector = StockSelector(pro)
    result = selector.select_stocks(top_n=args.top_n, min_amount=args.min_amount, max_stocks=args.max_stocks)
    
    # 保存结果到文件
    if len(result['selected_stocks']) > 0:
        output_file = f"stock_selection_{datetime.now().strftime('%Y%m%d')}.csv"
        result['selected_stocks'].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n选股结果已保存到: {output_file}")
    
    print("\n" + "=" * 80)
    print("运行完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
