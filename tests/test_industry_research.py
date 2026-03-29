#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业研究模块测试

测试内容：
- 行业表现获取
- 行业轮动
- 波特五力分析
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from industry_research.industry_research import IndustryResearch


class MockProAPI:
    """模拟Tushare API"""
    
    def sw_daily(self, ts_code, limit=20):
        return pd.DataFrame({
            'trade_date': pd.date_range('2024-01-01', periods=20, freq='D').strftime('%Y%m%d'),
            'close': [100 + i * 0.5 for i in range(20)]
        })


class TestIndustryResearch(unittest.TestCase):
    """测试行业研究"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.research = IndustryResearch(self.mock_pro)
    
    def test_get_industry_performance(self):
        """测试行业表现获取"""
        result = self.research.get_industry_performance('801750.SI', period=20)
        
        self.assertIn('total_return', result)
        self.assertIn('volatility', result)
    
    def test_industry_rotation(self):
        """测试行业轮动"""
        result = self.research.industry_rotation()
        
        self.assertIn('leading', result)
        self.assertIn('lagging', result)
    
    def test_porter_five_forces(self):
        """测试波特五力分析"""
        result = self.research.porter_five_forces('新能源汽车')
        
        self.assertEqual(result['industry'], '新能源汽车')
        self.assertIn('rivalry', result)
        self.assertIn('new_entrants', result)


if __name__ == '__main__':
    unittest.main()
