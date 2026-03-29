#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险标签模块测试

测试内容：
- 风险标签生成
- 标签分类
- 风险等级判定
- 标签字符串格式化
"""

import unittest
import pandas as pd
import sys
import os

# 添加 skills 目录到路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.risk_tags import (
    RiskLevel,
    RiskTag,
    RiskTagGenerator,
    AShareRiskAnalyzer,
    FuturesRiskAnalyzer,
    merge_issues_to_tags
)


class TestRiskTag(unittest.TestCase):
    """测试风险标签数据类"""
    
    def test_tag_creation(self):
        """测试标签创建"""
        tag = RiskTag(
            category='财务风险',
            tag='应收账款异常',
            level=RiskLevel.HIGH,
            description='可能存在财务造假'
        )
        
        self.assertEqual(tag.category, '财务风险')
        self.assertEqual(tag.tag, '应收账款异常')
        self.assertEqual(tag.level, RiskLevel.HIGH)


class TestRiskTagGenerator(unittest.TestCase):
    """测试风险标签生成器"""
    
    def setUp(self):
        self.generator = RiskTagGenerator()
    
    def test_add_tag(self):
        """测试添加标签"""
        self.generator.add_tag('财务风险', '应收账款异常', RiskLevel.HIGH)
        
        self.assertEqual(len(self.generator.tags), 1)
        self.assertEqual(self.generator.tags[0].tag, '应收账款异常')
    
    def test_add_raw_issues_financial(self):
        """测试财务问题分类"""
        issues = ['应收账款异常', '现金流质量差', '存贷双高']
        self.generator.add_raw_issues(issues)
        
        tags = self.generator.get_all_tags()
        self.assertIn('应收账款异常', tags)
        self.assertIn('现金流质量差', tags)
        self.assertIn('存贷双高', tags)
    
    def test_add_raw_issues_liquidity(self):
        """测试流动性问题分类"""
        issues = ['即将到期', '临近换月', '成交额过低']
        self.generator.add_raw_issues(issues)
        
        tags = self.generator.get_all_tags()
        self.assertIn('即将到期', tags)
        self.assertIn('临近换月', tags)
        self.assertIn('成交额过低', tags)
        
        # 检查极高风险标签
        critical = self.generator.get_critical_tags()
        self.assertIn('即将到期', critical)
    
    def test_add_raw_issues_volatility(self):
        """测试波动率问题分类"""
        issues = ['极高波动', '高波动', '异动']
        self.generator.add_raw_issues(issues)
        
        tags = self.generator.get_all_tags()
        self.assertIn('极高波动', tags)
        self.assertIn('高波动', tags)
        self.assertIn('异动', tags)
    
    def test_get_tags_string(self):
        """测试标签字符串生成"""
        self.generator.add_tag('财务风险', '应收账款异常', RiskLevel.HIGH)
        self.generator.add_tag('波动风险', '高波动', RiskLevel.MEDIUM)
        
        tag_str = self.generator.get_tags_string()
        
        self.assertIn('应收账款异常', tag_str)
        self.assertIn('高波动', tag_str)
        self.assertIn('|', tag_str)
    
    def test_get_tags_string_limit(self):
        """测试标签数量限制"""
        # 添加多个标签
        self.generator.add_tag('财务风险', '应收账款异常', RiskLevel.HIGH)
        self.generator.add_tag('财务风险', '现金流质量差', RiskLevel.HIGH)
        self.generator.add_tag('波动风险', '高波动', RiskLevel.MEDIUM)
        self.generator.add_tag('数据质量', '新股', RiskLevel.LOW)
        
        # 限制为2个
        tag_str = self.generator.get_tags_string(max_tags=2)
        
        # 应该只返回高优先级的2个
        tag_count = len(tag_str.split('|'))
        self.assertEqual(tag_count, 2)
    
    def test_has_critical_risk(self):
        """测试极高风险检测"""
        # 先添加非极高风险
        self.generator.add_tag('波动风险', '高波动', RiskLevel.MEDIUM)
        self.assertFalse(self.generator.has_critical_risk())
        
        # 添加极高风险
        self.generator.add_tag('流动性风险', '即将到期', RiskLevel.CRITICAL)
        self.assertTrue(self.generator.has_critical_risk())
    
    def test_get_risk_summary(self):
        """测试风险汇总"""
        self.generator.add_tag('财务风险', '应收账款异常', RiskLevel.HIGH)
        self.generator.add_tag('波动风险', '高波动', RiskLevel.MEDIUM)
        
        summary = self.generator.get_risk_summary()
        
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['high'], 1)
        self.assertEqual(summary['medium'], 1)
        self.assertIn('财务风险', summary['categories'])


class TestAShareRiskAnalyzer(unittest.TestCase):
    """测试A股风险分析器"""
    
    def setUp(self):
        self.analyzer = AShareRiskAnalyzer(api=None)
    
    def test_analyze_stock_with_high_volatility(self):
        """测试高波动股票分析"""
        # 创建高波动价格数据
        price_df = pd.DataFrame({
            'close': [10.0, 11.5, 9.0, 12.0, 8.5] * 6  # 高波动
        })
        
        generator = self.analyzer.analyze_stock('000001.SZ', price_df)
        
        tags = generator.get_all_tags()
        # 应该检测到波动风险
        self.assertTrue(
            any(tag in tags for tag in ['极高波动', '高波动', '异动']),
            f"应该检测到波动风险，但标签为: {tags}"
        )
    
    def test_analyze_stock_with_suspension(self):
        """测试停牌股票分析"""
        price_df = pd.DataFrame({
            'volume': [1000] * 25 + [0] * 5  # 最后5天停牌
        })
        
        generator = self.analyzer.analyze_stock('000001.SZ', price_df)
        
        tags = generator.get_all_tags()
        self.assertIn('近期停牌', tags)


class TestFuturesRiskAnalyzer(unittest.TestCase):
    """测试期货风险分析器"""
    
    def setUp(self):
        self.analyzer = FuturesRiskAnalyzer(api=None)
    
    def test_analyze_contract_near_expiry(self):
        """测试临近到期合约"""
        generator = self.analyzer.analyze_contract('CU2505.SHF', None, days_to_expiry=5)
        
        tags = generator.get_all_tags()
        self.assertIn('即将到期', tags)
        
        # 应该是极高风险
        self.assertTrue(generator.has_critical_risk())
    
    def test_analyze_contract_expired(self):
        """测试已到期合约"""
        generator = self.analyzer.analyze_contract('CU2501.SHF', None, days_to_expiry=-1)
        
        tags = generator.get_all_tags()
        self.assertIn('已到期', tags)
    
    def test_analyze_contract_low_liquidity(self):
        """测试低流动性合约"""
        price_df = pd.DataFrame({
            'volume': [100] * 30,  # 低成交量
            'amount': [1000000] * 30  # 低成交额
        })
        
        generator = self.analyzer.analyze_contract('XX8888.XXX', price_df)
        
        # 应该检测到流动性问题
        tags = generator.get_all_tags()
        self.assertTrue(
            any(tag in tags for tag in ['流动性差', '成交额低']),
            f"应该检测到流动性问题，但标签为: {tags}"
        )


class TestMergeIssuesToTags(unittest.TestCase):
    """测试快捷函数"""
    
    def test_merge_issues(self):
        """测试合并问题为标签"""
        issues = ['应收账款异常', '高波动', '除权缺口']
        
        tag_str = merge_issues_to_tags(issues)
        
        self.assertIn('应收账款异常', tag_str)
        self.assertIn('高波动', tag_str)
        self.assertIn('除权缺口', tag_str)
    
    def test_merge_empty_issues(self):
        """测试空问题列表"""
        tag_str = merge_issues_to_tags([])
        
        self.assertEqual(tag_str, "")


if __name__ == '__main__':
    unittest.main()
