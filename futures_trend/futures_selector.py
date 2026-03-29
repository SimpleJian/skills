#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品期货趋势跟踪选股策略 - 主选股模块

三层筛选框架：
1. 第一层：流动性门槛（日均成交≥10万手、持仓≥5万手）
2. 第二层：趋势方向判定（价格与均线关系、ADX>25）
3. 第三层：多维度趋势强度量化（动量30%、趋势30%、量价25%、波动15%）

组合构建：
- 3-5个核心品种（单品种上限20万）
- 2-3个观察备选
- 板块分散（同板块≤2个）
- 多空净敞口动态调整
"""

import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime

import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.data_quality import create_futures_processor
from tushare_utils.risk_tags import FuturesRiskAnalyzer, merge_issues_to_tags

from liquidity_filter import LiquidityFilter
from trend_direction import TrendDirection
from trend_strength import TrendStrength
from portfolio_builder import PortfolioBuilder


class FuturesSelector:
    """
    商品期货趋势跟踪选股器
    
    策略定位：进取型趋势跟踪，捕捉市场当前主线
    资金规模：100万
    风险偏好：高弹性收益，接受较大波动
    """
    
    def __init__(self, pro_api, total_capital: float = 1000000):
        self.pro = pro_api
        self.total_capital = total_capital
        
        # 初始化各模块
        self.liquidity = LiquidityFilter(pro_api)
        self.trend_dir = TrendDirection(pro_api)
        self.trend_strength = TrendStrength(pro_api)
        self.portfolio = PortfolioBuilder(total_capital)
        self.data_processor = create_futures_processor(pro_api)
        self.risk_analyzer = FuturesRiskAnalyzer(pro_api)
        self.contract_risk_tags = {}
    
    def select_contracts(self, market_env: str = '震荡', 
                        adx_threshold: float = 25) -> Dict:
        """
        执行完整选股流程
        
        Args:
            market_env: 市场环境（强牛/弱牛/震荡/弱熊/强熊）
            adx_threshold: ADX阈值
            
        Returns:
            选股结果
        """
        start_time = datetime.now()
        
        print()
        print("=" * 80)
        print("商品期货趋势跟踪选股策略")
        print("=" * 80)
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"资金规模: {self.total_capital/10000:.0f}万")
        print(f"风险偏好: 进取型")
        print(f"市场环境: {market_env}")
        print("=" * 80)
        print()
        print("策略逻辑: 三层筛选 + 综合评分")
        print("  第一层: 流动性门槛（日均成交≥10万手、持仓≥5万手）")
        print("  第二层: 趋势方向判定（均线排列、ADX>25）")
        print("  第三层: 多维度量化（动量30%、趋势30%、量价25%、波动15%）")
        print()
        
        # 第一层筛选：流动性
        df_liquidity = self.liquidity.filter_by_liquidity(top_n=40)
        
        if len(df_liquidity) == 0:
            print("警告：没有合约通过流动性筛选")
            return {}
        
        # 第二层筛选：趋势方向
        df_long, df_short = self.trend_dir.filter_by_trend(df_liquidity, adx_threshold)
        
        if len(df_long) == 0 and len(df_short) == 0:
            print("警告：没有合约通过趋势方向筛选")
            return {}
        
        # 第三层筛选：趋势强度量化评分
        print()
        print("=" * 70)
        print("第三层筛选：趋势强度量化")
        print("=" * 70)
        print()
        
        # 多头评分
        if len(df_long) > 0:
            print("多头候选评分...")
            long_scores = []
            for idx, row in df_long.iterrows():
                ts_code = row['ts_code']
                
                # 数据质量检查 + 风险标签
                price_df = None
                try:
                    price_df = self.pro.fut_daily(ts_code=ts_code, limit=60)
                except:
                    pass
                
                # 检查合约到期
                days_to_expiry = 999
                try:
                    _, expiry_tag = self.data_processor.check_contract_expiry(ts_code)
                    if expiry_tag:
                        # 解析天数
                        import re
                        match = re.search(r'(\d+)', expiry_tag)
                        if match:
                            days_to_expiry = int(match.group(1))
                except:
                    pass
                
                # 风险分析
                risk_generator = self.risk_analyzer.analyze_contract(ts_code, price_df, days_to_expiry)
                risk_tags = risk_generator.get_tags_string()
                self.contract_risk_tags[ts_code] = risk_tags
                
                # 若即将到期，跳过
                if days_to_expiry < 7:
                    continue
                
                result = self.trend_strength.calculate_comprehensive_score(ts_code, '多头')
                
                if result['total_score'] > 0:
                    long_scores.append({
                        'ts_code': ts_code,
                        'name': row['name'],
                        'sector': self.portfolio.get_commodity_sector(ts_code),
                        'total_score': result['total_score'],
                        'adx': row['adx'],
                        'direction': '多头',
                        'risk_tags': risk_tags
                    })
            
            df_long_scored = pd.DataFrame(long_scores)
            if len(df_long_scored) > 0:
                df_long_scored = df_long_scored.sort_values('total_score', ascending=False)
                print(f"多头评分完成: {len(df_long_scored)}只")
        else:
            df_long_scored = pd.DataFrame()
        
        # 空头评分
        if len(df_short) > 0:
            print()
            print("空头候选评分...")
            short_scores = []
            for idx, row in df_short.iterrows():
                ts_code = row['ts_code']
                
                # 数据质量检查 + 风险标签（复用多头的）
                risk_tags = self.contract_risk_tags.get(ts_code, "")
                
                # 检查合约到期
                days_to_expiry = 999
                try:
                    days_to_expiry, _ = self.data_processor.check_contract_expiry(ts_code)
                except:
                    pass
                
                # 若即将到期，跳过
                if days_to_expiry < 7:
                    continue
                
                result = self.trend_strength.calculate_comprehensive_score(ts_code, '空头')
                
                if result['total_score'] > 0:
                    short_scores.append({
                        'ts_code': ts_code,
                        'name': row['name'],
                        'sector': self.portfolio.get_commodity_sector(ts_code),
                        'total_score': result['total_score'],
                        'adx': row['adx'],
                        'direction': '空头',
                        'risk_tags': risk_tags
                    })
            
            df_short_scored = pd.DataFrame(short_scores)
            if len(df_short_scored) > 0:
                df_short_scored = df_short_scored.sort_values('total_score', ascending=False)
                print(f"空头评分完成: {len(df_short_scored)}只")
        else:
            df_short_scored = pd.DataFrame()
        
        # 组合构建
        portfolio = self.portfolio.build_portfolio(
            df_long_scored, df_short_scored, market_env
        )
        
        # 打印结果
        self.portfolio.print_portfolio(portfolio)
        
        # 完成
        print()
        print("=" * 80)
        print(f"选股完成！耗时: {(datetime.now() - start_time).total_seconds():.1f} 秒")
        print("=" * 80)
        
        return portfolio


if __name__ == '__main__':
    import tushare as ts
    import os
    
    # 初始化Tushare
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("请设置 TUSHARE_TOKEN 环境变量")
        exit(1)
    
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 创建选股器
    selector = FuturesSelector(pro, total_capital=1000000)
    
    # 执行选股
    result = selector.select_contracts(market_env='震荡', adx_threshold=25)
