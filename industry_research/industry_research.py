#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业研究模块

提供产业链分析、行业景气度、行业轮动等功能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import sys
import os

_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter


class IndustryResearch:
    """行业研究"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
        
        # 产业链映射
        self.industry_chains = {
            '新能源汽车': ['锂矿', '钴矿', '电池', '电机', '整车'],
            '半导体': ['硅片', '设备', '设计', '制造', '封测'],
            '光伏': ['硅料', '硅片', '电池片', '组件', '电站'],
            '钢铁': ['铁矿石', '焦煤', '焦炭', '钢铁', '建材'],
            '房地产': ['水泥', '钢铁', '玻璃', '地产', '家电'],
        }
    
    def get_industry_performance(self, industry_code: str, period: int = 20) -> Dict:
        """
        获取行业表现
        """
        try:
            # 获取行业指数
            @self.limiter.rate_limit
            def fetch():
                return self.pro.sw_daily(ts_code=industry_code, limit=period)
            
            df = fetch()
            if df is None or df.empty:
                return {'error': '无法获取行业数据'}
            
            df = df.sort_values('trade_date')
            df['return'] = df['close'].pct_change()
            
            total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            volatility = df['return'].std() * np.sqrt(252) * 100
            
            return {
                'total_return': total_return,
                'volatility': volatility,
                'sharpe': total_return / volatility if volatility > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def industry_rotation(self) -> Dict:
        """
        行业轮动信号
        """
        # 简化实现
        # 实际应该比较不同行业近期的相对强弱
        return {
            'leading': ['科技', '新能源'],
            'lagging': ['地产', '银行'],
            'rotation_signal': '成长风格占优'
        }
    
    def porter_five_forces(self, industry: str) -> Dict:
        """
        波特五力分析
        
        简化版本，实际应该基于更多数据
        """
        return {
            'industry': industry,
            'rivalry': '中等',  # 行业内竞争
            'new_entrants': '低',  # 新进入者威胁
            'substitutes': '低',  # 替代品威胁
            'buyer_power': '中等',  # 买方议价能力
            'supplier_power': '中等'  # 供应商议价能力
        }


if __name__ == '__main__':
    print("行业研究模块")
