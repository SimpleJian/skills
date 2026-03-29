#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪与资金验证模块 - 第三层筛选

核心指标：
- 持仓结构：持仓量变化、量仓比
- 资金流向：成交量异动、价格-持仓关系
- 市场情绪：波动率、涨跌家数比
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


class SentimentVerification:
    """情绪与资金验证器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def get_fut_data(self, ts_code: str, days: int = 60) -> pd.DataFrame:
        """获取期货历史数据"""
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
    
    def analyze_position_structure(self, df: pd.DataFrame) -> Dict:
        """
        分析持仓结构
        
        关注持仓量与价格的关系
        """
        if len(df) < 20 or 'oi' not in df.columns:
            return {'position_score': 0}
        
        latest = df.iloc[-1]
        
        # 持仓量变化
        oi_current = latest['oi']
        oi_ma20 = df['oi'].tail(20).mean()
        oi_change = (oi_current / oi_ma20 - 1) * 100
        
        # 价格变化
        price_change = (latest['close'] / df.iloc[-20]['close'] - 1) * 100
        
        # 持仓-价格关系
        # 价格下跌 + 持仓增加 = 可能资金承接（利好）
        # 价格下跌 + 持仓减少 = 资金撤离（利空）
        
        position_score = 0
        
        if price_change < 0:  # 下跌中
            if oi_change > 5:  # 持仓明显增加
                position_score = 25
                position_status = '下跌中持仓大增，资金承接'
            elif oi_change > 0:
                position_score = 20
                position_status = '下跌中持仓增加，有承接'
            elif oi_change > -5:
                position_score = 10
                position_status = '下跌中持仓稳定'
            else:
                position_score = 5
                position_status = '下跌中持仓减少，资金撤离'
        else:  # 上涨中
            if oi_change > 5:
                position_score = 20
                position_status = '上涨中持仓大增，趋势确认'
            elif oi_change > 0:
                position_score = 15
                position_status = '上涨中持仓增加'
            else:
                position_score = 10
                position_status = '上涨中持仓减少，谨慎'
        
        return {
            'oi_current': int(oi_current),
            'oi_change_pct': round(oi_change, 2),
            'price_change_20d': round(price_change, 2),
            'position_score': position_score,
            'position_status': position_status
        }
    
    def analyze_volume_pattern(self, df: pd.DataFrame) -> Dict:
        """
        分析成交量形态
        
        寻找底部放量信号
        """
        if len(df) < 20:
            return {'volume_score': 0}
        
        latest = df.iloc[-1]
        
        # 成交量均线
        vol_current = latest['vol']
        vol_ma5 = df['vol'].tail(5).mean()
        vol_ma20 = df['vol'].tail(20).mean()
        
        # 成交量比率
        vol_ratio_5 = vol_current / vol_ma5 if vol_ma5 > 0 else 1
        vol_ratio_20 = vol_current / vol_ma20 if vol_ma20 > 0 else 1
        
        # 近期成交量趋势
        vol_trend = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1
        
        # 价格-成交量关系
        price_change_5d = (latest['close'] / df.iloc[-5]['close'] - 1) * 100
        
        volume_score = 0
        
        # 底部放量（价格企稳/反弹 + 成交量放大）
        if price_change_5d > -2:  # 价格企稳或反弹
            if vol_ratio_20 > 1.5:  # 成交量明显放大
                volume_score = 25
                volume_status = '底部放量，反弹确认'
            elif vol_ratio_20 > 1.2:
                volume_score = 20
                volume_status = '成交量温和放大'
            else:
                volume_score = 15
                volume_status = '价格企稳，量能一般'
        else:  # 仍在下跌
            if vol_ratio_20 > 1.5:  # 放量下跌
                volume_score = 10
                volume_status = '放量下跌，恐慌盘涌出'
            elif vol_ratio_20 < 0.8:  # 缩量下跌
                volume_score = 15
                volume_status = '缩量下跌，抛压减轻'
            else:
                volume_score = 10
                volume_status = '下跌中，量能正常'
        
        return {
            'vol_current': int(vol_current),
            'vol_ratio_20': round(vol_ratio_20, 2),
            'vol_trend': round(vol_trend, 2),
            'price_change_5d': round(price_change_5d, 2),
            'volume_score': volume_score,
            'volume_status': volume_status
        }
    
    def calculate_volatility(self, df: pd.DataFrame) -> Dict:
        """
        计算波动率指标
        
        波动率极端化往往意味着情绪极端
        """
        if len(df) < 20:
            return {'volatility_score': 0}
        
        # 计算历史波动率
        df['returns'] = df['close'].pct_change()
        current_vol = df['returns'].tail(20).std() * np.sqrt(252) * 100  # 年化波动率
        
        # 历史波动率分布
        if len(df) >= 60:
            hist_vol = df['returns'].rolling(window=20).std() * np.sqrt(252) * 100
            vol_mean = hist_vol.mean()
            vol_std = hist_vol.std()
            vol_percentile = (hist_vol < current_vol).sum() / len(hist_vol) * 100
        else:
            vol_mean = current_vol
            vol_percentile = 50
        
        # 波动率评分（满分25分）
        # 高波动率（恐慌）= 潜在机会
        if vol_percentile > 90:  # 波动率历史最高10%
            volatility_score = 25
            vol_status = '波动率极高，恐慌情绪浓厚'
        elif vol_percentile > 80:
            volatility_score = 22
            vol_status = '波动率很高，情绪过度反应'
        elif vol_percentile > 70:
            volatility_score = 18
            vol_status = '波动率较高，情绪偏悲观'
        elif vol_percentile > 50:
            volatility_score = 12
            vol_status = '波动率中等偏高'
        else:
            volatility_score = 8
            vol_status = '波动率正常或偏低'
        
        return {
            'current_volatility': round(current_vol, 2),
            'hist_volatility_mean': round(vol_mean, 2),
            'volatility_percentile': round(vol_percentile, 1),
            'volatility_score': volatility_score,
            'volatility_status': vol_status
        }
    
    def analyze_price_momentum(self, df: pd.DataFrame) -> Dict:
        """
        分析价格动量
        
        寻找动量衰竭信号
        """
        if len(df) < 20:
            return {'momentum_score': 0}
        
        # 不同周期的价格变化
        ret_5d = (df.iloc[-1]['close'] / df.iloc[-5]['close'] - 1) * 100
        ret_10d = (df.iloc[-1]['close'] / df.iloc[-10]['close'] - 1) * 100
        ret_20d = (df.iloc[-1]['close'] / df.iloc[-20]['close'] - 1) * 100
        
        # 动量衰竭判断
        # 跌幅趋缓或出现反弹
        if ret_20d < -10:  # 20天内跌幅超过10%
            if ret_5d > -3:  # 近5天跌幅收窄
                momentum_score = 25
                momentum_status = '深度下跌后跌势放缓，动量衰竭'
            elif ret_5d > ret_10d:  # 跌幅收窄趋势
                momentum_score = 20
                momentum_status = '下跌动量减弱'
            else:
                momentum_score = 12
                momentum_status = '仍在加速下跌'
        elif ret_20d < -5:
            if ret_5d > -2:
                momentum_score = 22
                momentum_status = '中度下跌后企稳'
            else:
                momentum_score = 15
                momentum_status = '中度下跌中'
        else:
            momentum_score = 10
            momentum_status = '跌幅不大或已反弹'
        
        return {
            'ret_5d': round(ret_5d, 2),
            'ret_10d': round(ret_10d, 2),
            'ret_20d': round(ret_20d, 2),
            'momentum_score': momentum_score,
            'momentum_status': momentum_status
        }
    
    def comprehensive_sentiment_check(self, ts_code: str) -> Dict:
        """
        综合情绪资金验证
        """
        df = self.get_fut_data(ts_code)
        
        if len(df) < 20:
            return {'sentiment_score': 0}
        
        position = self.analyze_position_structure(df)
        volume = self.analyze_volume_pattern(df)
        volatility = self.calculate_volatility(df)
        momentum = self.analyze_price_momentum(df)
        
        # 情绪资金总评分（满分100分）
        total_score = (
            position['position_score'] +
            volume['volume_score'] +
            volatility['volatility_score'] +
            momentum['momentum_score']
        )
        
        return {
            'ts_code': ts_code,
            'sentiment_score': total_score,
            'position': position,
            'volume': volume,
            'volatility': volatility,
            'momentum': momentum
        }
    
    def filter_sentiment(self, df_value: pd.DataFrame, min_score: int = 50) -> pd.DataFrame:
        """
        第三层筛选：情绪资金验证
        """
        print()
        print("=" * 70)
        print("第三层筛选：情绪资金验证")
        print("=" * 70)
        print(f"筛选条件: 情绪资金评分≥{min_score}")
        print()
        
        results = []
        
        for idx, row in df_value.iterrows():
            ts_code = row.get('ts_code')
            name = row.get('name', '')
            
            try:
                check = self.comprehensive_sentiment_check(ts_code)
                
                if check['sentiment_score'] >= min_score:
                    results.append({
                        'ts_code': ts_code,
                        'name': name,
                        'sentiment_score': check['sentiment_score'],
                        'position_score': check['position']['position_score'],
                        'volume_score': check['volume']['volume_score'],
                        'volatility_score': check['volatility']['volatility_score'],
                        'momentum_score': check['momentum']['momentum_score'],
                        'position_status': check['position']['position_status'],
                        'volume_status': check['volume']['volume_status']
                    })
            
            except Exception as e:
                continue
        
        if len(results) == 0:
            print("没有品种通过情绪资金验证")
            return pd.DataFrame()
        
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values('sentiment_score', ascending=False).reset_index(drop=True)
        
        print(f"通过情绪资金验证: {len(df_result)}只")
        print()
        print("最终品种列表（前15）：")
        print(df_result.head(15)[['ts_code', 'name', 'sentiment_score', 'position_status', 'volume_status']].to_string(index=False))
        
        return df_result


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    sv = SentimentVerification(pro)
    
    # 测试
    result = sv.comprehensive_sentiment_check('CU.SHF')
    print(f"沪铜情绪资金评分: {result['sentiment_score']}")
    print(f"持仓: {result['position']}")
    print(f"成交量: {result['volume']}")
