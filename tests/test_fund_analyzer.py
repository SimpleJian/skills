#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金分析模块测试

测试内容：
- 基金筛选
- 业绩分析
- 持仓获取
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from fund_analyzer.fund_analyzer import FundAnalyzer


class MockProAPI:
    """模拟Tushare API"""
    
    def fund_basic(self, market, status):
        return pd.DataFrame({
            'ts_code': ['110022.OF', '110023.OF', '110024.OF'],
            'name': ['易方达消费', '易方达医药', '易方达科技'],
            'fund_type': ['E', 'E', 'E']
        })
    
    def fund_nav(self, ts_code, limit=252):
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        nav_values = [1.0 + i * 0.001 for i in range(100)]
        return pd.DataFrame({
            'end_date': dates.strftime('%Y%m%d'),
            'nav': nav_values
        })
    
    def fund_portfolio(self, ts_code):
        return pd.DataFrame({
            'symbol': ['000001.SZ', '600519.SH'],
            'name': ['平安银行', '贵州茅台'],
            'weight': [10.0, 15.0]
        })


class TestFundAnalyzer(unittest.TestCase):
    """测试基金分析器"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.analyzer = FundAnalyzer(self.mock_pro)
    
    def test_filter_funds(self):
        """测试基金筛选"""
        result = self.analyzer.filter_funds(fund_type='E')
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
    
    def test_analyze_fund_performance(self):
        """测试基金业绩分析"""
        result = self.analyzer.analyze_fund_performance('110022.OF')
        
        self.assertIn('total_return', result)
        self.assertIn('annual_return', result)
        self.assertIn('sharpe', result)
        self.assertIn('max_drawdown', result)
    
    def test_get_fund_portfolio(self):
        """测试基金持仓获取"""
        result = self.analyzer.get_fund_portfolio('110022.OF')
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
