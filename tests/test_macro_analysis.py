#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观分析模块测试

测试内容：
- 经济周期判断
- 宏观指标获取
- 资产配置建议
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from macro_analysis.macro_analyzer import MacroAnalyzer


class MockProAPI:
    """模拟Tushare API"""
    
    def cn_gdp(self, start_q, end_q):
        return pd.DataFrame({
            'quarter': ['2023Q1', '2023Q2', '2023Q3', '2023Q4', '2024Q1', '2024Q2'],
            'gdp': [280000, 300000, 320000, 340000, 290000, 310000],
            'gdp_yoy': [4.5, 5.0, 5.2, 5.3, 5.0, 5.2]
        })
    
    def cn_cpi(self, start_m, end_m):
        return pd.DataFrame({
            'month': ['202401', '202402', '202403', '202404', '202405', '202406'],
            'nt_yoy': [0.5, 0.7, 0.8, 0.6, 0.5, 0.7]
        })
    
    def cn_ppi(self, start_m, end_m):
        return pd.DataFrame({
            'month': ['202401', '202402', '202403', '202404', '202405', '202406'],
            'ppi_yoy': [-2.5, -2.2, -2.0, -1.8, -1.5, -1.2]
        })
    
    def cn_pmi(self, start_m, end_m):
        return pd.DataFrame({
            'month': ['202401', '202402', '202403', '202404', '202405', '202406'],
            'pmi010000': [49.0, 49.5, 50.0, 50.5, 51.0, 51.2]
        })
    
    def cn_m(self, start_m, end_m):
        return pd.DataFrame({
            'month': ['202401', '202402', '202403', '202404', '202405', '202406'],
            'm2_yoy': [8.5, 8.6, 8.7, 8.5, 8.4, 8.3]
        })
    
    def sf_month(self, start_m, end_m):
        return pd.DataFrame({
            'month': ['202401', '202402', '202403', '202404', '202405', '202406'],
            'inc_cum_yoy': [9.0, 9.2, 9.5, 9.3, 9.1, 9.0]
        })
    
    def shibor_lpr(self, start_date, end_date):
        return pd.DataFrame({
            'date': ['20240101', '20240201', '20240301', '20240401', '20240501', '20240601'],
            '1y': [3.45, 3.45, 3.40, 3.35, 3.30, 3.25]
        })


class TestMacroAnalyzer(unittest.TestCase):
    """测试宏观分析器"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.analyzer = MacroAnalyzer(self.mock_pro)
    
    def test_detect_economic_phase_recovery(self):
        """测试复苏期判断"""
        phase, confidence = self.analyzer.detect_economic_phase()
        
        self.assertIn(phase, ['复苏期', '过热期', '滞胀期', '衰退期', '不确定'])
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)
    
    def test_get_gdp_data(self):
        """测试GDP数据获取"""
        df = self.analyzer.get_gdp_data(quarters=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
        if 'gdp_yoy' in df.columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df['gdp_yoy']))
    
    def test_get_cpi_data(self):
        """测试CPI数据获取"""
        df = self.analyzer.get_cpi_data(months=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
    
    def test_get_ppi_data(self):
        """测试PPI数据获取"""
        df = self.analyzer.get_ppi_data(months=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
    
    def test_get_pmi_data(self):
        """测试PMI数据获取"""
        df = self.analyzer.get_pmi_data(months=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
    
    def test_get_money_supply(self):
        """测试货币供应量数据获取"""
        df = self.analyzer.get_money_supply(months=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
    
    def test_get_social_finance(self):
        """测试社融数据获取"""
        df = self.analyzer.get_social_finance(months=6)
        
        self.assertIsNotNone(df)
    
    def test_get_lpr_data(self):
        """测试LPR数据获取"""
        df = self.analyzer.get_lpr_data(months=6)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
    
    def test_get_asset_allocation(self):
        """测试资产配置建议"""
        allocation = self.analyzer.get_asset_allocation()
        
        self.assertIn('phase', allocation)
        self.assertIn('allocation', allocation)
        self.assertIn('股票', allocation['allocation'])
        self.assertIn('债券', allocation['allocation'])
    
    def test_analyze_all_indicators(self):
        """测试全指标分析"""
        indicators = self.analyzer.analyze_all_indicators()
        
        self.assertIsInstance(indicators, dict)
        # 至少应该有部分指标
        self.assertGreater(len(indicators), 0)
    
    def test_trend_symbol_up(self):
        """测试上升趋势符号"""
        result = self.analyzer._get_trend_symbol(6.0, 5.0)
        self.assertEqual(result, "↗ 回升")
    
    def test_trend_symbol_down(self):
        """测试下降趋势符号"""
        result = self.analyzer._get_trend_symbol(4.0, 5.0)
        self.assertEqual(result, "↘ 下行")
    
    def test_trend_symbol_stable(self):
        """测试平稳趋势符号"""
        result = self.analyzer._get_trend_symbol(5.0, 5.0)
        self.assertEqual(result, "→ 平稳")


if __name__ == '__main__':
    unittest.main()
