#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情集中度指标计算模块

行情集中度 = 涨幅前30%个股涨幅均值 − 全市场涨幅中位数
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from datetime import datetime, timedelta


class MarketConcentration:
    """行情集中度计算器"""
    
    def __init__(self, pro_api):
        """
        初始化
        
        Args:
            pro_api: Tushare pro_api 实例
        """
        self.pro = pro_api
    
    def calculate_concentration(self, trade_date: str = None) -> Dict:
        """
        计算指定日期的行情集中度指标
        
        Args:
            trade_date: 交易日期 (YYYYMMDD格式)，默认为最近交易日
            
        Returns:
            Dict: 包含集中度指标和分市场统计
        """
        if trade_date is None:
            # 获取最近交易日
            trade_cal = self.pro.trade_cal(exchange='SSE', start_date='20250101', 
                                           end_date='20251231')
            trade_cal = trade_cal[trade_cal['is_open'] == 1]
            trade_date = trade_cal['cal_date'].max()
        
        # 获取当日全部A股涨跌幅数据
        df_daily = self.pro.daily(trade_date=trade_date)
        df_basic = self.pro.stock_basic(list_status='L')
        
        # 过滤ST/*ST股票和退市股票
        df_daily = df_daily[~df_daily['ts_code'].str.contains('ST')]
        
        # 计算涨跌幅 (基于收盘价)
        # 需要前一日数据计算涨幅
        prev_date = self._get_prev_trade_date(trade_date)
        if prev_date:
            df_prev = self.pro.daily(trade_date=prev_date)
            df_daily = df_daily.merge(df_prev[['ts_code', 'close']], on='ts_code', 
                                     suffixes=('', '_prev'), how='left')
            df_daily['pct_change'] = (df_daily['close'] / df_daily['close_prev'] - 1) * 100
        else:
            # 使用当日涨跌额估算
            df_daily['pct_change'] = df_daily['change'] / (df_daily['close'] - df_daily['change']) * 100
        
        # 过滤无效数据
        df_daily = df_daily[df_daily['pct_change'].notna()]
        
        if len(df_daily) == 0:
            return {'concentration': 0, 'top30_mean': 0, 'median': 0, 'count': 0}
        
        # 计算行情集中度
        total_count = len(df_daily)
        top30_count = int(total_count * 0.3)
        
        # 涨幅前30%的个股
        top30 = df_daily.nlargest(top30_count, 'pct_change')
        top30_mean = top30['pct_change'].mean()
        
        # 全市场中位数
        median_pct = df_daily['pct_change'].median()
        
        # 行情集中度指标
        concentration = top30_mean - median_pct
        
        return {
            'trade_date': trade_date,
            'concentration': round(concentration, 4),
            'top30_mean': round(top30_mean, 4),
            'median': round(median_pct, 4),
            'count': total_count,
            'top30_stocks': top30['ts_code'].tolist()[:20]  # 前20只作为参考
        }
    
    def calculate_industry_concentration(self, trade_date: str = None) -> pd.DataFrame:
        """
        计算各行业板块行情集中度
        
        Args:
            trade_date: 交易日期
            
        Returns:
            pd.DataFrame: 各行业集中度排名
        """
        if trade_date is None:
            trade_cal = self.pro.trade_cal(exchange='SSE', start_date='20250101',
                                           end_date='20251231')
            trade_cal = trade_cal[trade_cal['is_open'] == 1]
            trade_date = trade_cal['cal_date'].max()
        
        # 获取行业列表
        industries = self.pro.index_classify(level='L1', src='SW2021')
        
        results = []
        
        for _, row in industries.iterrows():
            industry_code = row['index_code']
            industry_name = row['industry_name']
            
            # 获取行业成分股
            members = self.pro.index_member(index_code=industry_code)
            if members is None or len(members) == 0:
                continue
            
            stock_list = members['con_code'].tolist()
            
            # 获取成分股当日行情
            df_daily = self.pro.daily(trade_date=trade_date)
            df_industry = df_daily[df_daily['ts_code'].isin(stock_list)]
            
            if len(df_industry) < 10:  # 成分股太少跳过
                continue
            
            # 计算涨跌幅
            prev_date = self._get_prev_trade_date(trade_date)
            if prev_date:
                df_prev = self.pro.daily(trade_date=prev_date)
                df_industry = df_industry.merge(df_prev[['ts_code', 'close']], on='ts_code',
                                               suffixes=('', '_prev'), how='left')
                df_industry['pct_change'] = (df_industry['close'] / df_industry['close_prev'] - 1) * 100
            else:
                df_industry['pct_change'] = df_industry['change'] / (df_industry['close'] - df_industry['change']) * 100
            
            df_industry = df_industry[df_industry['pct_change'].notna()]
            
            if len(df_industry) == 0:
                continue
            
            # 计算行业集中度
            total_count = len(df_industry)
            top30_count = max(3, int(total_count * 0.3))
            
            top30 = df_industry.nlargest(top30_count, 'pct_change')
            top30_mean = top30['pct_change'].mean()
            median_pct = df_industry['pct_change'].median()
            concentration = top30_mean - median_pct
            
            # 计算板块成交额占比
            industry_amount = df_industry['amount'].sum()
            
            results.append({
                'industry_code': industry_code,
                'industry_name': industry_name,
                'concentration': round(concentration, 4),
                'top30_mean': round(top30_mean, 4),
                'median': round(median_pct, 4),
                'stock_count': total_count,
                'amount': industry_amount,
                'limit_up_count': len(df_industry[df_industry['pct_change'] > 9]),
                'up_ratio': len(df_industry[df_industry['pct_change'] > 0]) / total_count
            })
        
        df_result = pd.DataFrame(results)
        if len(df_result) > 0:
            df_result = df_result.sort_values('concentration', ascending=False).reset_index(drop=True)
        
        return df_result
    
    def get_concentration_trend(self, days: int = 20) -> pd.DataFrame:
        """
        获取近期行情集中度趋势
        
        Args:
            days: 计算天数
            
        Returns:
            pd.DataFrame: 每日集中度数据
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # 考虑节假日
        
        trade_cal = self.pro.trade_cal(
            exchange='SSE',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        trade_cal = trade_cal[trade_cal['is_open'] == 1].tail(days)
        
        results = []
        for date in trade_cal['cal_date']:
            try:
                data = self.calculate_concentration(date)
                results.append(data)
            except Exception as e:
                continue
        
        return pd.DataFrame(results)
    
    def _get_prev_trade_date(self, trade_date: str) -> str:
        """获取前一个交易日"""
        date_obj = datetime.strptime(trade_date, '%Y%m%d')
        start_date = (date_obj - timedelta(days=30)).strftime('%Y%m%d')
        
        trade_cal = self.pro.trade_cal(
            exchange='SSE',
            start_date=start_date,
            end_date=trade_date
        )
        trade_cal = trade_cal[trade_cal['is_open'] == 1]
        trade_cal = trade_cal[trade_cal['cal_date'] < trade_date]
        
        if len(trade_cal) > 0:
            return trade_cal['cal_date'].max()
        return None
    
    def interpret_concentration(self, concentration: float) -> str:
        """
        解读行情集中度指标
        
        Args:
            concentration: 集中度数值
            
        Returns:
            str: 市场状态解读
        """
        if concentration < -2:
            return "市场极度分散，无明确主线 - 建议降低仓位，观望等待"
        elif -2 <= concentration < 1:
            return "主线酝酿期，资金试探性集中 - 建议轻仓布局潜在方向"
        elif 1 <= concentration < 3:
            return "主线初步确立，赚钱效应扩散 - 建议加仓确认方向，持有龙头"
        elif 3 <= concentration < 5:
            return "主升浪展开，资金极致集中 - 建议核心仓位持有，警惕过热"
        else:
            return "情绪泡沫化，分歧加大 - 建议逐步减仓，锁定利润"


if __name__ == '__main__':
    # 测试代码
    import tushare as ts
    
    pro = ts.pro_api()
    mc = MarketConcentration(pro)
    
    # 计算当日集中度
    result = mc.calculate_concentration()
    print(f"行情集中度: {result['concentration']}%")
    print(f"解读: {mc.interpret_concentration(result['concentration'])}")
    
    # 计算行业集中度
    industries = mc.calculate_industry_concentration()
    print("\n行业集中度排名:")
    print(industries.head(10)[['industry_name', 'concentration', 'limit_up_count', 'up_ratio']])
