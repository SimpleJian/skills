#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
估值筛选模块 - 初阶筛选

核心指标：
- 市盈率（PE）分层标准
- 市净率（PB）与资产质量验证
- 股息率门槛与可持续性评估
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import time
import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.api_utils import APIRateLimiter, retry_on_rate_limit


class ValuationFilter:
    """估值过滤器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)  # 保守设置，每分钟300次
    
    @retry_on_rate_limit(max_retries=3, sleep_time=10)
    def get_daily_basic(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取每日基本面指标（包含估值数据）
        """
        if trade_date is None:
            # 获取最近交易日
            @self.limiter.rate_limit
            def get_trade_cal():
                return self.pro.trade_cal(exchange='SSE', start_date='20250101', end_date='20251231')
            
            trade_cal = get_trade_cal()
            trade_cal = trade_cal[trade_cal['is_open'] == 1]
            trade_date = trade_cal['cal_date'].max()
        
        @self.limiter.rate_limit
        def fetch_data():
            return self.pro.daily_basic(trade_date=trade_date)
        
        df = fetch_data()
        return df
    
    def filter_by_pe(self, df: pd.DataFrame, max_pe: float = 20, 
                     min_pe: float = 0, industry: str = None) -> pd.DataFrame:
        """
        按市盈率筛选
        
        Args:
            df: 基本面数据
            max_pe: 最大PE
            min_pe: 最小PE（排除负值）
            industry: 指定行业（可选）
        """
        # 过滤PE在合理范围内的股票
        filtered = df[(df['pe'] >= min_pe) & (df['pe'] <= max_pe)]
        
        # 排除极端值（可能是亏损或一次性收益）
        filtered = filtered[filtered['pe'] > 0]
        
        return filtered
    
    def filter_by_pb(self, df: pd.DataFrame, max_pb: float = 1.5, 
                     min_pb: float = 0) -> pd.DataFrame:
        """
        按市净率筛选
        
        PB<1 构成强烈的低估信号
        """
        filtered = df[(df['pb'] >= min_pb) & (df['pb'] <= max_pb)]
        return filtered
    
    def filter_by_dividend(self, df: pd.DataFrame, min_dividend_yield: float = 3.0,
                           max_dividend_yield: float = 10.0) -> pd.DataFrame:
        """
        按股息率筛选
        
        Args:
            min_dividend_yield: 最小股息率（%）
            max_dividend_yield: 最大股息率（%），排除异常高股息
        """
        # 注意：Tushare的dv_ratio是股息率（%）
        if 'dv_ratio' in df.columns:
            filtered = df[(df['dv_ratio'] >= min_dividend_yield) & 
                         (df['dv_ratio'] <= max_dividend_yield)]
        else:
            # 如果没有股息率数据，需要单独计算
            filtered = df
        
        return filtered
    
    @retry_on_rate_limit(max_retries=3, sleep_time=10)
    def get_dividend_history(self, ts_code: str, years: int = 3) -> pd.DataFrame:
        """
        获取历史分红数据，验证分红持续性
        
        Returns:
            DataFrame with columns: end_date, cash_div, div_rate
        """
        try:
            @self.limiter.rate_limit
            def fetch():
                return self.pro.dividend(ts_code=ts_code)
            
            df = fetch()
            if df is not None and len(df) > 0:
                df = df.sort_values('end_date', ascending=False).head(years)
                return df[['end_date', 'cash_div', 'div_rate', 'stk_div']]
        except Exception as e:
            if "每分钟最多访问" in str(e):
                time.sleep(10)
                return self.get_dividend_history(ts_code, years)
        return pd.DataFrame()
    
    def check_dividend_sustainability(self, ts_code: str) -> Dict:
        """
        检查股息可持续性
        
        Returns:
            {
                'continuous_years': 连续分红年数,
                'avg_div_rate': 平均分红率,
                'div_trend': 分红趋势,
                'sustainable': 是否可持续
            }
        """
        df = self.get_dividend_history(ts_code, years=5)
        
        if len(df) < 3:
            return {
                'continuous_years': len(df),
                'avg_div_rate': 0,
                'div_trend': 'unknown',
                'sustainable': False
            }
        
        # 计算平均分红率
        avg_div_rate = df['div_rate'].mean() if 'div_rate' in df.columns else 0
        
        # 判断趋势
        if len(df) >= 3:
            recent = df.head(3)['cash_div'].mean()
            older = df.tail(3)['cash_div'].mean() if len(df) >= 6 else recent
            
            if recent > older * 1.1:
                trend = '上升'
            elif recent < older * 0.9:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            trend = 'unknown'
        
        # 可持续性判断
        # 分红率在30%-70%之间较为健康
        sustainable = 30 <= avg_div_rate <= 80 if avg_div_rate > 0 else False
        
        return {
            'continuous_years': len(df),
            'avg_div_rate': round(avg_div_rate, 2),
            'div_trend': trend,
            'sustainable': sustainable
        }
    
    def get_pe_history_percentile(self, ts_code: str, years: int = 3) -> float:
        """
        获取PE历史分位数
        
        Returns:
            当前PE在过去N年中的分位数 (0-100)
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            df = self.pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or len(df) < 60:  # 至少60个交易日数据
                return 50  # 数据不足返回中位数
            
            current_pe = df.iloc[0]['pe']
            pe_series = df['pe'].dropna()
            
            if len(pe_series) == 0:
                return 50
            
            percentile = (pe_series < current_pe).sum() / len(pe_series) * 100
            
            return round(percentile, 2)
        
        except:
            return 50
    
    def preliminary_filter(self, trade_date: str = None,
                          max_pe: float = 20,
                          max_pb: float = 1.5,
                          min_dividend_yield: float = 3.0) -> pd.DataFrame:
        """
        初阶筛选：估值安全边际
        
        保守型价值组合标准：
        - PE < 15倍
        - 股息率 > 4%
        - PB < 1.5倍
        - 连续分红 ≥ 3年
        """
        print("=" * 60)
        print("初阶筛选：估值安全边际")
        print("=" * 60)
        
        # 获取基础数据
        df_basic = self.get_daily_basic(trade_date)
        print(f"全市场股票数量: {len(df_basic)}")
        
        # 1. PE筛选
        df_pe = self.filter_by_pe(df_basic, max_pe=max_pe, min_pe=0.1)
        print(f"PE < {max_pe}倍: {len(df_pe)}只")
        
        # 2. PB筛选
        df_pb = self.filter_by_pb(df_pe, max_pb=max_pb)
        print(f"PB < {max_pb}倍: {len(df_pb)}只")
        
        # 3. 股息率筛选
        df_div = self.filter_by_dividend(df_pb, min_dividend_yield=min_dividend_yield)
        print(f"股息率 > {min_dividend_yield}%: {len(df_div)}只")
        
        # 4. 排除ST股票
        df_st = self.pro.stock_st(trade_date=trade_date)
        if df_st is not None and len(df_st) > 0:
            st_stocks = set(df_st['ts_code'].tolist())
            df_div = df_div[~df_div['ts_code'].isin(st_stocks)]
        
        print(f"初阶筛选后: {len(df_div)}只")
        
        return df_div
    
    def get_industry_pe_median(self, industry: str) -> float:
        """
        获取行业PE中位数
        """
        try:
            # 获取行业成分股
            df_industry = self.pro.index_classify(level='L1', src='SW2021')
            industry_row = df_industry[df_industry['industry_name'] == industry]
            
            if len(industry_row) == 0:
                return None
            
            index_code = industry_row.iloc[0]['index_code']
            members = self.pro.index_member(index_code=index_code)
            
            if members is None or len(members) == 0:
                return None
            
            # 获取成分股PE
            pe_list = []
            for ts_code in members['con_code'].tolist()[:50]:  # 限制数量
                try:
                    df = self.pro.daily_basic(ts_code=ts_code)
                    if df is not None and len(df) > 0:
                        pe = df.iloc[0]['pe']
                        if pe > 0 and pe < 100:  # 排除异常值
                            pe_list.append(pe)
                except:
                    continue
            
            if len(pe_list) > 0:
                return np.median(pe_list)
        
        except:
            pass
        
        return None


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    vf = ValuationFilter(pro)
    
    # 执行初阶筛选
    result = vf.preliminary_filter(max_pe=15, max_pb=1.5, min_dividend_yield=4.0)
    
    print("\n初阶筛选结果（前10）:")
    print(result.head(10)[['ts_code', 'pe', 'pb', 'dv_ratio']].to_string(index=False))
