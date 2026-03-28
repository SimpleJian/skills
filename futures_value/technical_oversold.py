#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术面超卖筛选模块 - 第一层筛选

核心指标：
- 动量类：RSI(14)<30、KDJ-J<0、CCI(20)<-100、%R<-80
- 波动与趋势：布林带下轨、长期均线偏离
- 量价关系：下跌缩量后放量企稳
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta


class TechnicalOversold:
    """技术面超卖筛选器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_fut_data(self, ts_code: str, days: int = 120) -> pd.DataFrame:
        """
        获取期货历史数据
        """
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
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算RSI（相对强弱指数）
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        """
        low_list = df['low'].rolling(window=n, min_periods=n).min()
        high_list = df['high'].rolling(window=n, min_periods=n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        
        df['k'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
        df['d'] = df['k'].ewm(alpha=1/m2, adjust=False).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        return df
    
    def calculate_cci(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        计算CCI（商品通道指数）
        """
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma = tp.rolling(window=period).mean()
        md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (tp - ma) / (0.015 * md)
        
        return df
    
    def calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算威廉指标 %R
        """
        high_h = df['high'].rolling(window=period).max()
        low_l = df['low'].rolling(window=period).min()
        df['williams_r'] = (high_h - df['close']) / (high_h - low_l) * (-100)
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """
        计算布林带
        """
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + std_dev * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - std_dev * df['bb_std']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    def calculate_ma_deviation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算均线偏离度
        """
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        df['ma120'] = df['close'].rolling(window=120).mean()
        
        df['deviation_ma20'] = (df['close'] - df['ma20']) / df['ma20'] * 100
        df['deviation_ma60'] = (df['close'] - df['ma60']) / df['ma60'] * 100
        df['deviation_ma120'] = (df['close'] - df['ma120']) / df['ma120'] * 100
        
        return df
    
    def analyze_volume_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        量价关系分析
        """
        # 成交量均线
        df['vol_ma5'] = df['vol'].rolling(window=5).mean()
        df['vol_ma20'] = df['vol'].rolling(window=20).mean()
        
        # 成交量比率
        df['vol_ratio'] = df['vol'] / df['vol_ma20']
        
        # 价格变化
        df['price_change'] = df['close'].pct_change()
        
        # 持仓量变化
        if 'oi' in df.columns:
            df['oi_change'] = df['oi'].diff()
            df['oi_ratio'] = df['oi'] / df['oi'].rolling(window=20).mean()
        
        return df
    
    def check_oversold_signals(self, df: pd.DataFrame) -> Dict:
        """
        检查超卖信号
        
        Returns:
            {
                'rsi_oversold': RSI超卖,
                'kdj_oversold': KDJ超卖,
                'cci_oversold': CCI超卖,
                'williams_oversold': 威廉指标超卖,
                'bb_oversold': 布林带下轨,
                'ma_deviation': 均线偏离,
                'oversold_score': 超卖评分,
                'signals': 信号列表
            }
        """
        if len(df) < 60:
            return {'oversold_score': 0, 'signals': []}
        
        latest = df.iloc[-1]
        signals = []
        score = 0
        
        # 1. RSI超卖 (25分)
        rsi = latest.get('rsi', 50)
        if rsi < 20:
            score += 25
            signals.append(f'RSI极端超卖({rsi:.1f})')
        elif rsi < 30:
            score += 20
            signals.append(f'RSI超卖({rsi:.1f})')
        elif rsi < 40:
            score += 10
        
        # 2. KDJ超卖 (20分)
        j = latest.get('j', 0)
        if j < -20:
            score += 20
            signals.append(f'KDJ-J极端超卖({j:.1f})')
        elif j < 0:
            score += 15
            signals.append(f'KDJ-J超卖({j:.1f})')
        
        # 3. CCI超卖 (20分)
        cci = latest.get('cci', 0)
        if cci < -200:
            score += 20
            signals.append(f'CCI极端超卖({cci:.1f})')
        elif cci < -100:
            score += 15
            signals.append(f'CCI超卖({cci:.1f})')
        
        # 4. 威廉指标超卖 (15分)
        wr = latest.get('williams_r', -50)
        if wr < -90:
            score += 15
            signals.append(f'威廉指标极端超卖({wr:.1f})')
        elif wr < -80:
            score += 10
            signals.append(f'威廉指标超卖({wr:.1f})')
        
        # 5. 布林带下轨 (10分)
        bb_position = latest.get('bb_position', 0.5)
        if bb_position < 0:
            score += 10
            signals.append('跌破布林带下轨')
        elif bb_position < 0.1:
            score += 8
            signals.append('接近布林带下轨')
        
        # 6. 均线偏离 (10分)
        dev_120 = latest.get('deviation_ma120', 0)
        if dev_120 < -20:
            score += 10
            signals.append(f'严重偏离120日均线({dev_120:.1f}%)')
        elif dev_120 < -10:
            score += 8
            signals.append(f'偏离120日均线({dev_120:.1f}%)')
        
        return {
            'rsi': round(rsi, 2),
            'kdj_j': round(j, 2),
            'cci': round(cci, 2),
            'williams_r': round(wr, 2),
            'bb_position': round(bb_position, 3),
            'ma_deviation_120': round(dev_120, 2),
            'oversold_score': score,
            'signals': signals
        }
    
    def filter_oversold(self, df_candidates: pd.DataFrame, min_score: int = 60) -> pd.DataFrame:
        """
        第一层筛选：技术面超卖
        
        Args:
            df_candidates: 候选品种列表
            min_score: 最低超卖评分
        """
        print("=" * 70)
        print("第一层筛选：技术面超卖")
        print("=" * 70)
        print(f"筛选条件: 超卖评分≥{min_score}")
        print()
        
        results = []
        
        for idx, row in df_candidates.iterrows():
            ts_code = row.get('ts_code')
            name = row.get('name', '')
            
            try:
                # 获取数据
                df = self.get_fut_data(ts_code)
                if len(df) < 60:
                    continue
                
                # 计算指标
                df = self.calculate_rsi(df)
                df = self.calculate_kdj(df)
                df = self.calculate_cci(df)
                df = self.calculate_williams_r(df)
                df = self.calculate_bollinger(df)
                df = self.calculate_ma_deviation(df)
                df = self.analyze_volume_price(df)
                
                # 检查超卖信号
                signals = self.check_oversold_signals(df)
                
                if signals['oversold_score'] >= min_score:
                    results.append({
                        'ts_code': ts_code,
                        'name': name,
                        'oversold_score': signals['oversold_score'],
                        'rsi': signals['rsi'],
                        'kdj_j': signals['kdj_j'],
                        'cci': signals['cci'],
                        'williams_r': signals['williams_r'],
                        'ma_deviation': signals['ma_deviation_120'],
                        'signals': ';'.join(signals['signals'])
                    })
            
            except Exception as e:
                continue
        
        if len(results) == 0:
            print("没有品种通过超卖筛选")
            return pd.DataFrame()
        
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values('oversold_score', ascending=False).reset_index(drop=True)
        
        print(f"通过超卖筛选: {len(df_result)}只")
        print()
        print("超卖品种列表（前15）：")
        print(df_result.head(15)[['ts_code', 'name', 'oversold_score', 'rsi', 'cci', 'signals']].to_string(index=False))
        
        return df_result


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    to = TechnicalOversold(pro)
    
    # 测试
    df = to.get_fut_data('CU.SHF')
    if len(df) > 0:
        df = to.calculate_rsi(df)
        df = to.calculate_kdj(df)
        df = to.calculate_cci(df)
        signals = to.check_oversold_signals(df)
        print(f"沪铜超卖信号: {signals}")
