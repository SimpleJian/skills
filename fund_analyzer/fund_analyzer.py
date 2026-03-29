#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金分析模块

提供基金筛选、业绩分析、持仓穿透等功能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import sys
import os

_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter


class FundAnalyzer:
    """基金分析器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def filter_funds(self, fund_type: str = 'E', min_nav: float = 1.0) -> pd.DataFrame:
        """
        筛选基金
        
        Args:
            fund_type: 基金类型 E-股票型, M-混合型
            min_nav: 最小净值
        """
        try:
            @self.limiter.rate_limit
            def fetch():
                return self.pro.fund_basic(market='E', status='L')
            
            df = fetch()
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 筛选
            df = df[df['fund_type'] == fund_type]
            
            return df
        except Exception as e:
            print(f"筛选基金失败: {e}")
            return pd.DataFrame()
    
    def analyze_fund_performance(self, fund_code: str) -> Dict:
        """
        分析基金业绩
        """
        try:
            # 获取净值数据
            @self.limiter.rate_limit
            def fetch():
                return self.pro.fund_nav(ts_code=fund_code, limit=252)
            
            df = fetch()
            if df is None or df.empty:
                return {'error': '无法获取净值数据'}
            
            df = df.sort_values('end_date')
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['return'] = df['nav'].pct_change()
            
            # 计算指标
            total_return = (df['nav'].iloc[-1] / df['nav'].iloc[0] - 1) * 100
            annual_return = (1 + total_return/100) ** (252 / len(df)) - 1
            volatility = df['return'].std() * np.sqrt(252) * 100
            sharpe = annual_return * 100 / volatility if volatility > 0 else 0
            
            # 最大回撤
            cumulative = (1 + df['return']).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min() * 100
            
            return {
                'total_return': total_return,
                'annual_return': annual_return * 100,
                'volatility': volatility,
                'sharpe': sharpe,
                'max_drawdown': max_drawdown
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_fund_portfolio(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金持仓
        """
        try:
            @self.limiter.rate_limit
            def fetch():
                return self.pro.fund_portfolio(ts_code=fund_code)
            
            df = fetch()
            if df is None or df.empty:
                return pd.DataFrame()
            
            return df
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return pd.DataFrame()


if __name__ == '__main__':
    print("基金分析模块")
