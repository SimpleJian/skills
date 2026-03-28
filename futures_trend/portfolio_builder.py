#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合构建模块

组合结构：
- 核心持仓：3-5个品种，单品种15-20万（上限20万）
- 观察备选：2-3个品种，单品种5-10万
- 板块分散：同一板块最多2个品种
- 相关性控制：高度相关品种最多1个
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class PortfolioBuilder:
    """期货组合构建器"""
    
    def __init__(self, total_capital: float = 1000000):
        """
        初始化
        
        Args:
            total_capital: 总资金规模，默认100万
        """
        self.total_capital = total_capital
        
        # 仓位限制
        self.max_position_per_contract = 200000  # 单品种上限20万
        self.min_position_per_contract = 50000   # 单品种下限5万
        self.core_position = 150000  # 核心仓位15万
        
        # 板块限制
        self.max_per_sector = 2  # 同板块最多2个
        
        # 组合结构
        self.core_count = 5  # 核心品种数量
        self.backup_count = 3  # 备选品种数量
    
    def get_commodity_sector(self, ts_code: str) -> str:
        """
        获取商品所属板块
        """
        # 从合约代码提取品种代码
        symbol = ts_code.split('.')[0]
        product = ''.join([c for c in symbol if not c.isdigit()])
        
        # 板块分类
        sector_map = {
            # 有色金属
            'CU': '有色金属', 'AL': '有色金属', 'ZN': '有色金属', 'PB': '有色金属', 
            'NI': '有色金属', 'SN': '有色金属', 'SS': '有色金属',
            # 黑色金属
            'RB': '黑色金属', 'HC': '黑色金属', 'I': '黑色金属', 'J': '黑色金属', 
            'JM': '黑色金属', 'FG': '黑色金属',
            # 能源化工
            'SC': '能源', 'FU': '能源', 'BU': '能源', 'PG': '能源',
            'TA': '化工', 'MA': '化工', 'PP': '化工', 'L': '化工', 
            'PVC': '化工', 'EG': '化工', 'EB': '化工', 'PF': '化工',
            # 农产品
            'M': '农产品', 'Y': '农产品', 'P': '农产品', 'A': '农产品', 
            'C': '农产品', 'CS': '农产品', 'LH': '农产品',
            'CF': '农产品', 'SR': '农产品', 'OI': '农产品', 'RM': '农产品',
            # 贵金属
            'AU': '贵金属', 'AG': '贵金属',
            # 其他
            'RU': '化工', 'SP': '化工', 'SA': '化工',
        }
        
        return sector_map.get(product, '其他')
    
    def check_correlation(self, code1: str, code2: str) -> float:
        """
        检查两个品种的相关性
        
        简化处理：同一板块内品种相关性较高
        """
        sector1 = self.get_commodity_sector(code1)
        sector2 = self.get_commodity_sector(code2)
        
        # 产业链关系
       产业链_pairs = [
            ('JM', 'J'), ('J', 'RB'), ('J', 'HC'),  # 焦煤-焦炭-钢材
            ('I', 'RB'), ('I', 'HC'),  # 铁矿石-钢材
            ('SC', 'TA'), ('SC', 'FU'), ('SC', 'BU'),  # 原油-化工/能源
            ('M', 'Y'), ('M', 'P'),  # 豆粕-油脂
        ]
        
        # 检查是否在产业链上
        pair1 = (code1.split('.')[0][:2], code2.split('.')[0][:2])
        pair2 = (code2.split('.')[0][:2], code1.split('.')[0][:2])
        
        if pair1 in 产业链_pairs or pair2 in 产业链_pairs:
            return 0.8  # 高度相关
        
        # 同板块
        if sector1 == sector2:
            return 0.6  # 中等相关
        
        return 0.3  # 低相关
    
    def build_portfolio(self, df_long: pd.DataFrame, df_short: pd.DataFrame, 
                       market_env: str = '震荡') -> Dict:
        """
        构建投资组合
        
        Args:
            df_long: 多头候选
            df_short: 空头候选
            market_env: 市场环境（强牛/弱牛/震荡/弱熊/强熊）
            
        Returns:
            {
                'core_long': 核心多头,
                'core_short': 核心空头,
                'backup_long': 备选多头,
                'backup_short': 备选空头,
                'position_ratio': 仓位比例建议
            }
        """
        print()
        print("=" * 70)
        print("组合构建")
        print("=" * 70)
        print(f"市场环境: {market_env}")
        print(f"资金规模: {self.total_capital/10000:.0f}万")
        print()
        
        # 根据市场环境确定多空配置
        env_config = {
            '强牛': {'net_exposure': 1.0, 'long_ratio': 1.0, 'short_ratio': 0.0},
            '弱牛': {'net_exposure': 0.6, 'long_ratio': 0.8, 'short_ratio': 0.2},
            '震荡': {'net_exposure': 0.0, 'long_ratio': 0.5, 'short_ratio': 0.5},
            '弱熊': {'net_exposure': -0.6, 'long_ratio': 0.2, 'short_ratio': 0.8},
            '强熊': {'net_exposure': -1.0, 'long_ratio': 0.0, 'short_ratio': 1.0},
        }
        
        config = env_config.get(market_env, env_config['震荡'])
        
        # 选择核心品种
        core_long = self._select_core(df_long, '多头', config['long_ratio'])
        core_short = self._select_core(df_short, '空头', config['short_ratio'])
        
        # 选择备选品种
        backup_long = self._select_backup(df_long, core_long, '多头')
        backup_short = self._select_backup(df_short, core_short, '空头')
        
        # 计算仓位分配
        position_allocation = self._calculate_position_allocation(
            core_long, core_short, backup_long, backup_short, config
        )
        
        return {
            'core_long': core_long,
            'core_short': core_short,
            'backup_long': backup_long,
            'backup_short': backup_short,
            'position_ratio': position_allocation,
            'net_exposure': config['net_exposure']
        }
    
    def _select_core(self, df: pd.DataFrame, direction: str, ratio: float) -> pd.DataFrame:
        """
        选择核心品种
        """
        if len(df) == 0 or ratio == 0:
            return pd.DataFrame()
        
        # 计算需要的数量
        count = int(self.core_count * ratio)
        if count == 0 and ratio > 0:
            count = 1
        
        selected = []
        sector_count = {}
        
        for idx, row in df.iterrows():
            if len(selected) >= count:
                break
            
            ts_code = row['ts_code']
            sector = self.get_commodity_sector(ts_code)
            
            # 检查板块限制
            if sector_count.get(sector, 0) >= self.max_per_sector:
                continue
            
            # 检查相关性
            too_correlated = False
            for sel in selected:
                corr = self.check_correlation(ts_code, sel['ts_code'])
                if corr >= 0.8:  # 高度相关
                    too_correlated = True
                    break
            
            if too_correlated:
                continue
            
            selected.append(row)
            sector_count[sector] = sector_count.get(sector, 0) + 1
        
        if len(selected) > 0:
            return pd.DataFrame(selected)
        return pd.DataFrame()
    
    def _select_backup(self, df: pd.DataFrame, core_df: pd.DataFrame, direction: str) -> pd.DataFrame:
        """
        选择备选品种
        """
        if len(df) == 0:
            return pd.DataFrame()
        
        # 排除已选入核心的品种
        if len(core_df) > 0:
            core_codes = set(core_df['ts_code'].tolist())
            df = df[~df['ts_code'].isin(core_codes)]
        
        # 选择前2-3个
        count = min(self.backup_count, len(df))
        if count == 0:
            return pd.DataFrame()
        
        return df.head(count)
    
    def _calculate_position_allocation(self, core_long: pd.DataFrame, core_short: pd.DataFrame,
                                      backup_long: pd.DataFrame, backup_short: pd.DataFrame,
                                      config: Dict) -> Dict:
        """
        计算仓位分配
        """
        allocation = {}
        
        # 核心多头仓位
        if len(core_long) > 0:
            core_long_capital = min(self.core_position, self.total_capital * 0.15)
            for idx, row in core_long.iterrows():
                allocation[row['ts_code']] = {
                    'direction': '多头',
                    'capital': core_long_capital,
                    'type': '核心'
                }
        
        # 核心空头仓位
        if len(core_short) > 0:
            core_short_capital = min(self.core_position, self.total_capital * 0.15)
            for idx, row in core_short.iterrows():
                allocation[row['ts_code']] = {
                    'direction': '空头',
                    'capital': core_short_capital,
                    'type': '核心'
                }
        
        # 备选多头仓位
        if len(backup_long) > 0:
            backup_capital = self.total_capital * 0.05  # 5万试探
            for idx, row in backup_long.iterrows():
                if row['ts_code'] not in allocation:
                    allocation[row['ts_code']] = {
                        'direction': '多头',
                        'capital': backup_capital,
                        'type': '备选'
                    }
        
        # 备选空头仓位
        if len(backup_short) > 0:
            backup_capital = self.total_capital * 0.05
            for idx, row in backup_short.iterrows():
                if row['ts_code'] not in allocation:
                    allocation[row['ts_code']] = {
                        'direction': '空头',
                        'capital': backup_capital,
                        'type': '备选'
                    }
        
        return allocation
    
    def print_portfolio(self, portfolio: Dict):
        """
        打印组合配置
        """
        print()
        print("=" * 70)
        print("最终组合配置")
        print("=" * 70)
        print()
        
        # 核心多头
        core_long = portfolio['core_long']
        if len(core_long) > 0:
            print(f"【核心多头】{len(core_long)}只 - 建议仓位15-20万/只")
            print(core_long[['ts_code', 'name', 'adx', 'trend_score']].to_string(index=False))
            print()
        
        # 核心空头
        core_short = portfolio['core_short']
        if len(core_short) > 0:
            print(f"【核心空头】{len(core_short)}只 - 建议仓位15-20万/只")
            print(core_short[['ts_code', 'name', 'adx', 'trend_score']].to_string(index=False))
            print()
        
        # 备选品种
        backup_long = portfolio['backup_long']
        backup_short = portfolio['backup_short']
        
        if len(backup_long) > 0 or len(backup_short) > 0:
            print(f"【观察备选】")
            if len(backup_long) > 0:
                print(f"  多头备选: {', '.join(backup_long['name'].tolist())}")
            if len(backup_short) > 0:
                print(f"  空头备选: {', '.join(backup_short['name'].tolist())}")
            print()
        
        # 仓位汇总
        print("=" * 70)
        print("仓位配置建议")
        print("=" * 70)
        
        allocation = portfolio['position_ratio']
        total_capital_used = sum([v['capital'] for v in allocation.values()])
        
        print(f"总资金使用: {total_capital_used/10000:.0f}万 / {self.total_capital/10000:.0f}万")
        print(f"净敞口: {portfolio['net_exposure']*100:.0f}%")
        print()
        
        for code, alloc in allocation.items():
            print(f"{code}: {alloc['direction']} {alloc['type']} 资金{alloc['capital']/10000:.0f}万")


if __name__ == '__main__':
    builder = PortfolioBuilder(total_capital=1000000)
    
    # 测试数据
    test_data = {
        'ts_code': ['CU.SHF', 'RB.SHF', 'M.DCE'],
        'name': ['沪铜', '螺纹钢', '豆粕'],
        'adx': [35, 40, 30],
        'trend_score': [80, 85, 75]
    }
    df_test = pd.DataFrame(test_data)
    
    sector = builder.get_commodity_sector('CU.SHF')
    print(f"CU.SHF 所属板块: {sector}")
