#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合管理模块测试

测试内容：
- 组合分析
- 相关性计算
- 再平衡建议
"""

import unittest
import pandas as pd
import numpy as np
import json
import tempfile
import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from portfolio_manager.portfolio import PortfolioManager


class MockProAPI:
    """模拟Tushare API"""
    
    def daily(self, ts_code, limit=1):
        prices = {
            '000001.SZ': 11.0,
            '600519.SH': 1700.0,
            '000858.SZ': 150.0,
            '002594.SZ': 220.0
        }
        return pd.DataFrame({
            'trade_date': ['20240329'],
            'close': [prices.get(ts_code, 10.0)]
        })
    
    def stock_basic(self, ts_code=None, industry=None):
        industries = {
            '000001.SZ': '银行',
            '600519.SH': '白酒',
            '000858.SZ': '白酒',
            '002594.SZ': '汽车'
        }
        if ts_code:
            return pd.DataFrame({
                'ts_code': [ts_code],
                'industry': [industries.get(ts_code, '其他')]
            })
        elif industry:
            codes = [k for k, v in industries.items() if v == industry]
            return pd.DataFrame({
                'ts_code': codes,
                'industry': [industry] * len(codes)
            })
        return pd.DataFrame()


class TestPortfolioManager(unittest.TestCase):
    """测试组合管理器"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.manager = PortfolioManager(self.mock_pro)
        
        # 创建测试组合（包含market_value字段）
        self.test_portfolio = {
            'holdings': [
                {'ts_code': '000001.SZ', 'name': '平安银行', 'quantity': 1000, 'cost': 10.0, 
                 'current_price': 11.0, 'market_value': 11000},
                {'ts_code': '600519.SH', 'name': '贵州茅台', 'quantity': 100, 'cost': 1600.0,
                 'current_price': 1700.0, 'market_value': 170000}
            ],
            'cash': 50000,
            'total_capital': 200000,
            'total_market_value': 231000
        }
    
    def test_load_portfolio(self):
        """测试加载组合"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_portfolio, f)
            temp_path = f.name
        
        try:
            portfolio = self.manager.load_portfolio(temp_path)
            
            self.assertEqual(len(portfolio['holdings']), 2)
            self.assertIn('total_market_value', portfolio)
            self.assertIn('current_price', portfolio['holdings'][0])
        finally:
            os.unlink(temp_path)
    
    def test_analyze_summary(self):
        """测试组合概况分析"""
        analysis = self.manager._analyze_summary(self.test_portfolio)
        
        self.assertIn('total_cost', analysis)
        self.assertIn('total_market_value', analysis)
        self.assertIn('total_return', analysis)
        self.assertIn('cash_ratio', analysis)
    
    def test_analyze_sector(self):
        """测试行业分析"""
        # 先加载以获取价格
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_portfolio, f)
            temp_path = f.name
        
        try:
            portfolio = self.manager.load_portfolio(temp_path)
            sector = self.manager._analyze_sector(portfolio)
            
            self.assertIn('sector_weights', sector)
            self.assertIn('max_sector', sector)
        finally:
            os.unlink(temp_path)
    
    def test_get_rebalance_suggestion(self):
        """测试再平衡建议"""
        # 先加载
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_portfolio, f)
            temp_path = f.name
        
        try:
            portfolio = self.manager.load_portfolio(temp_path)
            
            target_weights = {
                '000001.SZ': 50,
                '600519.SH': 50
            }
            
            rebalance = self.manager.get_rebalance_suggestion(portfolio, target_weights)
            
            self.assertIn('suggestions', rebalance)
            self.assertIn('needs_rebalance', rebalance)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
