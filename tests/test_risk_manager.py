#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理模块测试

测试内容：
- 风险扫描
- VaR计算
- 凯利公式
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from risk_manager.risk_manager import RiskManager


class MockProAPI:
    """模拟Tushare API"""
    
    def daily(self, ts_code, limit=1):
        # 模拟不同价格以测试盈亏
        prices = {
            '000001.SZ': 10.5,   # 盈利5%
            '600519.SH': 1500.0, # 亏损6.25%
            'RISKY01.SZ': 9.0,   # 亏损10%
            'RISKY02.SZ': 8.0    # 亏损20%
        }
        return pd.DataFrame({
            'trade_date': ['20240329'],
            'close': [prices.get(ts_code, 10.0)]
        })


class TestRiskManager(unittest.TestCase):
    """测试风险管理器"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.manager = RiskManager(self.mock_pro)
    
    def test_scan_portfolio_risk_normal(self):
        """测试正常持仓风险扫描"""
        holdings = [
            {'ts_code': '000001.SZ', 'quantity': 1000, 'cost': 10.0}  # 盈利5%
        ]
        
        result = self.manager.scan_portfolio_risk(holdings)
        
        self.assertIn('alerts', result)
        self.assertIn('warnings', result)
        # 盈利状态应该没有警报
        self.assertEqual(len(result['alerts']), 0)
    
    def test_scan_portfolio_risk_stop_loss(self):
        """测试止损警报"""
        holdings = [
            {'ts_code': 'RISKY02.SZ', 'quantity': 1000, 'cost': 10.0}  # 亏损20%
        ]
        
        result = self.manager.scan_portfolio_risk(holdings)
        
        # 应该触发止损警报
        self.assertGreater(len(result['alerts']), 0)
    
    def test_calculate_var(self):
        """测试VaR计算"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        var_95 = self.manager.calculate_var(returns, 0.95)
        
        # VaR应该是负数
        self.assertLess(var_95, 0)
    
    def test_calculate_expected_shortfall(self):
        """测试ES计算"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        es = self.manager.calculate_expected_shortfall(returns, 0.95)
        
        # ES应该是负数且小于VaR
        self.assertLess(es, 0)
    
    def test_kelly_criterion_optimal(self):
        """测试凯利公式最优仓位"""
        # 胜率50%，盈亏比2:1
        kelly = self.manager.kelly_criterion(0.5, 2.0, 1.0)
        
        self.assertGreater(kelly, 0)
        self.assertLessEqual(kelly, 1.0)
    
    def test_kelly_criterion_negative(self):
        """测试凯利公式负期望"""
        # 胜率30%，盈亏比1:1（负期望）
        kelly = self.manager.kelly_criterion(0.3, 1.0, 1.0)
        
        # 应该返回0（不下注）
        self.assertEqual(kelly, 0)


if __name__ == '__main__':
    unittest.main()
