#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险标签生成模块

为标的生成多维度风险标签，供上层风控参考
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


@dataclass
class RiskTag:
    """风险标签"""
    category: str      # 类别：财务/流动性/政策/数据/波动
    tag: str          # 具体标签
    level: RiskLevel  # 风险等级
    description: str  # 描述


class RiskTagGenerator:
    """风险标签生成器"""
    
    # 风险类别定义
    CATEGORIES = {
        '财务风险': ['应收账款异常', '现金流质量差', '存贷双高', '高商誉', '盈利波动大', '财务数据为空'],
        '流动性风险': ['成交额过低', '流动性差', '即将到期', '临近换月', '已到期', '无成交量'],
        '政策风险': ['监管政策打压', '行业衰退期', 'ST风险'],
        '数据质量': ['数据为空', '除权缺口', '价格 discontinuity', '价格异常值', '部分停牌', '近期停牌', '新股'],
        '波动风险': ['极高波动', '高波动', '异动', 'ATR异常']
    }
    
    def __init__(self):
        self.tags = []
    
    def add_tag(self, category: str, tag: str, level: RiskLevel = RiskLevel.MEDIUM, 
                description: str = ""):
        """添加标签"""
        self.tags.append(RiskTag(category, tag, level, description))
    
    def add_raw_issues(self, issues: List[str]):
        """从原始问题列表生成标签"""
        for issue in issues:
            self._classify_issue(issue)
    
    def _classify_issue(self, issue: str):
        """分类问题到对应类别和等级"""
        # 财务风险 - 高
        if issue in ['应收账款异常', '现金流质量差', '存贷双高']:
            self.add_tag('财务风险', issue, RiskLevel.HIGH, "可能存在财务造假或资金占用")
        elif issue in ['高商誉']:
            self.add_tag('财务风险', issue, RiskLevel.HIGH, "并购后遗症风险")
        elif issue in ['盈利波动大']:
            self.add_tag('财务风险', issue, RiskLevel.MEDIUM, "盈利稳定性差")
        elif issue in ['财务数据为空']:
            self.add_tag('财务风险', issue, RiskLevel.MEDIUM, "无法评估财务状况")
        
        # 流动性风险 - 极高
        elif issue in ['即将到期', '已到期']:
            self.add_tag('流动性风险', issue, RiskLevel.CRITICAL, "合约即将到期，需立即移仓或平仓")
        elif issue in ['临近换月']:
            self.add_tag('流动性风险', issue, RiskLevel.HIGH, "建议切换至下一主力合约")
        elif issue in ['成交额过低', '流动性差', '无成交量']:
            self.add_tag('流动性风险', issue, RiskLevel.HIGH, "可能无法按预期价格成交")
        elif issue in ['部分停牌']:
            self.add_tag('流动性风险', issue, RiskLevel.MEDIUM, "存在停牌交易日")
        
        # 政策风险
        elif issue in ['监管政策打压', '行业衰退期', 'ST风险']:
            self.add_tag('政策风险', issue, RiskLevel.HIGH, "政策面不利")
        
        # 数据质量 - 中低
        elif issue in ['除权缺口', '价格 discontinuity']:
            self.add_tag('数据质量', issue, RiskLevel.MEDIUM, "数据可能存在复权问题，技术指标可能失真")
        elif issue in ['价格异常值']:
            self.add_tag('数据质量', issue, RiskLevel.MEDIUM, "价格数据存在异常")
        elif issue in ['数据为空']:
            self.add_tag('数据质量', issue, RiskLevel.HIGH, "无法获取数据")
        elif issue in ['近期停牌']:
            self.add_tag('数据质量', issue, RiskLevel.MEDIUM, "近期存在停牌，注意流动性风险")
        elif issue in ['新股']:
            self.add_tag('数据质量', issue, RiskLevel.LOW, "上市时间较短，历史数据不足")
        
        # 波动风险
        elif issue in ['极高波动']:
            self.add_tag('波动风险', issue, RiskLevel.CRITICAL, "年化波动>60%，风险极高")
        elif issue in ['高波动']:
            self.add_tag('波动风险', issue, RiskLevel.HIGH, "年化波动>40%，需谨慎")
        elif issue in ['ATR异常']:
            self.add_tag('波动风险', issue, RiskLevel.HIGH, "近期波动剧烈，止损需放宽")
        elif issue in ['异动']:
            self.add_tag('波动风险', issue, RiskLevel.MEDIUM, "近期有大幅异动")
        
        # 其他未分类
        else:
            self.add_tag('其他', issue, RiskLevel.MEDIUM, "")
    
    def get_tags_string(self, max_tags: int = 5) -> str:
        """
        获取标签字符串（|分隔）
        
        Args:
            max_tags: 最多返回的标签数量，按风险等级排序
        """
        if not self.tags:
            return ""
        
        # 按风险等级排序
        level_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, 
                      RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        sorted_tags = sorted(self.tags, key=lambda x: level_order[x.level])
        
        # 取前N个
        selected_tags = sorted_tags[:max_tags]
        
        # 拼接
        return "|".join([tag.tag for tag in selected_tags])
    
    def get_all_tags(self) -> List[str]:
        """获取所有标签列表"""
        return [tag.tag for tag in self.tags]
    
    def get_critical_tags(self) -> List[str]:
        """获取极高风险标签"""
        return [tag.tag for tag in self.tags if tag.level == RiskLevel.CRITICAL]
    
    def has_critical_risk(self) -> bool:
        """是否存在极高风险"""
        return any(tag.level == RiskLevel.CRITICAL for tag in self.tags)
    
    def get_risk_summary(self) -> Dict:
        """获取风险汇总"""
        summary = {
            'total': len(self.tags),
            'critical': len([t for t in self.tags if t.level == RiskLevel.CRITICAL]),
            'high': len([t for t in self.tags if t.level == RiskLevel.HIGH]),
            'medium': len([t for t in self.tags if t.level == RiskLevel.MEDIUM]),
            'low': len([t for t in self.tags if t.level == RiskLevel.LOW]),
            'categories': {}
        }
        
        for tag in self.tags:
            cat = tag.category
            if cat not in summary['categories']:
                summary['categories'][cat] = []
            summary['categories'][cat].append(tag.tag)
        
        return summary


class AShareRiskAnalyzer:
    """A股风险分析器"""
    
    def __init__(self, api=None):
        self.api = api
        self.tag_generator = RiskTagGenerator()
    
    def analyze_stock(self, ts_code: str, price_df: pd.DataFrame = None, 
                     financial_df: pd.DataFrame = None) -> RiskTagGenerator:
        """
        分析单个股票风险
        
        Args:
            ts_code: 股票代码
            price_df: 价格数据
            financial_df: 财务数据
        
        Returns:
            RiskTagGenerator 包含所有风险标签
        """
        generator = RiskTagGenerator()
        
        # 1. 价格数据风险
        if price_df is not None and not price_df.empty:
            # 停牌检查
            if 'volume' in price_df.columns:
                recent_volume = price_df['volume'].tail(5)
                if (recent_volume == 0).any():
                    generator.add_tag('流动性风险', '近期停牌', RiskLevel.MEDIUM)
            
            # 波动率
            if 'close' in price_df.columns:
                returns = price_df['close'].pct_change().dropna()
                if len(returns) >= 20:
                    vol = returns.std() * np.sqrt(252)
                    if vol > 0.6:
                        generator.add_tag('波动风险', '极高波动', RiskLevel.CRITICAL)
                    elif vol > 0.4:
                        generator.add_tag('波动风险', '高波动', RiskLevel.HIGH)
        
        # 2. 财务风险
        if financial_df is not None and not financial_df.empty:
            # 简单财务检查
            if 'roe' in financial_df.columns:
                recent_roe = financial_df['roe'].dropna()
                if len(recent_roe) >= 3:
                    roe_std = recent_roe.std()
                    if roe_std > 10:
                        generator.add_tag('财务风险', '盈利波动大', RiskLevel.MEDIUM)
        
        # 3. 特殊处理标记（ST、退市等）
        if ts_code.startswith(('ST', '*ST')):
            generator.add_tag('政策风险', 'ST风险', RiskLevel.CRITICAL)
        
        return generator
    
    def batch_analyze(self, stocks_data: Dict[str, Dict]) -> Dict[str, RiskTagGenerator]:
        """
        批量分析
        
        Args:
            stocks_data: {ts_code: {'price': df, 'financial': df}}
        
        Returns:
            {ts_code: RiskTagGenerator}
        """
        results = {}
        for ts_code, data in stocks_data.items():
            generator = self.analyze_stock(
                ts_code, 
                data.get('price'), 
                data.get('financial')
            )
            results[ts_code] = generator
        return results


class FuturesRiskAnalyzer:
    """期货风险分析器"""
    
    def __init__(self, api=None):
        self.api = api
    
    def analyze_contract(self, contract_code: str, price_df: pd.DataFrame = None,
                        days_to_expiry: int = 999) -> RiskTagGenerator:
        """
        分析期货合约风险
        """
        generator = RiskTagGenerator()
        
        # 1. 到期风险
        if days_to_expiry < 0:
            generator.add_tag('流动性风险', '已到期', RiskLevel.CRITICAL)
        elif days_to_expiry < 7:
            generator.add_tag('流动性风险', '即将到期', RiskLevel.CRITICAL)
        elif days_to_expiry < 15:
            generator.add_tag('流动性风险', '临近换月', RiskLevel.HIGH)
        
        # 2. 流动性风险
        if price_df is not None and not price_df.empty:
            if 'volume' in price_df.columns:
                avg_volume = price_df['volume'].mean()
                if avg_volume < 1000:
                    generator.add_tag('流动性风险', '流动性差', RiskLevel.HIGH)
        
        # 3. 波动风险
        if price_df is not None and 'close' in price_df.columns:
            returns = price_df['close'].pct_change().dropna()
            if len(returns) >= 20:
                vol = returns.std() * np.sqrt(252)
                if vol > 0.5:
                    generator.add_tag('波动风险', '高波动', RiskLevel.HIGH)
        
        return generator


def merge_issues_to_tags(issues: List[str]) -> str:
    """
    将问题列表合并为标签字符串
    
    快捷函数
    """
    generator = RiskTagGenerator()
    generator.add_raw_issues(issues)
    return generator.get_tags_string()


def format_output_with_tags(ts_code: str, score: float, signal: str, 
                           risk_tags: str, reason: str) -> Dict:
    """
    格式化带标签的输出
    """
    return {
        'ts_code': ts_code,
        'score': score,
        'signal': signal,
        'risk_tags': risk_tags if risk_tags else "无",
        'reason': reason
    }
