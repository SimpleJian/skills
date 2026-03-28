#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分模型

维度：
- 估值安全（40%）
- 盈利质量（25%）
- 财务健康（20%）
- 成长潜力（15%）

分级：
- 核心池：≥80分
- 观察池：60-80分
- 备选池：40-60分
- 排除：<40分
"""

import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime

from valuation_filter import ValuationFilter
from quality_filter import QualityFilter
from growth_analyzer import GrowthAnalyzer


class ValueScorer:
    """价值选股评分器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.valuation = ValuationFilter(pro_api)
        self.quality = QualityFilter(pro_api)
        self.growth = GrowthAnalyzer(pro_api)
    
    def calculate_valuation_score(self, ts_code: str) -> Dict:
        """
        估值安全评分 (40分)
        
        - 滚动PE历史分位 (15分)
        - 滚动PB历史分位 (10分)
        - 股息率 (15分)
        """
        score_details = {}
        
        try:
            # 获取当前估值数据
            df_basic = self.pro.daily_basic(ts_code=ts_code)
            if df_basic is None or len(df_basic) == 0:
                return {'score': 0, 'details': {}}
            
            current = df_basic.iloc[0]
            pe = current.get('pe', 0)
            pb = current.get('pb', 0)
            dv_ratio = current.get('dv_ratio', 0)
            
            # PE历史分位评分 (15分)
            pe_percentile = self.valuation.get_pe_history_percentile(ts_code)
            if pe_percentile < 10:
                pe_score = 15
            elif pe_percentile < 30:
                pe_score = 12
            elif pe_percentile < 50:
                pe_score = 9
            elif pe_percentile < 80:
                pe_score = 6
            else:
                pe_score = 0
            score_details['pe_score'] = pe_score
            
            # PB评分 (10分)
            if pb < 0.5:
                pb_score = 10
            elif pb < 1.0:
                pb_score = 8
            elif pb < 1.5:
                pb_score = 6
            elif pb < 2.0:
                pb_score = 4
            else:
                pb_score = 0
            score_details['pb_score'] = pb_score
            
            # 股息率评分 (15分)
            if dv_ratio >= 8:
                div_score = 15
            elif dv_ratio >= 5:
                div_score = 12
            elif dv_ratio >= 4:
                div_score = 9
            elif dv_ratio >= 3:
                div_score = 6
            else:
                div_score = 0
            score_details['dividend_score'] = div_score
            
            # 分红可持续性加分
            div_check = self.valuation.check_dividend_sustainability(ts_code)
            if div_check['sustainable']:
                score_details['sustainability_bonus'] = 3
            
            total_score = sum(score_details.values())
            
            return {
                'score': min(total_score, 40),
                'details': score_details,
                'pe': pe,
                'pb': pb,
                'dv_ratio': dv_ratio,
                'pe_percentile': pe_percentile,
                'div_sustainable': div_check.get('sustainable', False)
            }
        
        except Exception as e:
            return {'score': 0, 'details': {}, 'error': str(e)}
    
    def calculate_quality_score(self, ts_code: str) -> Dict:
        """
        盈利质量评分 (25分)
        
        - 近三年平均ROE (15分)
        - 毛利率行业分位 (10分)
        """
        score_details = {}
        
        try:
            # ROE分析
            roe_analysis = self.quality.analyze_roe(ts_code)
            avg_roe = roe_analysis['avg_roe']
            
            if avg_roe >= 20:
                roe_score = 15
            elif avg_roe >= 15:
                roe_score = 12
            elif avg_roe >= 12:
                roe_score = 9
            elif avg_roe >= 10:
                roe_score = 6
            else:
                roe_score = 0
            
            # ROE稳定性调整
            if roe_analysis['roe_std'] > 5:
                roe_score -= 3
            
            score_details['roe_score'] = max(roe_score, 0)
            
            # 毛利率分析
            margin_analysis = self.quality.analyze_gross_margin(ts_code)
            avg_margin = margin_analysis['avg_gross_margin']
            
            if avg_margin >= 50:
                margin_score = 10
            elif avg_margin >= 40:
                margin_score = 8
            elif avg_margin >= 30:
                margin_score = 6
            elif avg_margin >= 20:
                margin_score = 4
            else:
                margin_score = 0
            
            # 稳定性调整
            if margin_analysis['stability'] == 'high':
                margin_score += 2
            elif margin_analysis['stability'] == 'low':
                margin_score -= 2
            
            score_details['margin_score'] = min(margin_score, 10)
            
            total_score = sum(score_details.values())
            
            return {
                'score': min(total_score, 25),
                'details': score_details,
                'roe': roe_analysis,
                'margin': margin_analysis
            }
        
        except Exception as e:
            return {'score': 0, 'details': {}, 'error': str(e)}
    
    def calculate_financial_health_score(self, ts_code: str) -> Dict:
        """
        财务健康评分 (20分)
        
        - 经营现金流/净利润 (10分)
        - 资产负债率 (10分)
        """
        score_details = {}
        
        try:
            # 现金流分析
            cashflow_analysis = self.quality.analyze_cashflow(ts_code)
            ocf_ratio = cashflow_analysis['ocf_to_profit_ratio']
            
            if ocf_ratio >= 100:
                cash_score = 10
            elif ocf_ratio >= 80:
                cash_score = 8
            elif ocf_ratio >= 60:
                cash_score = 6
            else:
                cash_score = 0
            
            # 连续正现金流加分
            if cashflow_analysis['ocf_positive_years'] >= 3:
                cash_score += 2
            
            score_details['cashflow_score'] = min(cash_score, 10)
            
            # 财务风险分析
            risk_analysis = self.quality.check_financial_risk(ts_code)
            debt_ratio = risk_analysis['debt_ratio']
            
            if debt_ratio < 40:
                debt_score = 10
            elif debt_ratio < 50:
                debt_score = 8
            elif debt_ratio < 60:
                debt_score = 6
            elif debt_ratio < 70:
                debt_score = 4
            else:
                debt_score = 0
            
            score_details['debt_score'] = debt_score
            
            total_score = sum(score_details.values())
            
            return {
                'score': min(total_score, 20),
                'details': score_details,
                'cashflow': cashflow_analysis,
                'risk': risk_analysis
            }
        
        except Exception as e:
            return {'score': 0, 'details': {}, 'error': str(e)}
    
    def calculate_growth_score(self, ts_code: str) -> Dict:
        """
        成长潜力评分 (15分)
        
        - 近三年净利润复合增长率 (10分)
        - 近三年营收复合增长率 (5分)
        """
        score_details = {}
        
        try:
            # 成长性分析
            growth_analysis = self.growth.comprehensive_growth_analysis(ts_code)
            growth_rates = growth_analysis['growth_rates']
            
            profit_cagr = growth_rates['profit_cagr']
            revenue_cagr = growth_rates['revenue_cagr']
            
            # 净利润增长评分 (10分)
            if profit_cagr >= 20:
                profit_score = 10
            elif profit_cagr >= 15:
                profit_score = 8
            elif profit_cagr >= 10:
                profit_score = 6
            elif profit_cagr >= 5:
                profit_score = 4
            else:
                profit_score = 0
            score_details['profit_growth_score'] = profit_score
            
            # 营收增长评分 (5分)
            if revenue_cagr >= 15:
                revenue_score = 5
            elif revenue_cagr >= 10:
                revenue_score = 4
            elif revenue_cagr >= 5:
                revenue_score = 3
            else:
                revenue_score = 0
            score_details['revenue_growth_score'] = revenue_score
            
            total_score = sum(score_details.values())
            
            return {
                'score': min(total_score, 15),
                'details': score_details,
                'growth': growth_analysis
            }
        
        except Exception as e:
            return {'score': 0, 'details': {}, 'error': str(e)}
    
    def calculate_total_score(self, ts_code: str) -> Dict:
        """
        计算综合评分
        """
        valuation = self.calculate_valuation_score(ts_code)
        quality = self.calculate_quality_score(ts_code)
        financial = self.calculate_financial_health_score(ts_code)
        growth = self.calculate_growth_score(ts_code)
        
        total_score = (
            valuation['score'] +
            quality['score'] +
            financial['score'] +
            growth['score']
        )
        
        # 分级
        if total_score >= 80:
            level = '核心池'
            suggestion = '优先配置，深度研究后可集中持仓'
        elif total_score >= 60:
            level = '观察池'
            suggestion = '持续跟踪，待瑕疵改善后介入'
        elif total_score >= 40:
            level = '备选池'
            suggestion = '关注特定催化因素'
        else:
            level = '排除'
            suggestion = '不符合价值抄底标准'
        
        return {
            'ts_code': ts_code,
            'total_score': round(total_score, 2),
            'level': level,
            'suggestion': suggestion,
            'valuation': valuation,
            'quality': quality,
            'financial': financial,
            'growth': growth
        }
    
    def get_pool_recommendation(self, score_result: Dict) -> str:
        """
        根据评分给出仓位建议
        """
        total_score = score_result['total_score']
        level = score_result['level']
        
        if level == '核心池':
            if total_score >= 90:
                return '核心仓位：可配置10-15%'
            else:
                return '核心仓位：可配置8-12%'
        elif level == '观察池':
            return '观察仓位：可配置3-5%'
        elif level == '备选池':
            return '备选关注：可配置1-3%'
        else:
            return '建议回避'


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    scorer = ValueScorer(pro)
    
    # 测试评分
    result = scorer.calculate_total_score('000001.SZ')
    
    print(f"综合评分: {result['total_score']}")
    print(f"分级: {result['level']}")
    print(f"建议: {result['suggestion']}")
    print(f"\n分项评分:")
    print(f"  估值安全: {result['valuation']['score']}/40")
    print(f"  盈利质量: {result['quality']['score']}/25")
    print(f"  财务健康: {result['financial']['score']}/20")
    print(f"  成长潜力: {result['growth']['score']}/15")
