#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股价值抄底选股策略 - 主选股模块

三阶筛选体系：
1. 初阶筛选：估值安全边际（PE/PB/股息率）
2. 精阶筛选：盈利能力与财务健康度（ROE/毛利率/现金流）
3. 高阶筛选：成长性验证与错杀时机判断

多因子评分模型：
- 估值安全（40%）
- 盈利质量（25%）
- 财务健康（20%）
- 成长潜力（15%）
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime

import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.data_quality import DataPreprocessor, create_default_processor
from tushare_utils.risk_tags import RiskTagGenerator, merge_issues_to_tags, AShareRiskAnalyzer

from valuation_filter import ValuationFilter
from quality_filter import QualityFilter
from growth_analyzer import GrowthAnalyzer
from value_scorer import ValueScorer


class ValueSelector:
    """
    A股价值抄底选股器
    
    核心逻辑：
    1. 初阶筛选：找出低估值高股息的安全标的
    2. 精阶筛选：验证盈利质量和财务健康度
    3. 高阶筛选：评估成长性和错杀信号
    4. 多因子评分：综合排序确定最终标的
    """
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.valuation = ValuationFilter(pro_api)
        self.quality = QualityFilter(pro_api)
        self.growth = GrowthAnalyzer(pro_api)
        self.scorer = ValueScorer(pro_api)
        self.data_processor = create_default_processor(pro_api)
        self.risk_analyzer = AShareRiskAnalyzer(pro_api)
        self.stock_risk_tags = {}
    
    def step1_valuation_filter(self, max_pe: float = 15, max_pb: float = 1.5,
                               min_dividend_yield: float = 3.0) -> pd.DataFrame:
        """
        初阶筛选：估值安全边际
        
        保守型标准：
        - PE < 15倍
        - PB < 1.5倍
        - 股息率 > 3%
        """
        print("=" * 70)
        print("初阶筛选：估值安全边际")
        print("=" * 70)
        print(f"筛选条件: PE < {max_pe}, PB < {max_pb}, 股息率 > {min_dividend_yield}%")
        print()
        
        result = self.valuation.preliminary_filter(
            max_pe=max_pe,
            max_pb=max_pb,
            min_dividend_yield=min_dividend_yield
        )
        
        return result
    
    def step2_quality_filter(self, df: pd.DataFrame) -> List[str]:
        """
        精阶筛选：盈利能力与财务健康度
        
        标准：
        - ROE连续三年 > 12%
        - 经营现金流/净利润 > 60%
        - 资产负债率 < 60%
        """
        print()
        print("=" * 70)
        print("精阶筛选：盈利能力与财务健康度")
        print("=" * 70)
        print("筛选条件: ROE≥12%, 现金流健康, 负债率<60%")
        print()
        
        qualified_stocks = []
        
        for idx, row in df.iterrows():
            ts_code = row['ts_code']
            name = row.get('name', '')
            
            try:
                # 综合质量检查
                quality_result = self.quality.comprehensive_quality_check(ts_code)
                
                if quality_result['pass']:
                    qualified_stocks.append({
                        'ts_code': ts_code,
                        'name': name,
                        'quality_score': quality_result['quality_score'],
                        'roe': quality_result['roe']['avg_roe'],
                        'debt_ratio': quality_result['risk']['debt_ratio']
                    })
            except:
                continue
        
        print(f"精阶筛选后: {len(qualified_stocks)}只")
        
        # 按质量评分排序
        qualified_stocks = sorted(qualified_stocks, key=lambda x: x['quality_score'], reverse=True)
        
        return [s['ts_code'] for s in qualified_stocks]
    
    def step3_growth_filter(self, stock_list: List[str]) -> List[str]:
        """
        高阶筛选：成长性验证与错杀时机判断
        
        标准：
        - 近三年净利润复合增长率 > 5%
        - 识别错杀信号
        """
        print()
        print("=" * 70)
        print("高阶筛选：成长性验证与错杀时机判断")
        print("=" * 70)
        print("筛选条件: 增长稳健 或 明显错杀")
        print()
        
        qualified_stocks = []
        
        for ts_code in stock_list[:100]:  # 限制数量
            try:
                # 成长性分析
                growth_result = self.growth.comprehensive_growth_analysis(ts_code)
                
                # 条件1：成长评分达标
                growth_ok = growth_result['pass']
                
                # 条件2：有明显错杀信号
                mispriced = growth_result['mispricing']['is_mispriced']
                
                if growth_ok or mispriced:
                    qualified_stocks.append(ts_code)
            except:
                continue
        
        print(f"高阶筛选后: {len(qualified_stocks)}只")
        
        return qualified_stocks
    
    def step4_comprehensive_scoring(self, stock_list: List[str]) -> pd.DataFrame:
        """
        多因子综合评分（含风险标签）
        """
        print()
        print("=" * 70)
        print("多因子综合评分")
        print("=" * 70)
        print()
        
        results = []
        
        for ts_code in stock_list[:50]:  # 限制数量避免超时
            try:
                # 计算综合评分
                score_result = self.scorer.calculate_total_score(ts_code)
                
                # 获取基本信息
                df_basic = self.pro.stock_basic(ts_code=ts_code)
                if df_basic is not None and len(df_basic) > 0:
                    name = df_basic.iloc[0]['name']
                    industry = df_basic.iloc[0]['industry']
                else:
                    name = ''
                    industry = ''
                
                # 风险标签分析
                # 1. 价格数据风险
                price_df = None
                try:
                    price_df = self.pro.daily(ts_code=ts_code, limit=60)
                    if price_df is not None and not price_df.empty:
                        price_df, price_issues = self.data_processor.process_stock_data(price_df, ts_code)
                except:
                    price_issues = ['数据获取失败']
                
                # 2. 财务风险（使用quality_filter的结果）
                financial_issues = []
                quality_result = score_result.get('quality', {})
                if quality_result.get('roe', {}).get('avg_roe', 0) < 5:
                    financial_issues.append('盈利波动大')
                
                # 3. 综合风险标签
                all_issues = price_issues if 'price_issues' in dir() else []
                all_issues.extend(financial_issues)
                
                risk_tags = merge_issues_to_tags(all_issues)
                self.stock_risk_tags[ts_code] = risk_tags
                
                results.append({
                    'ts_code': ts_code,
                    'name': name,
                    'industry': industry,
                    'total_score': score_result['total_score'],
                    'level': score_result['level'],
                    'valuation_score': score_result['valuation']['score'],
                    'quality_score': score_result['quality']['score'],
                    'financial_score': score_result['financial']['score'],
                    'growth_score': score_result['growth']['score'],
                    'pe': score_result['valuation'].get('pe', 0),
                    'pb': score_result['valuation'].get('pb', 0),
                    'dv_ratio': score_result['valuation'].get('dv_ratio', 0),
                    'roe': score_result['quality'].get('roe', {}).get('avg_roe', 0),
                    'suggestion': score_result['suggestion'],
                    'risk_tags': risk_tags
                })
            except:
                continue
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        print(f"评分完成，共 {len(df)} 只股票")
        
        return df
    
    def select_stocks(self, max_pe: float = 15, max_pb: float = 1.5,
                     min_dividend_yield: float = 3.0, top_n: int = 30) -> Dict:
        """
        执行完整选股流程
        
        Args:
            max_pe: 最大PE
            max_pb: 最大PB
            min_dividend_yield: 最小股息率
            top_n: 最终选出股票数量
            
        Returns:
            Dict: 选股结果
        """
        start_time = datetime.now()
        
        print()
        print("=" * 80)
        print("A股价值抄底选股策略")
        print("=" * 80)
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"参数: PE<{max_pe}, PB<{max_pb}, 股息率>{min_dividend_yield}%")
        print("=" * 80)
        print()
        print("策略理念: 区分'价格低估'与'价值陷阱'")
        print("          寻找'好公司遭遇坏价格'的投资机会")
        print()
        
        # 1. 初阶筛选
        df_valuation = self.step1_valuation_filter(max_pe, max_pb, min_dividend_yield)
        
        if len(df_valuation) == 0:
            print("\n警告：初阶筛选无结果，请放宽条件")
            return {'selected_stocks': pd.DataFrame()}
        
        # 2. 精阶筛选
        quality_list = self.step2_quality_filter(df_valuation)
        
        if len(quality_list) == 0:
            print("\n警告：精阶筛选无结果，放宽条件重试...")
            quality_list = df_valuation['ts_code'].tolist()[:50]
        
        # 3. 高阶筛选
        growth_list = self.step3_growth_filter(quality_list)
        
        if len(growth_list) == 0:
            print("\n警告：高阶筛选无结果，使用精阶结果")
            growth_list = quality_list[:30]
        
        # 4. 综合评分
        ranked_df = self.step4_comprehensive_scoring(growth_list)
        
        # 5. 输出结果
        if len(ranked_df) > 0:
            print()
            print("=" * 70)
            print("选股结果分级")
            print("=" * 70)
            
            # 核心池
            core_pool = ranked_df[ranked_df['level'] == '核心池']
            if len(core_pool) > 0:
                print(f"\n【核心池】{len(core_pool)}只 (评分≥80)")
                print("  建议: 优先配置，深度研究后可集中持仓")
                display_cols = ['ts_code', 'name', 'industry', 'total_score', 'pe', 'pb', 'dv_ratio', 'risk_tags']
                available_cols = [c for c in display_cols if c in core_pool.columns]
                print(core_pool[available_cols].to_string(index=False))
            
            # 观察池
            watch_pool = ranked_df[ranked_df['level'] == '观察池']
            if len(watch_pool) > 0:
                print(f"\n【观察池】{len(watch_pool)}只 (评分60-80)")
                print("  建议: 持续跟踪，待瑕疵改善后介入")
            
            # 备选池
            backup_pool = ranked_df[ranked_df['level'] == '备选池']
            if len(backup_pool) > 0:
                print(f"\n【备选池】{len(backup_pool)}只 (评分40-60)")
                print("  建议: 关注特定催化因素")
        
        # 6. 完成
        print()
        print("=" * 80)
        print(f"选股完成！耗时: {(datetime.now() - start_time).total_seconds():.1f} 秒")
        print("=" * 80)
        
        return {
            'selected_stocks': ranked_df.head(top_n),
            'core_pool': ranked_df[ranked_df['level'] == '核心池'],
            'watch_pool': ranked_df[ranked_df['level'] == '观察池'],
            'backup_pool': ranked_df[ranked_df['level'] == '备选池']
        }


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
    selector = ValueSelector(pro)
    
    # 执行选股
    result = selector.select_stocks(max_pe=15, max_pb=1.5, min_dividend_yield=3.0, top_n=30)
    
    print("\n【最终选股结果】")
    if len(result['selected_stocks']) > 0:
        print(result['selected_stocks'].to_string(index=False))
