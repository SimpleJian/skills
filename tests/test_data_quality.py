#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量模块测试

测试内容：
- 价格数据质量检查
- 财务数据异常检测
- 数据预处理流程
- 期货合约到期检查
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加 skills 目录到路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.data_quality import (
    DataQualityChecker,
    DataPreprocessor,
    FuturesDataProcessor
)


class TestDataQualityChecker(unittest.TestCase):
    """测试数据质量检查器"""
    
    def setUp(self):
        self.checker = DataQualityChecker()
    
    def test_check_price_data_normal(self):
        """测试正常价格数据"""
        # 创建正常价格数据
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': [10.0 + i * 0.1 for i in range(30)],
            'high': [10.2 + i * 0.1 for i in range(30)],
            'low': [9.8 + i * 0.1 for i in range(30)],
            'close': [10.1 + i * 0.1 for i in range(30)],
            'volume': [10000 + i * 100 for i in range(30)]
        })
        
        result_df, issues = self.checker.check_price_data(df, '000001.SZ')
        
        self.assertIsNotNone(result_df)
        self.assertEqual(len(issues), 0, f"正常数据不应有问题，但检测到: {issues}")
    
    def test_check_price_data_with_gap(self):
        """测试有除权缺口的价格数据"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        closes = [10.0 + i * 0.05 for i in range(30)]
        # 插入一个大幅跳空（模拟除权）
        closes[15] = closes[14] * 0.5  # 50%跌幅
        
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': closes,
            'high': [c * 1.02 for c in closes],
            'low': [c * 0.98 for c in closes],
            'close': closes,
            'volume': [10000] * 30
        })
        
        result_df, issues = self.checker.check_price_data(df, '000001.SZ')
        
        self.assertIn('除权缺口', issues)
    
    def test_check_price_data_suspended(self):
        """测试停牌数据"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        volumes = [10000] * 25 + [0] * 5  # 最后5天停牌
        
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': [10.0] * 30,
            'high': [10.2] * 30,
            'low': [9.8] * 30,
            'close': [10.0] * 30,
            'volume': volumes
        })
        
        result_df, issues = self.checker.check_price_data(df, '000001.SZ')
        
        self.assertIn('部分停牌', issues)
    
    def test_check_price_data_empty(self):
        """测试空数据"""
        df = pd.DataFrame()
        result_df, issues = self.checker.check_price_data(df, '000001.SZ')
        
        self.assertIn('数据为空', issues)
    
    def test_check_fundamental_data_red_flags(self):
        """测试财务异常红旗检测"""
        # 创建有问题的财务数据
        df = pd.DataFrame({
            'end_date': ['20231231', '20221231', '20211231'],
            'accounts_receiv': [1000, 500, 300],  # 应收账款快速增长
            'total_revenue': [2000, 1800, 1700],   # 营收增长慢于应收
            'n_cashflow_act': [100, 150, 200],     # 现金流少于净利润
            'net_profit': [500, 450, 400],
            'money_cap': [1000, 1000, 1000],       # 存贷双高
            'total_assets': [3000, 2900, 2800],
            'total_liab': [1500, 1400, 1300],
            'goodwill': [1000, 1000, 1000],        # 高商誉
            'roe': [15, 20, 5]                     # ROE波动大
        })
        
        issues = self.checker.check_fundamental_data(df)
        
        # 应该检测到多个红旗
        self.assertGreater(len(issues), 0)


class TestDataPreprocessor(unittest.TestCase):
    """测试数据预处理器"""
    
    def setUp(self):
        self.processor = DataPreprocessor(api=None)
    
    def test_mark_suspended(self):
        """测试停牌标记"""
        df = pd.DataFrame({
            'volume': [1000, 2000, 0, 0, 1000]  # 中间两天停牌
        })
        
        result = self.processor.mark_suspended(df)
        
        self.assertIn('is_suspended', result.columns)
        self.assertIn('recently_suspended', result.columns)
        self.assertTrue(result['recently_suspended'].iloc[-1])
    
    def test_calculate_volatility_tag(self):
        """测试波动率标签计算"""
        # 高波动数据
        df_high = pd.DataFrame({
            'close': [10.0, 11.0, 9.0, 12.0, 8.0] * 6  # 波动大
        })
        
        tag = self.processor.calculate_volatility_tag(df_high)
        
        self.assertIsNotNone(tag)
        self.assertIn(tag, ['极高波动', '高波动', '异动'])
    
    def test_calculate_volatility_tag_normal(self):
        """测试正常波动率"""
        # 正常波动数据
        df_normal = pd.DataFrame({
            'close': [10.0 + i * 0.01 for i in range(30)]  # 平稳上涨
        })
        
        tag = self.processor.calculate_volatility_tag(df_normal)
        
        self.assertIsNone(tag)


class TestFuturesDataProcessor(unittest.TestCase):
    """测试期货数据处理器"""
    
    def setUp(self):
        self.processor = FuturesDataProcessor(api=None)
    
    def test_check_contract_expiry_format(self):
        """测试合约到期解析格式"""
        # 测试正常合约
        days, tag = self.processor.check_contract_expiry('CU2505.SHF')
        
        # 应该返回天数和标签
        self.assertIsInstance(days, int)
        self.assertIsInstance(tag, str)
    
    def test_check_contract_expiry_invalid(self):
        """测试无效合约代码"""
        days, tag = self.processor.check_contract_expiry('INVALID')
        
        self.assertEqual(days, 999)
    
    def test_process_futures_data(self):
        """测试期货数据处理"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': [50000 + i * 10 for i in range(30)],
            'high': [50100 + i * 10 for i in range(30)],
            'low': [49900 + i * 10 for i in range(30)],
            'close': [50050 + i * 10 for i in range(30)],
            'volume': [10000] * 30,
            'amount': [500000000] * 30
        })
        
        result_df, issues = self.processor.process_futures_data(df, 'CU2505.SHF')
        
        self.assertIsNotNone(result_df)
        self.assertIsInstance(issues, list)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_pipeline_stock(self):
        """测试股票完整处理流程"""
        processor = DataPreprocessor(api=None)
        
        # 创建模拟数据
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': [10.0 + i * 0.1 for i in range(30)],
            'high': [10.2 + i * 0.1 for i in range(30)],
            'low': [9.8 + i * 0.1 for i in range(30)],
            'close': [10.1 + i * 0.1 for i in range(30)],
            'volume': [10000] * 30
        })
        
        result_df, issues = processor.process_stock_data(df, '000001.SZ')
        
        self.assertIsNotNone(result_df)
        self.assertIn('is_suspended', result_df.columns)
        self.assertIsInstance(issues, list)


if __name__ == '__main__':
    unittest.main()
