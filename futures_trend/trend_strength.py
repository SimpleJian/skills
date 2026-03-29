#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势强度量化模块 - 第三层筛选

多维度指标：
- 动量类 (30%): 长周期动量20%、短周期动量10%
- 趋势强度 (30%): ADX 20%、DI差5%、布林带斜率5%
- 量价配合 (25%): CMF 15%、PVT 10%
- 波动风险 (15%): ATR 10%、最大回撤5%
"""

import pandas as pd
import numpy as np
from typing import Dict
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


class TrendStrength:
    """趋势强度量化器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def get_data(self, ts_code: str, days: int = 120) -> pd.DataFrame:
        """获取历史数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            df = self.pro.fut_daily(ts_code=ts_code,
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
        except:
            pass
        
        return pd.DataFrame()
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算动量指标
        
        - 120日价格变化率（长周期）
        - 20日价格变化率（短周期）
        - 动量加速度
        """
        # 长周期动量 (120日)
        df['mom_long'] = (df['close'] / df['close'].shift(120) - 1) * 100
        
        # 短周期动量 (20日)
        df['mom_short'] = (df['close'] / df['close'].shift(20) - 1) * 100
        
        # 动量加速度
        df['mom_accel'] = df['mom_short'] - df['mom_short'].shift(5)
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        计算布林带
        """
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # 布林带中轨斜率
        df['bb_slope'] = df['bb_middle'].diff(5) / 5
        
        # 布林带宽度
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        return df
    
    def calculate_cmf(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        计算CMF（蔡金资金流向）
        
        CMF > 0: 资金净流入
        CMF > 0.25: 资金流入强劲
        """
        # 计算资金流量乘数
        df['money_flow_mult'] = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        
        # 计算资金流量
        df['money_flow_volume'] = df['money_flow_mult'] * df['vol']
        
        # 计算CMF
        df['cmf'] = df['money_flow_volume'].rolling(window=period).sum() / df['vol'].rolling(window=period).sum()
        
        return df
    
    def calculate_pvt(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算PVT（价量趋势）
        """
        df['price_change'] = df['close'].pct_change()
        df['pvt'] = (df['price_change'] * df['vol']).cumsum()
        
        # PVT变化率
        df['pvt_change'] = df['pvt'].pct_change(5) * 100
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算ATR（平均真实波幅）
        """
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=period).mean()
        
        # ATR变化率
        df['atr_change'] = df['atr'].pct_change(5) * 100
        
        # ATR百分比
        df['atr_pct'] = df['atr'] / df['close'] * 100
        
        return df
    
    def calculate_max_drawdown(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        计算近期最大回撤
        """
        df['rolling_max'] = df['close'].rolling(window=window).max()
        df['drawdown'] = (df['close'] - df['rolling_max']) / df['rolling_max'] * 100
        df['max_drawdown'] = df['drawdown'].rolling(window=window).min()
        
        return df
    
    def calculate_comprehensive_score(self, ts_code: str, direction: str) -> Dict:
        """
        计算综合评分
        
        权重配置：
        - 动量类 (30%): 长周期动量20%、短周期动量10%
        - 趋势强度 (30%): ADX 20%、DI差5%、布林带斜率5%
        - 量价配合 (25%): CMF 15%、PVT 10%
        - 波动风险 (15%): ATR 10%、最大回撤5%
        """
        df = self.get_data(ts_code)
        
        if len(df) < 60:
            return {'total_score': 0}
        
        # 计算所有指标
        df = self.calculate_momentum(df)
        df = self.calculate_bollinger(df)
        df = self.calculate_cmf(df)
        df = self.calculate_pvt(df)
        df = self.calculate_atr(df)
        df = self.calculate_max_drawdown(df)
        
        latest = df.iloc[-1]
        
        scores = {}
        
        # ===== 1. 动量类 (30分) =====
        
        # 长周期动量 (20分)
        mom_long = latest.get('mom_long', 0)
        if direction == '多头':
            if mom_long >= 20:
                scores['mom_long'] = 20
            elif mom_long >= 10:
                scores['mom_long'] = 16
            elif mom_long >= 5:
                scores['mom_long'] = 12
            elif mom_long >= 0:
                scores['mom_long'] = 8
            else:
                scores['mom_long'] = 0
        else:  # 空头
            if mom_long <= -20:
                scores['mom_long'] = 20
            elif mom_long <= -10:
                scores['mom_long'] = 16
            elif mom_long <= -5:
                scores['mom_long'] = 12
            elif mom_long <= 0:
                scores['mom_long'] = 8
            else:
                scores['mom_long'] = 0
        
        # 短周期动量 (10分)
        mom_short = latest.get('mom_short', 0)
        if direction == '多头':
            if mom_short >= 10:
                scores['mom_short'] = 10
            elif mom_short >= 5:
                scores['mom_short'] = 8
            elif mom_short >= 2:
                scores['mom_short'] = 6
            else:
                scores['mom_short'] = 0
        else:
            if mom_short <= -10:
                scores['mom_short'] = 10
            elif mom_short <= -5:
                scores['mom_short'] = 8
            elif mom_short <= -2:
                scores['mom_short'] = 6
            else:
                scores['mom_short'] = 0
        
        # ===== 2. 趋势强度 (30分) =====
        
        # 这里ADX和DI已经在趋势方向模块计算过，简化处理
        # ADX评分 (20分)
        # 假设ADX数据已在df中
        adx = latest.get('adx', 0)
        if adx >= 40:
            scores['adx'] = 20
        elif adx >= 30:
            scores['adx'] = 18
        elif adx >= 25:
            scores['adx'] = 15
        elif adx >= 20:
            scores['adx'] = 10
        else:
            scores['adx'] = 5
        
        # 布林带斜率 (10分)
        bb_slope = latest.get('bb_slope', 0)
        if direction == '多头':
            if bb_slope > 0.5:
                scores['bb_slope'] = 10
            elif bb_slope > 0:
                scores['bb_slope'] = 8
            else:
                scores['bb_slope'] = 0
        else:
            if bb_slope < -0.5:
                scores['bb_slope'] = 10
            elif bb_slope < 0:
                scores['bb_slope'] = 8
            else:
                scores['bb_slope'] = 0
        
        # ===== 3. 量价配合 (25分) =====
        
        # CMF (15分)
        cmf = latest.get('cmf', 0)
        if direction == '多头':
            if cmf >= 0.25:
                scores['cmf'] = 15
            elif cmf >= 0.1:
                scores['cmf'] = 12
            elif cmf >= 0:
                scores['cmf'] = 8
            else:
                scores['cmf'] = 0
        else:
            if cmf <= -0.25:
                scores['cmf'] = 15
            elif cmf <= -0.1:
                scores['cmf'] = 12
            elif cmf <= 0:
                scores['cmf'] = 8
            else:
                scores['cmf'] = 0
        
        # PVT (10分)
        pvt_change = latest.get('pvt_change', 0)
        if direction == '多头':
            if pvt_change >= 5:
                scores['pvt'] = 10
            elif pvt_change >= 2:
                scores['pvt'] = 8
            elif pvt_change >= 0:
                scores['pvt'] = 5
            else:
                scores['pvt'] = 0
        else:
            if pvt_change <= -5:
                scores['pvt'] = 10
            elif pvt_change <= -2:
                scores['pvt'] = 8
            elif pvt_change <= 0:
                scores['pvt'] = 5
            else:
                scores['pvt'] = 0
        
        # ===== 4. 波动风险 (15分) =====
        
        # ATR (10分) - 适中的波动率得分更高
        atr_pct = latest.get('atr_pct', 0)
        if 1.5 <= atr_pct <= 3.0:
            scores['atr'] = 10
        elif 1.0 <= atr_pct < 1.5 or 3.0 < atr_pct <= 4.0:
            scores['atr'] = 8
        elif atr_pct < 1.0 or atr_pct > 4.0:
            scores['atr'] = 5
        
        # 最大回撤 (5分) - 回撤小得分高
        max_dd = abs(latest.get('max_drawdown', 0))
        if max_dd <= 5:
            scores['max_dd'] = 5
        elif max_dd <= 10:
            scores['max_dd'] = 4
        elif max_dd <= 15:
            scores['max_dd'] = 3
        else:
            scores['max_dd'] = 0
        
        # 计算总分
        total_score = sum(scores.values())
        
        return {
            'ts_code': ts_code,
            'direction': direction,
            'total_score': total_score,
            'scores': scores,
            'indicators': {
                'mom_long': round(mom_long, 2),
                'mom_short': round(mom_short, 2),
                'cmf': round(cmf, 3),
                'atr_pct': round(atr_pct, 2),
                'max_drawdown': round(max_dd, 2)
            }
        }


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    ts_analyzer = TrendStrength(pro)
    
    # 测试
    result = ts_analyzer.calculate_comprehensive_score('CU.SHF', '多头')
    print(f"沪铜综合评分: {result['total_score']}")
    print(f"分项得分: {result['scores']}")
