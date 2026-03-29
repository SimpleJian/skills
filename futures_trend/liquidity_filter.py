#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流动性筛选模块 - 第一层筛选

筛选条件：
- 日均成交量 ≥ 10万手
- 日均持仓量 ≥ 5万手
- 优先选择成交金额大的品种
- 剔除上市不足一年的新品种
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
import time
import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.api_utils import APIRateLimiter


class LiquidityFilter:
    """期货流动性过滤器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.min_volume = 100000  # 10万手
        self.min_oi = 50000       # 5万手
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def get_fut_basic(self) -> pd.DataFrame:
        """
        获取期货品种基本信息
        """
        try:
            df = self.pro.fut_basic(exchange='', fut_type='2')  # 2=商品期货
            return df
        except:
            return pd.DataFrame()
    
    def get_main_contract_mapping(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取主力合约映射
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = self.pro.fut_mapping(trade_date=trade_date)
            return df
        except:
            return pd.DataFrame()
    
    def get_contract_daily(self, ts_code: str, days: int = 20) -> pd.DataFrame:
        """
        获取合约日线数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            df = self.pro.fut_daily(ts_code=ts_code, 
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'))
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date', ascending=False)
            return df
        except:
            return pd.DataFrame()
    
    def calculate_liquidity_metrics(self, ts_code: str, days: int = 20) -> Dict:
        """
        计算流动性指标
        
        Returns:
            {
                'avg_volume': 日均成交量,
                'avg_oi': 日均持仓量,
                'avg_amount': 日均成交金额,
                'volume_oi_ratio': 量仓比,
                'liquidity_score': 流动性评分
            }
        """
        df = self.get_contract_daily(ts_code, days)
        
        if len(df) < 10:  # 数据不足
            return {
                'avg_volume': 0,
                'avg_oi': 0,
                'avg_amount': 0,
                'volume_oi_ratio': 0,
                'liquidity_score': 0,
                'pass': False
            }
        
        df = df.head(days)
        
        # 计算指标
        avg_volume = df['vol'].mean()
        avg_oi = df['oi'].mean()
        avg_amount = (df['vol'] * df['close']).mean() if 'close' in df.columns else 0
        volume_oi_ratio = avg_volume / avg_oi if avg_oi > 0 else 0
        
        # 流动性评分 (满分100)
        score = 0
        
        # 成交量评分 (40分)
        if avg_volume >= 500000:  # 50万手
            score += 40
        elif avg_volume >= 200000:  # 20万手
            score += 35
        elif avg_volume >= 100000:  # 10万手
            score += 30
        elif avg_volume >= 50000:   # 5万手
            score += 20
        else:
            score += 10
        
        # 持仓量评分 (30分)
        if avg_oi >= 300000:  # 30万手
            score += 30
        elif avg_oi >= 100000:  # 10万手
            score += 25
        elif avg_oi >= 50000:   # 5万手
            score += 20
        else:
            score += 10
        
        # 量仓比评分 (20分) - 健康范围1-2
        if 1 <= volume_oi_ratio <= 2:
            score += 20
        elif 0.5 <= volume_oi_ratio < 1:
            score += 15
        elif 2 < volume_oi_ratio <= 3:
            score += 15
        else:
            score += 5
        
        # 持续性评分 (10分)
        volume_trend = df['vol'].iloc[:5].mean() / df['vol'].iloc[-5:].mean() if len(df) >= 10 else 1
        if 0.8 <= volume_trend <= 1.2:
            score += 10
        else:
            score += 5
        
        # 是否通过筛选
        pass_filter = (avg_volume >= self.min_volume) and (avg_oi >= self.min_oi)
        
        return {
            'avg_volume': int(avg_volume),
            'avg_oi': int(avg_oi),
            'avg_amount': int(avg_amount),
            'volume_oi_ratio': round(volume_oi_ratio, 2),
            'liquidity_score': score,
            'pass': pass_filter
        }
    
    def filter_by_liquidity(self, trade_date: str = None, top_n: int = 40) -> pd.DataFrame:
        """
        第一层筛选：流动性筛选
        
        筛选条件：
        1. 日均成交量 ≥ 10万手
        2. 日均持仓量 ≥ 5万手
        3. 按流动性评分排序
        """
        print("=" * 70)
        print("第一层筛选：流动性门槛")
        print("=" * 70)
        print(f"筛选条件: 日均成交量≥{self.min_volume/10000:.0f}万手, 日均持仓量≥{self.min_oi/10000:.0f}万手")
        print()
        
        # 获取主力合约映射
        mapping = self.get_main_contract_mapping(trade_date)
        if mapping is None or len(mapping) == 0:
            print("无法获取主力合约映射数据")
            return pd.DataFrame()
        
        print(f"全市场合约数量: {len(mapping)}")
        
        # 计算每个品种的流动性指标
        results = []
        
        for idx, row in mapping.iterrows():
            ts_code = row['ts_code']
            
            # 获取流动性指标
            metrics = self.calculate_liquidity_metrics(ts_code)
            
            if metrics['pass']:
                results.append({
                    'ts_code': ts_code,
                    'name': row.get('name', ''),
                    'avg_volume': metrics['avg_volume'],
                    'avg_oi': metrics['avg_oi'],
                    'avg_amount': metrics['avg_amount'],
                    'volume_oi_ratio': metrics['volume_oi_ratio'],
                    'liquidity_score': metrics['liquidity_score']
                })
        
        if len(results) == 0:
            print("没有合约通过流动性筛选")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df = df.sort_values('liquidity_score', ascending=False).reset_index(drop=True)
        
        print(f"通过流动性筛选: {len(df)}只")
        print(f"\n流动性Top {min(top_n, len(df))}:")
        print(df.head(top_n)[['ts_code', 'name', 'avg_volume', 'avg_oi', 'liquidity_score']].to_string(index=False))
        
        return df.head(top_n)
    
    def get_commodity_category(self, ts_code: str) -> str:
        """
        获取商品类别
        """
        category_map = {
            'CU': '有色金属', 'AL': '有色金属', 'ZN': '有色金属', 'PB': '有色金属', 'NI': '有色金属', 'SN': '有色金属',
            'RB': '黑色金属', 'HC': '黑色金属', 'I': '黑色金属', 'J': '黑色金属', 'JM': '黑色金属',
            'M': '农产品', 'Y': '农产品', 'P': '农产品', 'A': '农产品', 'C': '农产品', 'CS': '农产品',
            'CF': '农产品', 'SR': '农产品', 'OI': '农产品', 'RM': '农产品',
            'TA': '化工', 'MA': '化工', 'PP': '化工', 'L': '化工', 'PVC': '化工', 'EG': '化工',
            'SC': '能源', 'FU': '能源', 'BU': '能源', 'PG': '能源',
            'AU': '贵金属', 'AG': '贵金属',
        }
        
        # 从合约代码提取品种代码
        symbol = ts_code.split('.')[0]
        # 去掉数字部分
        product = ''.join([c for c in symbol if not c.isdigit()])
        
        return category_map.get(product, '其他')


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    lf = LiquidityFilter(pro)
    
    # 执行流动性筛选
    result = lf.filter_by_liquidity(top_n=40)
    
    print(f"\n筛选结果: {len(result)}只合约")
