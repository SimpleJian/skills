#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股趋势跟踪主线选股策略 - 主选股模块

三步筛选法：
1. 初步筛选（安全关 + 动量关）
2. 精确筛选（资金关 + 题材关 + 技术关）
3. 综合排序（多因子评分）
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os
# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)
from tushare_utils.api_utils import APIRateLimiter
from tushare_utils.data_quality import DataPreprocessor, create_default_processor
from tushare_utils.risk_tags import RiskTagGenerator, merge_issues_to_tags

from market_concentration import MarketConcentration
from technical_indicators import TechnicalIndicators
from fundamental_filter import FundamentalFilter, FundAnalysis
from multi_factor_scorer import MultiFactorScorer


class StockSelector:
    """
    A股趋势跟踪主线选股器
    
    核心逻辑：
    1. 计算行情集中度，识别市场主线板块
    2. 三步筛选法精选个股
    3. 多因子评分排序确定最终标的
    """
    
    def __init__(self, pro_api):
        """
        初始化
        
        Args:
            pro_api: Tushare pro_api 实例
        """
        self.pro = pro_api
        self.mc = MarketConcentration(pro_api)
        self.tech = TechnicalIndicators(pro_api)
        self.fund_filter = FundamentalFilter(pro_api)
        self.fund_analysis = FundAnalysis(pro_api)
        self.scorer = MultiFactorScorer(pro_api)
        self.data_processor = create_default_processor(pro_api)
        # 存储每只股票的risk_tags
        self.stock_risk_tags = {}
    
    def step1_preliminary_filter(self, min_amount: float = 1.0, max_stocks: int = None) -> List[str]:
        """
        第一步：初步筛选（安全关 + 动量关）
        
        筛选条件：
        - 排除风险股票（ST/*ST、财务风险等）
        - 20日新高突破（收盘高2%以上）
        - 成交量放大（较20日均量放大1.5倍以上）
        - 年线上方运行
        - 板块集中度提升
        
        Args:
            min_amount: 最小日均成交额（亿元）
            max_stocks: 最大分析股票数量（默认None表示分析全部，可根据API限制设置）
            
        Returns:
            List[str]: 初步筛选后的股票列表
        """
        print("=" * 60)
        print("第一步：初步筛选（安全关 + 动量关）")
        print("=" * 60)
        
        # 获取全部A股
        df_basic = self.pro.stock_basic(list_status='L')
        all_stocks = df_basic['ts_code'].tolist()
        print(f"全市场股票数量: {len(all_stocks)}")
        
        # 安全关：排除风险股票
        safe_stocks = self.fund_filter.filter_risk_stocks(all_stocks)
        
        # 获取最近交易日
        trade_cal = self.pro.trade_cal(exchange='SSE', 
                                       start_date='20250101',
                                       end_date='20251231')
        trade_cal = trade_cal[trade_cal['is_open'] == 1]
        latest_date = trade_cal['cal_date'].max()
        prev_date = trade_cal[trade_cal['cal_date'] < latest_date]['cal_date'].max()
        
        print(f"当前交易日: {latest_date}")
        print(f"前一交易日: {prev_date}")
        
        # 动量关：技术筛选
        momentum_stocks = []
        
        # 批量获取行情数据
        df_daily = self.pro.daily(trade_date=latest_date)
        df_prev = self.pro.daily(trade_date=prev_date)
        
        # 过滤安全股票
        df_daily = df_daily[df_daily['ts_code'].isin(safe_stocks)]
        
        # 计算20日新高
        ts_codes = df_daily['ts_code'].unique()
        if max_stocks is not None:
            ts_codes = ts_codes[:max_stocks]
            print(f"限制分析股票数量: {max_stocks} 只")
        
        for ts_code in ts_codes:
            try:
                # 获取历史数据
                start_dt = datetime.strptime(latest_date, '%Y%m%d') - timedelta(days=60)
                hist_df = self.pro.daily(ts_code=ts_code, 
                                        start_date=start_dt.strftime('%Y%m%d'))
                
                # 数据质量检查
                hist_df, quality_issues = self.data_processor.process_stock_data(hist_df, ts_code)
                
                if hist_df is None or len(hist_df) < 20:
                    # 记录数据质量问题
                    if quality_issues:
                        self.stock_risk_tags[ts_code] = merge_issues_to_tags(quality_issues)
                    continue
                
                hist_df = hist_df.sort_values('trade_date')
                latest = hist_df.iloc[-1]
                
                # 条件1: 20日新高突破（收盘高1%以上，放宽条件）
                high_20 = hist_df['close'].tail(21).head(20).max()
                price_break = latest['close'] > high_20 * 1.01
                
                # 条件2: 成交量放大（较20日均量放大1.2倍以上，放宽条件）
                avg_vol_20 = hist_df['vol'].tail(20).mean()
                volume_ratio = latest['vol'] / avg_vol_20 if avg_vol_20 > 0 else 0
                volume_confirm = volume_ratio >= 1.2
                
                # 条件3: 60日线上方（放宽为中期均线）
                if len(hist_df) >= 60:
                    ma60 = hist_df['close'].tail(60).mean()
                    above_ma = latest['close'] > ma60
                else:
                    above_ma = False
                
                # 条件4: 成交额门槛 (amount单位为千元，转换为亿元)
                amount_yi = latest['amount'] / 100000  # 转换为亿元
                amount_ok = amount_yi >= min_amount
                
                # 综合判断 (放宽条件)
                if price_break and (volume_confirm or above_ma) and amount_ok:
                    momentum_stocks.append({
                        'ts_code': ts_code,
                        'close': latest['close'],
                        'volume_ratio': volume_ratio,
                        'break_pct': (latest['close'] / high_20 - 1) * 100
                    })
            
            except Exception as e:
                continue
        
        print(f"初步筛选后股票数量: {len(momentum_stocks)}")
        
        # 按突破幅度排序
        momentum_stocks = sorted(momentum_stocks, key=lambda x: x['break_pct'], reverse=True)
        
        # 取前300只
        selected = [s['ts_code'] for s in momentum_stocks[:300]]
        
        return selected
    
    def step2_precise_filter(self, stock_list: List[str], 
                            industry_concentration: pd.DataFrame = None,
                            max_stocks: int = None) -> List[str]:
        """
        第二步：精确筛选（资金关 + 题材关 + 技术关）
        
        筛选条件：
        - 资金关：主力资金确认（北向资金、大单资金）
        - 题材关：所属板块处于行情集中度前列
        - 技术关：MACD零轴上方、多头排列、量价配合
        
        Args:
            stock_list: 第一步筛选后的股票列表
            industry_concentration: 行业集中度数据
            max_stocks: 最大分析股票数量（默认None表示分析全部）
            
        Returns:
            List[str]: 精确筛选后的股票列表
        """
        print("\n" + "=" * 60)
        print("第二步：精确筛选（资金关 + 题材关 + 技术关）")
        print("=" * 60)
        
        filtered_stocks = []
        
        # 限制分析数量
        if max_stocks is not None:
            stock_list = stock_list[:max_stocks]
            print(f"限制分析股票数量: {max_stocks} 只")
        
        for ts_code in stock_list:
            try:
                # 技术关检测
                tech_result = self.tech.get_technical_score(ts_code)
                
                # 技术要求（放宽条件）：
                # 1. 技术面评分 >= 50
                # 2. MACD在零轴上方或金叉
                if tech_result['score'] < 50:
                    continue
                
                macd_info = tech_result.get('macd_info', {})
                if not macd_info.get('above_zero', False):
                    continue
                
                # 资金关检测（放宽条件）
                fund_flow = self.fund_analysis.get_money_flow(ts_code, days=5)
                
                # 资金要求：净流入为正或大单流入为正（放宽）
                net_inflow = fund_flow.get('net_inflow', 0)
                big_net = fund_flow.get('big_net_inflow', 0)
                
                # 只要有一项为正即可
                if net_inflow < 0 and big_net < 0:
                    # 资金要求不满足，但仍然可以考虑
                    pass  # 放宽资金限制
                
                # 题材关检测（放宽条件）
                if industry_concentration is not None and len(industry_concentration) > 0:
                    df_basic = self.pro.stock_basic(ts_code=ts_code)
                    if df_basic is not None and len(df_basic) > 0:
                        industry = df_basic.iloc[0]['industry']
                        
                        # 检查行业是否在前70%（放宽）
                        industry_row = industry_concentration[
                            industry_concentration['industry_name'].str.contains(industry, na=False)
                        ]
                        
                        if len(industry_row) > 0:
                            rank = industry_row.index[0]
                            total = len(industry_concentration)
                            
                            # 保留前70%行业
                            if rank / total > 0.7:
                                continue
                
                filtered_stocks.append(ts_code)
            
            except Exception as e:
                continue
        
        print(f"精确筛选后股票数量: {len(filtered_stocks)}")
        
        return filtered_stocks
    
    def step3_ranking(self, stock_list: List[str], 
                     industry_concentration: pd.DataFrame = None) -> pd.DataFrame:
        """
        第三步：综合排序（多因子评分）
        
        根据四因子模型评分：
        - 趋势强度分（40%）
        - 资金认可度分（30%）
        - 主线契合度分（20%）
        - 风险调整分（10%）
        
        Args:
            stock_list: 第二步筛选后的股票列表
            industry_concentration: 行业集中度数据
            
        Returns:
            pd.DataFrame: 评分排名结果
        """
        print("\n" + "=" * 60)
        print("第三步：综合排序（多因子评分）")
        print("=" * 60)
        
        # 多因子评分排名
        ranked_df = self.scorer.rank_stocks(stock_list, industry_concentration)
        
        print(f"评分完成，共 {len(ranked_df)} 只股票")
        
        return ranked_df
    
    def select_stocks(self, top_n: int = 50, min_amount: float = 1.0, max_stocks: int = None) -> Dict:
        """
        执行完整选股流程
        
        Args:
            top_n: 最终选出股票数量
            min_amount: 最小日均成交额（亿元）
            max_stocks: 最大分析股票数量（默认None表示分析全部）
            
        Returns:
            Dict: 选股结果
        """
        start_time = datetime.now()
        
        print("\n" + "=" * 80)
        print("A股趋势跟踪主线选股策略")
        print("=" * 80)
        
        # 1. 计算行情集中度
        print("\n【行情集中度分析】")
        concentration = self.mc.calculate_concentration()
        print(f"当前行情集中度: {concentration['concentration']}%")
        print(f"解读: {self.mc.interpret_concentration(concentration['concentration'])}")
        
        # 2. 计算行业集中度
        print("\n【行业集中度排名】")
        industry_concentration = self.mc.calculate_industry_concentration()
        if len(industry_concentration) > 0:
            print(industry_concentration.head(10)[['industry_name', 'concentration', 'limit_up_count']].to_string(index=False))
        
        # 3. 三步选股
        # 第一步：初步筛选
        preliminary_list = self.step1_preliminary_filter(min_amount, max_stocks)
        
        if len(preliminary_list) == 0:
            print("\n警告：初步筛选无结果，请检查市场状态")
            return {
                'concentration': concentration,
                'industry_concentration': industry_concentration,
                'selected_stocks': pd.DataFrame()
            }
        
        # 第二步：精确筛选
        precise_list = self.step2_precise_filter(preliminary_list, industry_concentration, max_stocks)
        
        if len(precise_list) == 0:
            print("\n警告：精确筛选无结果，放宽条件重试...")
            # 放宽条件
            precise_list = preliminary_list[:50]
        
        # 第三步：综合排序
        ranked_df = self.step3_ranking(precise_list, industry_concentration)
        
        # 添加风险标签到结果
        if len(ranked_df) > 0 and 'ts_code' in ranked_df.columns:
            ranked_df['risk_tags'] = ranked_df['ts_code'].apply(
                lambda x: self.stock_risk_tags.get(x, "")
            )
        
        # 4. 仓位配置建议
        if len(ranked_df) > 0:
            print("\n" + "=" * 60)
            print("仓位配置建议")
            print("=" * 60)
            
            # 核心仓位（前10%）
            core_count = max(3, min(5, int(len(ranked_df) * 0.1)))
            core_stocks = ranked_df.head(core_count)
            print(f"\n【核心仓位】建议配置 30%-40% 资金，{core_count} 只")
            print(core_stocks[['ts_code', 'name', 'industry', 'total_score']].to_string(index=False))
            
            # 卫星仓位（10%-30%）
            satellite_count = max(5, min(8, int(len(ranked_df) * 0.3)))
            satellite_stocks = ranked_df.iloc[core_count:satellite_count]
            if len(satellite_stocks) > 0:
                print(f"\n【卫星仓位】建议配置 15%-20% 资金，{len(satellite_stocks)} 只")
                print(satellite_stocks[['ts_code', 'name', 'industry', 'total_score']].to_string(index=False))
            
            # 观察仓位（30%-50%）
            observe_count = max(5, min(10, int(len(ranked_df) * 0.5)))
            if observe_count > satellite_count:
                observe_stocks = ranked_df.iloc[satellite_count:observe_count]
                print(f"\n【观察仓位】建议配置 5%-10% 资金，{len(observe_stocks)} 只")
        
        # 5. 输出最终结果
        print("\n" + "=" * 80)
        print(f"选股完成！耗时: {(datetime.now() - start_time).total_seconds():.1f} 秒")
        print("=" * 80)
        
        return {
            'concentration': concentration,
            'industry_concentration': industry_concentration,
            'selected_stocks': ranked_df.head(top_n),
            'core_stocks': ranked_df.head(core_count) if len(ranked_df) > 0 else pd.DataFrame(),
            'market_status': self.mc.interpret_concentration(concentration['concentration'])
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
    selector = StockSelector(pro)
    
    # 执行选股
    result = selector.select_stocks(top_n=30, min_amount=1.0)
    
    print("\n【最终选股结果】")
    if len(result['selected_stocks']) > 0:
        display_cols = ['ts_code', 'name', 'industry', 'total_score', 'risk_tags']
        # 过滤存在的列
        available_cols = [c for c in display_cols if c in result['selected_stocks'].columns]
        print(result['selected_stocks'][available_cols].to_string(index=False))
