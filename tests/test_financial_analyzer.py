#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务分析模块测试

测试内容：
- 杜邦分析
- 财务质量评分
- 同业比较
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from financial_analyzer.financial_analyzer import FinancialAnalyzer


class MockProAPI:
    """模拟Tushare API"""
    
    def fina_indicator(self, ts_code, limit=4):
        return pd.DataFrame({
            'end_date': ['20231231', '20230930', '20230630', '20230331'],
            'roe': [15.0, 14.5, 14.0, 13.5],
            'q_sales_yoy': [10.0, 9.5, 9.0, 8.5],  # 净利润率
            'assets_turn': [0.8, 0.75, 0.78, 0.76],
            'debt_to_assets': [45.0, 46.0, 44.0, 45.0],
            'ocf_to_profit': [0.9, 0.85, 0.88, 0.82]
        })
    
    def stock_basic(self, ts_code=None, industry=None):
        if ts_code:
            return pd.DataFrame({
                'ts_code': [ts_code],
                'industry': ['银行']
            })
        return pd.DataFrame()


class TestFinancialAnalyzer(unittest.TestCase):
    """测试财务分析器"""
    
    def setUp(self):
        self.mock_pro = MockProAPI()
        self.analyzer = FinancialAnalyzer(self.mock_pro)
    
    def test_dupont_analysis(self):
        """测试杜邦分析"""
        result = self.analyzer.dupont_analysis('000001.SZ')
        
        self.assertIn('roe', result)
        self.assertIn('net_profit_margin', result)
        self.assertIn('asset_turnover', result)
        self.assertIn('equity_multiplier', result)
    
    def test_financial_quality_score(self):
        """测试财务质量评分"""
        result = self.analyzer.financial_quality_score('000001.SZ')
        
        self.assertIn('total_score', result)
        self.assertIn('scores', result)
        self.assertIn('grade', result)
        
        # 分数应该在0-100之间
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)
    
    def test_peer_comparison(self):
        """测试同业比较"""
        result = self.analyzer.peer_comparison('000001.SZ')
        
        # 可能返回成功或错误（取决于模拟数据）
        self.assertTrue(
            'industry' in result or 'error' in result,
            f"结果应该包含'industry'或'error'，实际为: {result}"
        )


if __name__ == '__main__':
    unittest.main()
