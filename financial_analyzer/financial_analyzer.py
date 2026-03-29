#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务深度分析模块

提供杜邦分析、财务质量评分、同业比较等功能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import sys
import os

_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter


class FinancialAnalyzer:
    """财务分析器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def dupont_analysis(self, ts_code: str) -> Dict:
        """
        杜邦分析
        
        ROE = 净利润率 × 总资产周转率 × 权益乘数
        """
        try:
            # 获取财务指标
            @self.limiter.rate_limit
            def fetch():
                return self.pro.fina_indicator(ts_code=ts_code, limit=4)
            
            df = fetch()
            if df is None or df.empty:
                return {'error': '无法获取财务数据'}
            
            latest = df.iloc[0]
            
            # 杜邦分析三要素
            net_profit_margin = float(latest.get('q_sales_yoy', 0))  # 净利润率
            asset_turnover = float(latest.get('assets_turn', 0))      # 总资产周转率
            equity_multiplier = float(latest.get('debt_to_assets', 0))  # 权益乘数
            
            roe = net_profit_margin * asset_turnover * equity_multiplier if equity_multiplier else 0
            
            return {
                'roe': roe,
                'net_profit_margin': net_profit_margin,
                'asset_turnover': asset_turnover,
                'equity_multiplier': equity_multiplier,
                'breakdown': {
                    'profitability': net_profit_margin,
                    'efficiency': asset_turnover,
                    'leverage': equity_multiplier
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def financial_quality_score(self, ts_code: str) -> Dict:
        """
        财务质量评分
        """
        try:
            @self.limiter.rate_limit
            def fetch():
                return self.pro.fina_indicator(ts_code=ts_code, limit=8)
            
            df = fetch()
            if df is None or df.empty:
                return {'error': '无法获取财务数据'}
            
            scores = {}
            
            # 盈利质量
            roe = df['roe'].mean() if 'roe' in df.columns else 0
            scores['profitability'] = min(roe / 15 * 100, 100)  # ROE 15%为满分
            
            # 现金流质量
            ocf_ratio = df['ocf_to_profit'].mean() if 'ocf_to_profit' in df.columns else 0
            scores['cashflow'] = min(ocf_ratio * 100, 100)
            
            # 杠杆水平
            debt_ratio = df['debt_to_assets'].mean() if 'debt_to_assets' in df.columns else 0
            scores['leverage'] = max(0, (60 - debt_ratio) / 60 * 100)  # 负债率越低越好
            
            # 成长能力
            revenue_growth = df['q_sales_yoy'].mean() if 'q_sales_yoy' in df.columns else 0
            scores['growth'] = min(max(revenue_growth, 0), 100)
            
            # 总分
            total_score = np.mean(list(scores.values()))
            
            return {
                'total_score': total_score,
                'scores': scores,
                'grade': 'A' if total_score >= 80 else 'B' if total_score >= 60 else 'C'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def peer_comparison(self, ts_code: str) -> Dict:
        """
        同业比较
        """
        try:
            # 获取公司行业
            @self.limiter.rate_limit
            def fetch_basic():
                return self.pro.stock_basic(ts_code=ts_code)
            
            basic = fetch_basic()
            if basic is None or basic.empty:
                return {'error': '无法获取公司信息'}
            
            industry = basic.iloc[0].get('industry')
            
            # 获取同行业公司
            @self.limiter.rate_limit
            def fetch_peers():
                return self.pro.stock_basic(industry=industry)
            
            peers = fetch_peers()
            if peers is None or peers.empty or len(peers) < 5:
                return {'error': '同行业公司不足'}
            
            # 简化为返回行业信息
            return {
                'industry': industry,
                'peer_count': len(peers),
                'industry_avg_pe': None  # 需要额外计算
            }
        except Exception as e:
            return {'error': str(e)}


if __name__ == '__main__':
    print("财务分析模块")
