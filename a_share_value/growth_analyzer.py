#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长性分析模块 - 高阶筛选

核心指标：
- 收入与利润增长质量
- 增长驱动因素识别
- 错杀信号的定量识别
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


class GrowthAnalyzer:
    """成长性分析器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_income_data(self, ts_code: str) -> pd.DataFrame:
        """
        获取利润表数据
        """
        try:
            df = self.pro.income(ts_code=ts_code)
            if df is not None and len(df) > 0:
                df = df.sort_values('end_date', ascending=False)
                return df
        except:
            pass
        return pd.DataFrame()
    
    def calculate_growth_rates(self, ts_code: str, years: int = 3) -> Dict:
        """
        计算增长率
        
        Returns:
            {
                'revenue_cagr': 营收复合增长率,
                'profit_cagr': 净利润复合增长率,
                'revenue_quality': 营收增长质量,
                'profit_quality': 利润增长质量
            }
        """
        df_income = self.get_income_data(ts_code)
        
        if len(df_income) < years:
            return {
                'revenue_cagr': 0,
                'profit_cagr': 0,
                'revenue_quality': 'low',
                'profit_quality': 'low'
            }
        
        df = df_income.head(years)
        
        # 营业收入
        revenue_values = df['total_revenue'].astype(float).values
        # 净利润（扣非）
        profit_col = 'deduct_income' if 'deduct_income' in df.columns else 'net_profit'
        profit_values = df[profit_col].astype(float).values
        
        # 计算CAGR
        if len(revenue_values) >= 2 and revenue_values[-1] > 0:
            revenue_cagr = (revenue_values[0] / revenue_values[-1]) ** (1 / (len(revenue_values) - 1)) - 1
        else:
            revenue_cagr = 0
        
        if len(profit_values) >= 2 and profit_values[-1] > 0:
            profit_cagr = (profit_values[0] / profit_values[-1]) ** (1 / (len(profit_values) - 1)) - 1
        else:
            profit_cagr = 0
        
        # 增长质量判断
        # 营收质量
        if revenue_cagr >= 0.20:
            revenue_quality = 'excellent'
        elif revenue_cagr >= 0.15:
            revenue_quality = 'good'
        elif revenue_cagr >= 0.10:
            revenue_quality = 'acceptable'
        else:
            revenue_quality = 'low'
        
        # 利润质量
        if profit_cagr >= 0.20:
            profit_quality = 'excellent'
        elif profit_cagr >= 0.15:
            profit_quality = 'good'
        elif profit_cagr >= 0.10:
            profit_quality = 'acceptable'
        else:
            profit_quality = 'low'
        
        return {
            'revenue_cagr': round(revenue_cagr * 100, 2),
            'profit_cagr': round(profit_cagr * 100, 2),
            'revenue_quality': revenue_quality,
            'profit_quality': profit_quality
        }
    
    def analyze_growth_drivers(self, ts_code: str) -> Dict:
        """
        分析增长驱动因素
        
        1. 量价齐升（最理想）
        2. 量增价稳
        3. 量稳价升
        4. 量增价跌（警惕）
        """
        df_income = self.get_income_data(ts_code)
        
        if len(df_income) < 2:
            return {'driver_type': 'unknown', 'quality': 'low'}
        
        df = df_income.head(2)
        
        # 收入变化
        revenue_change = (df.iloc[0]['total_revenue'] - df.iloc[1]['total_revenue']) / df.iloc[1]['total_revenue']
        
        # 毛利率变化（作为价格的代理）
        df_fina = self.pro.fina_indicator(ts_code=ts_code)
        if df_fina is not None and len(df_fina) >= 2:
            margin_current = float(df_fina.iloc[0].get('grossprofit_margin', 0))
            margin_prev = float(df_fina.iloc[1].get('grossprofit_margin', 0))
            margin_change = margin_current - margin_prev
        else:
            margin_change = 0
        
        # 驱动类型判断
        if revenue_change > 0.1 and margin_change > 1:
            driver_type = '量价齐升'
            quality = 'excellent'
        elif revenue_change > 0.1 and abs(margin_change) < 2:
            driver_type = '量增价稳'
            quality = 'good'
        elif abs(revenue_change) < 0.1 and margin_change > 1:
            driver_type = '量稳价升'
            quality = 'good'
        elif revenue_change > 0.1 and margin_change < -2:
            driver_type = '量增价跌'
            quality = 'warning'
        else:
            driver_type = '其他'
            quality = 'unknown'
        
        return {
            'driver_type': driver_type,
            'quality': quality,
            'revenue_change': round(revenue_change * 100, 2),
            'margin_change': round(margin_change, 2)
        }
    
    def detect_mispricing(self, ts_code: str) -> Dict:
        """
        检测错杀信号
        
        信号：
        1. 当前PE较近三年均值折价 > 30%
        2. 机构持股比例变化与基本面背离
        3. 市场情绪极端指标
        """
        signals = []
        
        try:
            # 1. PE折价分析
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now().replace(year=datetime.now().year - 3)).strftime('%Y%m%d')
            
            df_basic = self.pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df_basic is not None and len(df_basic) > 60:
                current_pe = df_basic.iloc[0]['pe']
                avg_pe = df_basic['pe'].mean()
                
                if current_pe > 0 and avg_pe > 0:
                    pe_discount = (avg_pe - current_pe) / avg_pe * 100
                    
                    if pe_discount > 50:
                        signals.append({'type': 'PE深度折价', 'value': f'{pe_discount:.1f}%', 'level': 'strong'})
                    elif pe_discount > 30:
                        signals.append({'type': 'PE显著折价', 'value': f'{pe_discount:.1f}%', 'level': 'medium'})
            
            # 2. 业绩与股价背离
            # 简化处理：检查最近一季利润增长
            df_fina = self.pro.fina_indicator(ts_code=ts_code)
            if df_fina is not None and len(df_fina) >= 2:
                profit_current = float(df_fina.iloc[0].get('netprofit_deducted', 0))
                profit_prev = float(df_fina.iloc[1].get('netprofit_deducted', 0))
                
                if profit_prev > 0:
                    profit_growth = (profit_current - profit_prev) / profit_prev * 100
                    
                    if profit_growth > 20:
                        signals.append({'type': '业绩高增长', 'value': f'{profit_growth:.1f}%', 'level': 'info'})
            
            # 3. 股息率异常（高股息+低估值）
            df_daily = self.pro.daily_basic(ts_code=ts_code)
            if df_daily is not None and len(df_daily) > 0:
                pe = df_daily.iloc[0].get('pe', 0)
                dv_ratio = df_daily.iloc[0].get('dv_ratio', 0)
                
                if pe < 10 and dv_ratio > 5:
                    signals.append({'type': '高股息低估值', 'value': f'PE{pe:.1f}/股息率{dv_ratio:.1f}%', 'level': 'strong'})
        
        except:
            pass
        
        # 错杀评分
        score = 0
        for signal in signals:
            if signal['level'] == 'strong':
                score += 30
            elif signal['level'] == 'medium':
                score += 20
            elif signal['level'] == 'info':
                score += 10
        
        return {
            'mispricing_signals': signals,
            'mispricing_score': min(score, 100),
            'is_mispriced': score >= 30
        }
    
    def comprehensive_growth_analysis(self, ts_code: str) -> Dict:
        """
        综合成长性分析
        """
        growth_rates = self.calculate_growth_rates(ts_code)
        growth_drivers = self.analyze_growth_drivers(ts_code)
        mispricing = self.detect_mispricing(ts_code)
        
        # 综合评分
        score = 0
        
        # 增长率评分 (60分)
        if growth_rates['profit_cagr'] >= 20:
            score += 40
        elif growth_rates['profit_cagr'] >= 15:
            score += 35
        elif growth_rates['profit_cagr'] >= 10:
            score += 25
        elif growth_rates['profit_cagr'] >= 5:
            score += 15
        
        if growth_rates['revenue_cagr'] >= 15:
            score += 20
        elif growth_rates['revenue_cagr'] >= 10:
            score += 15
        elif growth_rates['revenue_cagr'] >= 5:
            score += 10
        
        # 驱动质量评分 (20分)
        if growth_drivers['quality'] == 'excellent':
            score += 20
        elif growth_drivers['quality'] == 'good':
            score += 15
        elif growth_drivers['quality'] == 'acceptable':
            score += 10
        
        # 错杀信号评分 (20分)
        score += mispricing['mispricing_score'] * 0.2
        
        return {
            'ts_code': ts_code,
            'growth_score': round(score, 2),
            'growth_rates': growth_rates,
            'growth_drivers': growth_drivers,
            'mispricing': mispricing,
            'pass': score >= 50
        }


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    ga = GrowthAnalyzer(pro)
    
    # 测试
    result = ga.comprehensive_growth_analysis('000001.SZ')
    print(f"成长评分: {result['growth_score']}")
    print(f"增长率: {result['growth_rates']}")
    print(f"驱动因素: {result['growth_drivers']}")
    print(f"错杀信号: {result['mispricing']}")
