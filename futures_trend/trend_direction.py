#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势方向判定模块 - 第二层筛选

判定标准：
- 价格与均线关系：收盘价 vs 20日/60日均线
- 均线排列状态：短期均线上穿/下穿长期均线
- ADX > 25 判定趋势确立
- 初步分类：多头候选/空头候选/震荡剔除
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class TrendDirection:
    """趋势方向判定器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_continuous_data(self, ts_code: str, days: int = 80) -> pd.DataFrame:
        """
        获取连续合约数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            # 使用日线数据
            df = self.pro.fut_daily(ts_code=ts_code,
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
        except Exception as e:
            print(f"获取数据失败 {ts_code}: {e}")
        
        return pd.DataFrame()
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算移动平均线
        """
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 均线斜率
        df['ma20_slope'] = df['ma20'].diff(5) / 5
        df['ma60_slope'] = df['ma60'].diff(10) / 10
        
        return df
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算ADX（平均趋向指数）
        
        ADX > 25: 趋势较强
        ADX > 40: 趋势很强
        """
        # 计算+DM和-DM
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = -df['low'].diff()
        
        df['+dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
        df['-dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
        
        # 计算TR（真实波幅）
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # 计算ATR
        df['atr'] = df['tr'].rolling(window=period).mean()
        
        # 计算+DI和-DI
        df['+di'] = (df['+dm'].rolling(window=period).mean() / df['atr']) * 100
        df['-di'] = (df['-dm'].rolling(window=period).mean() / df['atr']) * 100
        
        # 计算DX和ADX
        df['dx'] = (abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])) * 100
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        return df
    
    def determine_trend_direction(self, df: pd.DataFrame) -> Dict:
        """
        判定趋势方向
        
        Returns:
            {
                'direction': '多头'/'空头'/'震荡',
                'strength': 趋势强度,
                'adx': ADX值,
                'ma_alignment': 均线排列,
                'score': 趋势方向评分
            }
        """
        if len(df) < 60:
            return {
                'direction': 'unknown',
                'strength': 0,
                'adx': 0,
                'ma_alignment': 'unknown',
                'score': 0
            }
        
        latest = df.iloc[-1]
        
        # 1. 价格与均线关系
        price_above_ma20 = latest['close'] > latest['ma20']
        price_above_ma60 = latest['close'] > latest['ma60']
        ma20_above_ma60 = latest['ma20'] > latest['ma60']
        
        # 2. 均线斜率
        ma20_rising = latest['ma20_slope'] > 0
        ma60_rising = latest['ma60_slope'] > 0
        
        # 3. ADX
        adx = latest.get('adx', 0)
        plus_di = latest.get('+di', 0)
        minus_di = latest.get('-di', 0)
        
        # 4. 趋势方向判定
        if price_above_ma20 and price_above_ma60 and ma20_above_ma60 and ma20_rising:
            direction = '多头'
            ma_alignment = '多头排列'
        elif not price_above_ma20 and not price_above_ma60 and not ma20_above_ma60 and not ma20_rising:
            direction = '空头'
            ma_alignment = '空头排列'
        else:
            direction = '震荡'
            ma_alignment = '均线缠绕'
        
        # 5. 趋势强度评分
        score = 0
        
        # ADX评分 (40分)
        if adx >= 40:
            score += 40
        elif adx >= 25:
            score += 35
        elif adx >= 20:
            score += 25
        else:
            score += 10
        
        # 均线排列评分 (30分)
        if direction == '多头' and ma20_above_ma60 and ma20_rising and ma60_rising:
            score += 30
        elif direction == '空头' and not ma20_above_ma60 and not ma20_rising and not ma60_rising:
            score += 30
        elif direction in ['多头', '空头']:
            score += 20
        else:
            score += 5
        
        # DI差评分 (20分)
        di_diff = abs(plus_di - minus_di)
        if di_diff >= 20:
            score += 20
        elif di_diff >= 10:
            score += 15
        else:
            score += 5
        
        # 价格位置评分 (10分)
        if direction == '多头':
            # 价格在均线之上且距离合理
            distance = (latest['close'] - latest['ma20']) / latest['ma20'] * 100
            if 0 < distance < 10:
                score += 10
            else:
                score += 5
        elif direction == '空头':
            distance = (latest['ma20'] - latest['close']) / latest['ma20'] * 100
            if 0 < distance < 10:
                score += 10
            else:
                score += 5
        
        return {
            'direction': direction,
            'strength': '强' if adx >= 40 else ('中等' if adx >= 25 else '弱'),
            'adx': round(adx, 2),
            'plus_di': round(plus_di, 2),
            'minus_di': round(minus_di, 2),
            'ma_alignment': ma_alignment,
            'price_vs_ma20': round((latest['close'] / latest['ma20'] - 1) * 100, 2),
            'price_vs_ma60': round((latest['close'] / latest['ma60'] - 1) * 100, 2),
            'score': score
        }
    
    def filter_by_trend(self, df_liquidity: pd.DataFrame, adx_threshold: float = 25) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        第二层筛选：趋势方向判定
        
        Args:
            df_liquidity: 通过流动性筛选的品种
            adx_threshold: ADX阈值，默认25
            
        Returns:
            (多头候选, 空头候选)
        """
        print()
        print("=" * 70)
        print("第二层筛选：趋势方向判定")
        print("=" * 70)
        print(f"筛选条件: ADX>={adx_threshold}, 均线多头排列/空头排列")
        print()
        
        long_candidates = []
        short_candidates = []
        
        for idx, row in df_liquidity.iterrows():
            ts_code = row['ts_code']
            name = row.get('name', '')
            
            try:
                # 获取数据
                df = self.get_continuous_data(ts_code)
                
                if len(df) < 60:
                    continue
                
                # 计算指标
                df = self.calculate_ma(df)
                df = self.calculate_adx(df)
                
                # 判定趋势
                trend = self.determine_trend_direction(df)
                
                # ADX必须大于阈值
                if trend['adx'] < adx_threshold:
                    continue
                
                result = {
                    'ts_code': ts_code,
                    'name': name,
                    'direction': trend['direction'],
                    'strength': trend['strength'],
                    'adx': trend['adx'],
                    'ma_alignment': trend['ma_alignment'],
                    'price_vs_ma20': trend['price_vs_ma20'],
                    'price_vs_ma60': trend['price_vs_ma60'],
                    'trend_score': trend['score'],
                    'avg_volume': row.get('avg_volume', 0),
                    'avg_oi': row.get('avg_oi', 0)
                }
                
                if trend['direction'] == '多头':
                    long_candidates.append(result)
                elif trend['direction'] == '空头':
                    short_candidates.append(result)
            
            except Exception as e:
                continue
        
        # 转换为DataFrame并排序
        df_long = pd.DataFrame(long_candidates)
        df_short = pd.DataFrame(short_candidates)
        
        if len(df_long) > 0:
            df_long = df_long.sort_values('trend_score', ascending=False).reset_index(drop=True)
        
        if len(df_short) > 0:
            df_short = df_short.sort_values('trend_score', ascending=False).reset_index(drop=True)
        
        print(f"多头候选: {len(df_long)}只")
        if len(df_long) > 0:
            print(df_long.head(10)[['ts_code', 'name', 'adx', 'ma_alignment', 'trend_score']].to_string(index=False))
        
        print()
        print(f"空头候选: {len(df_short)}只")
        if len(df_short) > 0:
            print(df_short.head(10)[['ts_code', 'name', 'adx', 'ma_alignment', 'trend_score']].to_string(index=False))
        
        return df_long, df_short


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    td = TrendDirection(pro)
    
    # 测试
    df = td.get_continuous_data('CU.SHF', days=80)
    if len(df) > 0:
        df = td.calculate_ma(df)
        df = td.calculate_adx(df)
        result = td.determine_trend_direction(df)
        print(f"沪铜趋势判定: {result}")
