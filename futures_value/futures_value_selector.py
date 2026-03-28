#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品期货价值抄底选股策略 - 主选股模块

三层筛选体系：
1. 第一层：技术面超卖初筛（RSI、KDJ、CCI、布林带等）
2. 第二层：基本面价值精筛（期限结构、成本、库存、利润）
3. 第三层：情绪资金验证（持仓结构、资金流向、波动率）

多因子评分模型：
- 技术面超卖 (25%)
- 基本面价值 (40%) - 权重最高
- 情绪资金 (25%)
- 跨市场验证 (10%)

优先板块：贵金属 > 有色金属 > 能源化工 > 农产品
"""

import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime

from technical_oversold import TechnicalOversold
from fundamental_value import FundamentalValue
from sentiment_verification import SentimentVerification
from value_scorer import FuturesValueScorer, PortfolioBuilder


class FuturesValueSelector:
    """
    商品期货价值抄底选股器
    
    策略定位：识别"被低估"而非"价格低"的标的
    核心逻辑：市场情绪过度反应后的基本面回归
    适用场景：流动性冲击、板块轮动中的结构性低估、事件驱动错杀
    """
    
    def __init__(self, pro_api, total_capital: float = 1000000):
        self.pro = pro_api
        self.total_capital = total_capital
        
        # 初始化各模块
        self.tech = TechnicalOversold(pro_api)
        self.fund = FundamentalValue(pro_api)
        self.sent = SentimentVerification(pro_api)
        self.scorer = FuturesValueScorer(pro_api)
        self.builder = PortfolioBuilder(total_capital)
    
    def get_liquid_contracts(self, min_volume: int = 50000) -> pd.DataFrame:
        """
        获取流动性好的合约列表
        """
        try:
            # 获取期货基础信息
            df_basic = self.pro.fut_basic(exchange='', fut_type='2')
            
            if df_basic is None or len(df_basic) == 0:
                return pd.DataFrame()
            
            # 简化处理，返回主力合约列表
            # 实际应该根据成交量筛选
            return df_basic[['ts_code', 'name']]
        
        except:
            return pd.DataFrame()
    
    def select_contracts(self, 
                        tech_min_score: int = 60,
                        fund_min_score: int = 50,
                        sent_min_score: int = 50) -> Dict:
        """
        执行完整选股流程
        
        Args:
            tech_min_score: 技术面最低评分
            fund_min_score: 基本面最低评分
            sent_min_score: 情绪资金最低评分
            
        Returns:
            选股结果
        """
        start_time = datetime.now()
        
        print()
        print("=" * 80)
        print("商品期货价值抄底选股策略")
        print("=" * 80)
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"资金规模: {self.total_capital/10000:.0f}万")
        print("=" * 80)
        print()
        print("策略理念: 识别'被低估'而非'价格低'的标的")
        print("核心逻辑: 市场情绪过度反应后的基本面回归")
        print()
        print("三层筛选体系：")
        print("  第一层: 技术面超卖初筛（RSI<30、KDJ-J<0、CCI<-100等）")
        print("  第二层: 基本面价值精筛（期限结构、成本支撑、库存）")
        print("  第三层: 情绪资金验证（持仓结构、资金流向、波动率）")
        print()
        print("多因子评分权重：")
        print("  技术面超卖: 25%")
        print("  基本面价值: 40%（权重最高）")
        print("  情绪资金: 25%")
        print("  跨市场验证: 10%")
        print()
        
        # 获取候选合约列表
        df_candidates = self.get_liquid_contracts()
        
        if len(df_candidates) == 0:
            print("无法获取合约列表")
            return {}
        
        print(f"全市场合约数量: {len(df_candidates)}")
        print()
        
        # 第一层筛选：技术面超卖
        df_oversold = self.tech.filter_oversold(df_candidates, min_score=tech_min_score)
        
        if len(df_oversold) == 0:
            print("警告：没有合约通过技术面超卖筛选")
            return {}
        
        # 第二层筛选：基本面价值
        df_value = self.fund.filter_fundamental_value(df_oversold, min_score=fund_min_score)
        
        if len(df_value) == 0:
            print("警告：没有合约通过基本面价值筛选")
            return {}
        
        # 第三层筛选：情绪资金验证
        df_sentiment = self.sent.filter_sentiment(df_value, min_score=sent_min_score)
        
        if len(df_sentiment) == 0:
            print("警告：没有合约通过情绪资金验证")
            # 使用基本面筛选结果继续
            df_sentiment = df_value
        
        # 多因子综合评分
        df_scored = self.scorer.rank_contracts(df_sentiment)
        
        # 组合构建
        portfolio = self.builder.build_portfolio(df_scored)
        
        # 输出最终结果
        self._print_final_results(portfolio)
        
        # 完成
        print()
        print("=" * 80)
        print(f"选股完成！耗时: {(datetime.now() - start_time).total_seconds():.1f} 秒")
        print("=" * 80)
        
        return portfolio
    
    def _print_final_results(self, portfolio: Dict):
        """
        打印最终结果
        """
        print()
        print("=" * 70)
        print("最终选股结果")
        print("=" * 70)
        print()
        
        # 核心池
        core_pool = portfolio.get('core_pool', pd.DataFrame())
        if len(core_pool) > 0:
            print(f"🔴 【核心池】{len(core_pool)}只 (评分≥80)")
            print("    建议: 优先配置，深度价值，仓位15-20%/只")
            print()
            print(core_pool.head(10)[['ts_code', 'name', 'total_score', 'fund_score', 'tech_score']].to_string(index=False))
            print()
        
        # 观察池
        watch_pool = portfolio.get('watch_pool', pd.DataFrame())
        if len(watch_pool) > 0:
            print(f"🟡 【观察池】{len(watch_pool)}只 (评分60-80)")
            print("    建议: 持续跟踪，待验证，仓位5-8%/只")
            print()
        
        # 备选池
        backup_pool = portfolio.get('backup_pool', pd.DataFrame())
        if len(backup_pool) > 0:
            print(f"🔵 【备选池】{len(backup_pool)}只 (评分40-60)")
            print("    建议: 关注催化因素")
            print()
        
        # 最终配置
        selected = portfolio.get('selected', pd.DataFrame())
        if len(selected) > 0:
            print("=" * 70)
            print("推荐配置")
            print("=" * 70)
            print()
            
            for idx, row in selected.iterrows():
                capital = row['position_pct'] * self.total_capital / 10000
                print(f"{idx+1}. {row['ts_code']} {row['name']} ({row['sector']})")
                print(f"   分级: {row['level']} | 评分: {row['score']}")
                print(f"   建议仓位: {row['position_pct']*100:.0f}% ({capital:.0f}万)")
                print()


if __name__ == '__main__':
    import tushare as ts
    import os
    
    # 初始化Tushare
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("请设置 TUSHARE_TOKEN 环境变量")
        exit(1)
    
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 创建选股器
    selector = FuturesValueSelector(pro, total_capital=1000000)
    
    # 执行选股
    result = selector.select_contracts()
