#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分模型

维度与权重：
- 技术面超卖 (25%)
- 基本面价值 (40%) - 权重最高
- 情绪资金 (25%)
- 跨市场验证 (10%)

分级：
- 核心池：≥80分
- 观察池：60-80分
- 备选池：40-60分
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import time
import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.api_utils import APIRateLimiter

from technical_oversold import TechnicalOversold
from fundamental_value import FundamentalValue
from sentiment_verification import SentimentVerification


class FuturesValueScorer:
    """期货价值评分器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.tech = TechnicalOversold(pro_api)
        self.fund = FundamentalValue(pro_api)
        self.sent = SentimentVerification(pro_api)
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def calculate_comprehensive_score(self, ts_code: str) -> Dict:
        """
        计算综合评分
        
        权重配置：
        - 技术面超卖: 25%
        - 基本面价值: 40%
        - 情绪资金: 25%
        - 跨市场验证: 10%
        """
        try:
            # 技术面评分
            df_tech = self.tech.get_fut_data(ts_code)
            if len(df_tech) >= 60:
                df_tech = self.tech.calculate_rsi(df_tech)
                df_tech = self.tech.calculate_kdj(df_tech)
                df_tech = self.tech.calculate_cci(df_tech)
                df_tech = self.tech.calculate_williams_r(df_tech)
                df_tech = self.tech.calculate_bollinger(df_tech)
                df_tech = self.tech.calculate_ma_deviation(df_tech)
                
                tech_signals = self.tech.check_oversold_signals(df_tech)
                tech_score = tech_signals['oversold_score']
            else:
                tech_score = 0
            
            # 基本面评分
            fund_check = self.fund.comprehensive_fundamental_check(ts_code)
            fund_score = fund_check['fundamental_score']
            
            # 情绪资金评分
            sent_check = self.sent.comprehensive_sentiment_check(ts_code)
            sent_score = sent_check['sentiment_score']
            
            # 跨市场验证（简化处理，使用价格相对位置）
            # 如果价格处于历史极低位置，给予额外加分
            price_percentile = fund_check.get('basis', {}).get('price_percentile', 50)
            if price_percentile < 10:
                cross_score = 10
            elif price_percentile < 20:
                cross_score = 8
            elif price_percentile < 30:
                cross_score = 5
            else:
                cross_score = 0
            
            # 加权总分
            total_score = (
                tech_score * 0.25 +
                fund_score * 0.40 +
                sent_score * 0.25 +
                cross_score * 1.0  # 已经是10分制
            )
            
            # 分级
            if total_score >= 80:
                level = '核心池'
                suggestion = '优先配置，深度价值'
            elif total_score >= 60:
                level = '观察池'
                suggestion = '持续跟踪，待验证'
            elif total_score >= 40:
                level = '备选池'
                suggestion = '关注催化因素'
            else:
                level = '排除'
                suggestion = '不符合标准'
            
            return {
                'ts_code': ts_code,
                'total_score': round(total_score, 2),
                'level': level,
                'suggestion': suggestion,
                'tech_score': tech_score,
                'fund_score': fund_score,
                'sent_score': sent_score,
                'cross_score': cross_score,
                'details': {
                    'tech_signals': tech_signals.get('signals', []),
                    'fund_status': fund_check.get('cost', {}).get('cost_status', ''),
                    'sent_status': sent_check.get('position', {}).get('position_status', '')
                }
            }
        
        except Exception as e:
            return {
                'ts_code': ts_code,
                'total_score': 0,
                'level': '错误',
                'error': str(e)
            }
    
    def rank_contracts(self, df_candidates: pd.DataFrame, 
                       risk_tags_map: dict = None) -> pd.DataFrame:
        """
        对候选合约进行综合评分排名（含风险标签）
        """
        print()
        print("=" * 70)
        print("多因子综合评分")
        print("=" * 70)
        print()
        
        results = []
        
        for idx, row in df_candidates.iterrows():
            ts_code = row.get('ts_code')
            name = row.get('name', '')
            
            score_result = self.calculate_comprehensive_score(ts_code)
            
            # 获取风险标签
            risk_tags = risk_tags_map.get(ts_code, "") if risk_tags_map else ""
            
            results.append({
                'ts_code': ts_code,
                'name': name,
                'total_score': score_result['total_score'],
                'level': score_result['level'],
                'tech_score': score_result['tech_score'],
                'fund_score': score_result['fund_score'],
                'sent_score': score_result['sent_score'],
                'suggestion': score_result['suggestion'],
                'risk_tags': risk_tags
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        print(f"评分完成，共 {len(df)} 只合约")
        
        return df
    
    def get_pool_recommendation(self, score: float, level: str) -> str:
        """
        根据评分给出仓位建议
        """
        if level == '核心池':
            if score >= 85:
                return '核心仓位：建议配置15-20%'
            else:
                return '核心仓位：建议配置10-15%'
        elif level == '观察池':
            return '观察仓位：建议配置5-8%'
        elif level == '备选池':
            return '备选关注：建议配置2-5%'
        else:
            return '建议回避'


class PortfolioBuilder:
    """组合构建器"""
    
    def __init__(self, total_capital: float = 1000000):
        self.total_capital = total_capital
        self.max_per_sector = 2  # 同板块最多2个
        self.sector_priority = {
            '贵金属': 1,
            '有色金属': 2,
            '能源化工': 3,
            '农产品': 4,
            '黑色金属': 5,
            '其他': 6
        }
    
    def get_commodity_sector(self, ts_code: str) -> str:
        """获取商品所属板块"""
        symbol = ts_code.split('.')[0]
        product = ''.join([c for c in symbol if not c.isdigit()])
        
        sector_map = {
            'AU': '贵金属', 'AG': '贵金属',
            'CU': '有色金属', 'AL': '有色金属', 'ZN': '有色金属', 'PB': '有色金属', 
            'NI': '有色金属', 'SN': '有色金属', 'SS': '有色金属',
            'SC': '能源化工', 'FU': '能源化工', 'BU': '能源化工', 'PG': '能源化工',
            'TA': '能源化工', 'MA': '能源化工', 'PP': '能源化工', 'L': '能源化工', 
            'PVC': '能源化工', 'EG': '能源化工', 'EB': '能源化工', 'PF': '能源化工',
            'M': '农产品', 'Y': '农产品', 'P': '农产品', 'A': '农产品', 
            'C': '农产品', 'CS': '农产品', 'CF': '农产品', 'SR': '农产品',
            'RB': '黑色金属', 'HC': '黑色金属', 'I': '黑色金属', 'J': '黑色金属', 'JM': '黑色金属',
        }
        
        return sector_map.get(product, '其他')
    
    def build_portfolio(self, df_scored: pd.DataFrame) -> Dict:
        """
        构建投资组合
        """
        print()
        print("=" * 70)
        print("组合构建")
        print("=" * 70)
        print()
        
        # 筛选核心池和观察池
        core_pool = df_scored[df_scored['level'] == '核心池']
        watch_pool = df_scored[df_scored['level'] == '观察池']
        backup_pool = df_scored[df_scored['level'] == '备选池']
        
        # 选择标的（考虑板块分散）
        selected = []
        sector_count = {}
        
        # 优先选择高优先级板块
        for idx, row in core_pool.iterrows():
            if len(selected) >= 5:  # 核心品种不超过5个
                break
            
            ts_code = row['ts_code']
            sector = self.get_commodity_sector(ts_code)
            
            if sector_count.get(sector, 0) >= self.max_per_sector:
                continue
            
            selected.append({
                'ts_code': ts_code,
                'name': row['name'],
                'sector': sector,
                'score': row['total_score'],
                'level': '核心',
                'position_pct': 0.15 if row['total_score'] >= 85 else 0.10
            })
            sector_count[sector] = sector_count.get(sector, 0) + 1
        
        # 从观察池补充
        for idx, row in watch_pool.iterrows():
            if len(selected) >= 8:  # 总品种不超过8个
                break
            
            ts_code = row['ts_code']
            sector = self.get_commodity_sector(ts_code)
            
            if sector_count.get(sector, 0) >= self.max_per_sector:
                continue
            
            selected.append({
                'ts_code': ts_code,
                'name': row['name'],
                'sector': sector,
                'score': row['total_score'],
                'level': '观察',
                'position_pct': 0.08
            })
            sector_count[sector] = sector_count.get(sector, 0) + 1
        
        df_selected = pd.DataFrame(selected)
        
        print(f"核心池: {len(core_pool)}只")
        print(f"观察池: {len(watch_pool)}只")
        print(f"备选池: {len(backup_pool)}只")
        print()
        
        if len(df_selected) > 0:
            print("最终配置：")
            print(df_selected[['ts_code', 'name', 'sector', 'level', 'score', 'position_pct']].to_string(index=False))
        
        return {
            'core_pool': core_pool,
            'watch_pool': watch_pool,
            'backup_pool': backup_pool,
            'selected': df_selected,
            'sector_count': sector_count
        }


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    scorer = FuturesValueScorer(pro)
    
    # 测试
    result = scorer.calculate_comprehensive_score('CU.SHF')
    print(f"沪铜综合评分: {result['total_score']}")
    print(f"分级: {result['level']}")
    print(f"建议: {result['suggestion']}")
