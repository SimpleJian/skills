#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
质量筛选模块 - 精阶筛选

核心指标：
- ROE（净资产收益率）质量分析
- 毛利率与竞争优势识别
- 经营性现金流（OCF）硬性要求
- 财务风险排雷
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


class QualityFilter:
    """质量过滤器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_financial_indicators(self, ts_code: str) -> pd.DataFrame:
        """
        获取财务指标数据
        
        包含：ROE、毛利率、净利率等
        """
        try:
            df = self.pro.fina_indicator(ts_code=ts_code)
            if df is not None and len(df) > 0:
                df = df.sort_values('end_date', ascending=False)
                return df
        except:
            pass
        return pd.DataFrame()
    
    def get_cashflow_data(self, ts_code: str) -> pd.DataFrame:
        """
        获取现金流量表数据
        """
        try:
            df = self.pro.cashflow(ts_code=ts_code)
            if df is not None and len(df) > 0:
                df = df.sort_values('end_date', ascending=False)
                return df
        except:
            pass
        return pd.DataFrame()
    
    def get_balance_sheet(self, ts_code: str) -> pd.DataFrame:
        """
        获取资产负债表数据
        """
        try:
            df = self.pro.balancesheet(ts_code=ts_code)
            if df is not None and len(df) > 0:
                df = df.sort_values('end_date', ascending=False)
                return df
        except:
            pass
        return pd.DataFrame()
    
    def analyze_roe(self, ts_code: str, years: int = 3) -> Dict:
        """
        分析ROE质量
        
        标准：连续3年ROE > 15%
        
        Returns:
            {
                'avg_roe': 平均ROE,
                'min_roe': 最低ROE,
                'roe_std': ROE波动,
                'roe_trend': ROE趋势,
                'meet_standard': 是否达标,
                'quality': ROE质量
            }
        """
        df = self.get_financial_indicators(ts_code)
        
        if len(df) < years:
            return {
                'avg_roe': 0,
                'min_roe': 0,
                'roe_std': 0,
                'roe_trend': 'unknown',
                'meet_standard': False,
                'quality': 'low'
            }
        
        df = df.head(years)
        
        # 使用净资产收益率（扣非）
        roe_col = 'roe_dt' if 'roe_dt' in df.columns else 'roe'
        roe_values = df[roe_col].astype(float).values
        
        avg_roe = np.mean(roe_values)
        min_roe = np.min(roe_values)
        roe_std = np.std(roe_values)
        
        # 趋势判断
        if len(roe_values) >= 3:
            if roe_values[0] > roe_values[-1] * 1.05:
                trend = '上升'
            elif roe_values[0] < roe_values[-1] * 0.95:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            trend = 'unknown'
        
        # 是否达标：平均ROE > 15% 且 最低ROE > 10%
        meet_standard = (avg_roe >= 15) and (min_roe >= 10)
        
        # 质量评级
        if avg_roe >= 20 and roe_std < 3:
            quality = 'excellent'
        elif avg_roe >= 15 and roe_std < 5:
            quality = 'good'
        elif avg_roe >= 12:
            quality = 'acceptable'
        else:
            quality = 'low'
        
        return {
            'avg_roe': round(avg_roe, 2),
            'min_roe': round(min_roe, 2),
            'roe_std': round(roe_std, 2),
            'roe_trend': trend,
            'meet_standard': meet_standard,
            'quality': quality
        }
    
    def analyze_gross_margin(self, ts_code: str, years: int = 3) -> Dict:
        """
        分析毛利率
        
        标准：制造业 > 30%，消费/科技服务 > 50%
        """
        df = self.get_financial_indicators(ts_code)
        
        if len(df) < years:
            return {
                'avg_gross_margin': 0,
                'margin_std': 0,
                'margin_trend': 'unknown',
                'stability': 'low'
            }
        
        df = df.head(years)
        
        # 毛利率
        if 'grossprofit_margin' in df.columns:
            margin_values = df['grossprofit_margin'].astype(float).values
        elif 'gross_margin' in df.columns:
            margin_values = df['gross_margin'].astype(float).values
        else:
            return {
                'avg_gross_margin': 0,
                'margin_std': 0,
                'margin_trend': 'unknown',
                'stability': 'low'
            }
        
        avg_margin = np.mean(margin_values)
        margin_std = np.std(margin_values)
        
        # 趋势
        if len(margin_values) >= 3:
            if margin_values[0] > margin_values[-1] * 1.02:
                trend = '上升'
            elif margin_values[0] < margin_values[-1] * 0.98:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            trend = 'unknown'
        
        # 稳定性：波动 < 5个百分点
        stability = 'high' if margin_std < 3 else ('medium' if margin_std < 5 else 'low')
        
        return {
            'avg_gross_margin': round(avg_margin, 2),
            'margin_std': round(margin_std, 2),
            'margin_trend': trend,
            'stability': stability
        }
    
    def analyze_cashflow(self, ts_code: str, years: int = 3) -> Dict:
        """
        分析现金流质量
        
        标准：
        1. 经营现金流连续3年 > 0
        2. 经营现金流/净利润 > 80%
        """
        df_cash = self.get_cashflow_data(ts_code)
        df_fina = self.get_financial_indicators(ts_code)
        
        if len(df_cash) < years or len(df_fina) < years:
            return {
                'ocf_positive_years': 0,
                'ocf_to_profit_ratio': 0,
                'ocf_trend': 'unknown',
                'quality': 'low',
                'meet_standard': False
            }
        
        # 经营现金流净额
        ocf_col = 'n_cashflow_act' if 'n_cashflow_act' in df_cash.columns else None
        if ocf_col is None:
            return {
                'ocf_positive_years': 0,
                'ocf_to_profit_ratio': 0,
                'ocf_trend': 'unknown',
                'quality': 'low',
                'meet_standard': False
            }
        
        df_cash = df_cash.head(years)
        df_fina = df_fina.head(years)
        
        ocf_values = df_cash[ocf_col].astype(float).values
        profit_values = df_fina['netprofit_deducted' if 'netprofit_deducted' in df_fina.columns else 'netprofit'].astype(float).values
        
        # 正现金流年数
        positive_years = (ocf_values > 0).sum()
        
        # 经营现金流/净利润
        total_ocf = np.sum(ocf_values)
        total_profit = np.sum(profit_values)
        ocf_to_profit = (total_ocf / total_profit * 100) if total_profit > 0 else 0
        
        # 趋势
        if len(ocf_values) >= 3:
            if ocf_values[0] > ocf_values[-1] * 1.2:
                trend = '上升'
            elif ocf_values[0] < ocf_values[-1] * 0.8:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            trend = 'unknown'
        
        # 质量判断
        if positive_years >= years and ocf_to_profit >= 100:
            quality = 'excellent'
        elif positive_years >= years and ocf_to_profit >= 80:
            quality = 'good'
        elif positive_years >= years - 1 and ocf_to_profit >= 60:
            quality = 'acceptable'
        else:
            quality = 'low'
        
        meet_standard = (positive_years >= years) and (ocf_to_profit >= 80)
        
        return {
            'ocf_positive_years': int(positive_years),
            'ocf_to_profit_ratio': round(ocf_to_profit, 2),
            'ocf_trend': trend,
            'quality': quality,
            'meet_standard': meet_standard
        }
    
    def check_financial_risk(self, ts_code: str) -> Dict:
        """
        财务风险排雷
        
        检查：
        1. 资产负债率 < 60%
        2. 流动比率 > 1.5
        3. 商誉/净资产 < 20%
        """
        df_balance = self.get_balance_sheet(ts_code)
        
        if len(df_balance) == 0:
            return {
                'debt_ratio': 0,
                'current_ratio': 0,
                'goodwill_ratio': 0,
                'risk_level': 'unknown',
                'safe': False
            }
        
        latest = df_balance.iloc[0]
        
        # 资产负债率
        total_assets = float(latest.get('total_assets', 0))
        total_liab = float(latest.get('total_liab', 0))
        debt_ratio = (total_liab / total_assets * 100) if total_assets > 0 else 0
        
        # 流动比率
        total_cur_assets = float(latest.get('total_cur_assets', 0))
        total_cur_liab = float(latest.get('total_cur_liab', 0))
        current_ratio = (total_cur_assets / total_cur_liab) if total_cur_liab > 0 else 0
        
        # 商誉比例
        goodwill = float(latest.get('goodwill', 0))
        goodwill_ratio = (goodwill / total_assets * 100) if total_assets > 0 else 0
        
        # 风险评级
        risks = []
        if debt_ratio > 70:
            risks.append('高负债')
        if current_ratio < 1:
            risks.append('流动性紧张')
        if goodwill_ratio > 20:
            risks.append('高商誉风险')
        
        if len(risks) == 0:
            risk_level = 'low'
        elif len(risks) == 1:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # 安全标准
        safe = (debt_ratio < 60) and (current_ratio > 1.5) and (goodwill_ratio < 20)
        
        return {
            'debt_ratio': round(debt_ratio, 2),
            'current_ratio': round(current_ratio, 2),
            'goodwill_ratio': round(goodwill_ratio, 2),
            'risk_level': risk_level,
            'risks': risks,
            'safe': safe
        }
    
    def comprehensive_quality_check(self, ts_code: str) -> Dict:
        """
        综合质量检查
        """
        roe_analysis = self.analyze_roe(ts_code)
        margin_analysis = self.analyze_gross_margin(ts_code)
        cashflow_analysis = self.analyze_cashflow(ts_code)
        risk_analysis = self.check_financial_risk(ts_code)
        
        # 综合评分
        score = 0
        
        # ROE评分 (40分)
        if roe_analysis['avg_roe'] >= 20:
            score += 40
        elif roe_analysis['avg_roe'] >= 15:
            score += 35
        elif roe_analysis['avg_roe'] >= 12:
            score += 25
        elif roe_analysis['avg_roe'] >= 10:
            score += 15
        
        # 毛利率评分 (20分)
        if margin_analysis['avg_gross_margin'] >= 50:
            score += 20
        elif margin_analysis['avg_gross_margin'] >= 40:
            score += 18
        elif margin_analysis['avg_gross_margin'] >= 30:
            score += 15
        elif margin_analysis['avg_gross_margin'] >= 20:
            score += 10
        
        # 现金流评分 (20分)
        if cashflow_analysis['quality'] == 'excellent':
            score += 20
        elif cashflow_analysis['quality'] == 'good':
            score += 18
        elif cashflow_analysis['quality'] == 'acceptable':
            score += 12
        
        # 财务安全评分 (20分)
        if risk_analysis['safe']:
            score += 20
        elif risk_analysis['risk_level'] == 'medium':
            score += 10
        
        return {
            'ts_code': ts_code,
            'quality_score': score,
            'roe': roe_analysis,
            'gross_margin': margin_analysis,
            'cashflow': cashflow_analysis,
            'risk': risk_analysis,
            'pass': score >= 70 and risk_analysis['safe']
        }


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    qf = QualityFilter(pro)
    
    # 测试
    result = qf.comprehensive_quality_check('000001.SZ')
    print(f"质量评分: {result['quality_score']}")
    print(f"ROE分析: {result['roe']}")
    print(f"现金流: {result['cashflow']}")
    print(f"风险: {result['risk']}")
