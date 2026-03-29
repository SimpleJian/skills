#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算模块

包含：移动平均线、MACD、成交量分析、突破检测等
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
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


class TechnicalIndicators:
    """技术指标计算器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def get_stock_data(self, ts_code: str, days: int = 120) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            ts_code: 股票代码
            days: 获取天数
            
        Returns:
            pd.DataFrame: 历史行情数据
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 1.5)
        
        df = self.pro.daily(
            ts_code=ts_code,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算移动平均线
        
        周期：5日、10日、20日、60日、120日、250日
        """
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        df['ma120'] = df['close'].rolling(window=120).mean()
        df['ma250'] = df['close'].rolling(window=250).mean()
        
        # 均线斜率
        df['ma20_slope'] = df['ma20'].diff(5) / 5
        df['ma60_slope'] = df['ma60'].diff(10) / 10
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, 
                       signal: int = 9) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df: 行情数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['macd_dif'] = ema_fast - ema_slow
        df['macd_dea'] = df['macd_dif'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = (df['macd_dif'] - df['macd_dea']) * 2
        
        # 判断金叉死叉
        df['macd_golden_cross'] = (df['macd_dif'].shift(1) < df['macd_dea'].shift(1)) & \
                                   (df['macd_dif'] > df['macd_dea'])
        df['macd_dead_cross'] = (df['macd_dif'].shift(1) > df['macd_dea'].shift(1)) & \
                                 (df['macd_dif'] < df['macd_dea'])
        
        # 零轴位置
        df['macd_above_zero'] = df['macd_dif'] > 0
        
        return df
    
    def check_divergence(self, df: pd.DataFrame) -> Dict:
        """
        检测MACD顶背离和底背离
        
        Returns:
            Dict: 背离信号
        """
        n = len(df)
        if n < 30:
            return {'top_divergence': False, 'bottom_divergence': False}
        
        # 找最近的高点
        recent_high_idx = df['close'].tail(20).idxmax()
        recent_high_price = df.loc[recent_high_idx, 'close']
        recent_high_macd = df.loc[recent_high_idx, 'macd_dif']
        
        # 找前一波高点（20-60周期前）
        if recent_high_idx - 20 < 0:
            prev_high_idx = df['close'].head(recent_high_idx).idxmax()
        else:
            prev_high_idx = df.iloc[:recent_high_idx-20]['close'].idxmax()
        
        prev_high_price = df.loc[prev_high_idx, 'close']
        prev_high_macd = df.loc[prev_high_idx, 'macd_dif']
        
        # 顶背离：价格新高，MACD未新高
        top_divergence = (recent_high_price > prev_high_price * 1.05) and \
                         (recent_high_macd < prev_high_macd * 0.95)
        
        # 找最近的低点
        recent_low_idx = df['close'].tail(20).idxmin()
        recent_low_price = df.loc[recent_low_idx, 'close']
        recent_low_macd = df.loc[recent_low_idx, 'macd_dif']
        
        # 找前一波低点
        if recent_low_idx - 20 < 0:
            prev_low_idx = df['close'].head(recent_low_idx).idxmin()
        else:
            prev_low_idx = df.iloc[:recent_low_idx-20]['close'].idxmin()
        
        prev_low_price = df.loc[prev_low_idx, 'close']
        prev_low_macd = df.loc[prev_low_idx, 'macd_dif']
        
        # 底背离：价格新低，MACD未新低
        bottom_divergence = (recent_low_price < prev_low_price * 0.95) and \
                            (recent_low_macd > prev_low_macd * 1.05)
        
        return {
            'top_divergence': top_divergence,
            'bottom_divergence': bottom_divergence,
            'recent_high_idx': recent_high_idx,
            'recent_low_idx': recent_low_idx
        }
    
    def check_breakthrough(self, df: pd.DataFrame, days: int = 20) -> Dict:
        """
        检测突破信号
        
        Args:
            df: 行情数据
            days: 突破周期
            
        Returns:
            Dict: 突破信号详情
        """
        if len(df) < days + 5:
            return {'breakthrough': False, 'volume_ratio': 0}
        
        latest = df.iloc[-1]
        
        # 计算前N日最高价
        prev_high = df['high'].tail(days+1).head(days).max()
        prev_close = df['close'].tail(days+1).head(days).max()
        
        # 突破判断
        price_break = latest['close'] > prev_high * 1.02  # 收盘高2%以上
        
        # 成交量判断
        avg_volume = df['vol'].tail(days).mean()
        volume_ratio = latest['vol'] / avg_volume if avg_volume > 0 else 0
        volume_confirm = volume_ratio >= 1.5  # 放量50%以上
        
        # 突破类型
        if price_break and volume_confirm:
            breakthrough = True
            bt_type = 'strong' if volume_ratio >= 2 else 'normal'
        elif price_break:
            breakthrough = True
            bt_type = 'weak'
        else:
            breakthrough = False
            bt_type = 'none'
        
        # 平台整理突破检测
        recent_df = df.tail(20)
        price_range = (recent_df['high'].max() - recent_df['low'].min()) / recent_df['close'].mean()
        platform_consolidation = price_range < 0.15  # 15%以内波动视为平台整理
        
        return {
            'breakthrough': breakthrough,
            'type': bt_type,
            'volume_ratio': round(volume_ratio, 2),
            'price_break': price_break,
            'volume_confirm': volume_confirm,
            'platform_break': price_break and platform_consolidation,
            'new_high_20d': latest['close'] >= df['close'].tail(days).max()
        }
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict:
        """
        成交量分析
        """
        if len(df) < 20:
            return {}
        
        latest = df.iloc[-1]
        
        # 近期均量
        avg_vol_5 = df['vol'].tail(5).mean()
        avg_vol_20 = df['vol'].tail(20).mean()
        
        # 量比
        volume_ratio = latest['vol'] / avg_vol_20 if avg_vol_20 > 0 else 0
        
        # 量价关系
        recent_5d = df.tail(5)
        up_days = recent_5d[recent_5d['close'] > recent_5d['open']]
        down_days = recent_5d[recent_5d['close'] < recent_5d['open']]
        
        up_volume = up_days['vol'].mean() if len(up_days) > 0 else 0
        down_volume = down_days['vol'].mean() if len(down_days) > 0 else 0
        
        volume_trend = 'healthy' if up_volume > down_volume * 1.2 else 'weak'
        
        return {
            'volume_ratio': round(volume_ratio, 2),
            'avg_vol_5': round(avg_vol_5, 0),
            'avg_vol_20': round(avg_vol_20, 0),
            'volume_trend': volume_trend,
            'up_volume': round(up_volume, 0),
            'down_volume': round(down_volume, 0)
        }
    
    def check_ma_arrangement(self, df: pd.DataFrame) -> Dict:
        """
        检查均线排列形态
        """
        if len(df) < 5:
            return {'arrangement': 'unknown'}
        
        latest = df.iloc[-1]
        
        # 获取各均线值
        ma5 = latest.get('ma5', 0)
        ma10 = latest.get('ma10', 0)
        ma20 = latest.get('ma20', 0)
        ma60 = latest.get('ma60', 0)
        
        # 多头排列：短期均线在长期均线上方
        if ma5 > ma10 > ma20 > ma60:
            arrangement = 'bull'
        # 空头排列
        elif ma5 < ma10 < ma20 < ma60:
            arrangement = 'bear'
        # 均线缠绕
        elif abs(ma5 - ma20) / ma20 < 0.03:
            arrangement = 'tangle'
        else:
            arrangement = 'mixed'
        
        # 股价与均线关系
        close = latest['close']
        above_ma20 = close > ma20
        above_ma60 = close > ma60
        
        # 均线乖离率
        ma_bias = (close - ma20) / ma20 * 100 if ma20 > 0 else 0
        
        return {
            'arrangement': arrangement,
            'above_ma20': above_ma20,
            'above_ma60': above_ma60,
            'ma20_slope': round(latest.get('ma20_slope', 0), 4),
            'ma_bias': round(ma_bias, 2),
            'ma20_trend': 'up' if latest.get('ma20_slope', 0) > 0 else 'down'
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算ATR（平均真实波幅）
        """
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=period).mean()
        
        # 波动率
        df['volatility'] = df['atr'] / df['close'] * 100
        
        return df
    
    def get_technical_score(self, ts_code: str) -> Dict:
        """
        获取个股技术面综合评分
        
        Returns:
            Dict: 技术面评分和详细信息
        """
        df = self.get_stock_data(ts_code, 120)
        if len(df) < 60:
            return {'score': 0, 'error': '数据不足'}
        
        # 计算指标
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)
        df = self.calculate_atr(df)
        
        latest = df.iloc[-1]
        
        # 各项评分 (满分100)
        scores = {}
        
        # 1. 均线排列评分 (25分)
        ma_info = self.check_ma_arrangement(df)
        if ma_info['arrangement'] == 'bull':
            scores['ma_score'] = 25
        elif ma_info['arrangement'] == 'mixed' and ma_info['above_ma20']:
            scores['ma_score'] = 15
        elif ma_info['above_ma20']:
            scores['ma_score'] = 10
        else:
            scores['ma_score'] = 0
        
        # 2. MACD评分 (25分)
        macd_score = 0
        if latest['macd_above_zero']:
            macd_score += 10
        if latest['macd_dif'] > latest['macd_dea']:
            macd_score += 10
        if latest['macd_hist'] > df['macd_hist'].iloc[-2]:
            macd_score += 5
        scores['macd_score'] = macd_score
        
        # 3. 突破评分 (20分)
        bt_info = self.check_breakthrough(df)
        if bt_info['breakthrough']:
            if bt_info['type'] == 'strong':
                scores['break_score'] = 20
            else:
                scores['break_score'] = 15
        elif bt_info['new_high_20d']:
            scores['break_score'] = 10
        else:
            scores['break_score'] = 0
        
        # 4. 趋势一致性评分 (15分)
        trend_score = 0
        if ma_info['ma20_trend'] == 'up':
            trend_score += 5
        if latest['close'] > latest['ma60']:
            trend_score += 5
        if latest['ma60_slope'] > 0:
            trend_score += 5
        scores['trend_score'] = trend_score
        
        # 5. 量价配合评分 (15分)
        vol_info = self.analyze_volume(df)
        vol_score = 0
        if vol_info.get('volume_ratio', 0) > 1.5:
            vol_score += 5
        if vol_info.get('volume_trend') == 'healthy':
            vol_score += 5
        if bt_info.get('volume_confirm', False):
            vol_score += 5
        scores['volume_score'] = vol_score
        
        # 总分
        total_score = sum(scores.values())
        
        # 风险信号
        risks = []
        divergence = self.check_divergence(df)
        if divergence['top_divergence']:
            risks.append('顶背离')
        if latest['volatility'] > 5:
            risks.append('高波动')
        if ma_info['ma_bias'] > 20:
            risks.append('超买')
        
        return {
            'score': total_score,
            'detail_scores': scores,
            'ma_info': ma_info,
            'macd_info': {
                'dif': round(latest['macd_dif'], 3),
                'dea': round(latest['macd_dea'], 3),
                'hist': round(latest['macd_hist'], 3),
                'above_zero': latest['macd_above_zero'],
                'golden_cross': latest['macd_golden_cross']
            },
            'break_info': bt_info,
            'volume_info': vol_info,
            'risks': risks,
            'volatility': round(latest['volatility'], 2)
        }


if __name__ == '__main__':
    import tushare as ts
    
    pro = ts.pro_api()
    ti = TechnicalIndicators(pro)
    
    # 测试个股
    result = ti.get_technical_score('000001.SZ')
    print(f"技术面评分: {result['score']}")
    print(f"详细评分: {result['detail_scores']}")
    print(f"风险信号: {result['risks']}")
