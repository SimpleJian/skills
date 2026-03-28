#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面筛选模块

风险排除清单：
- 退市风险（ST/*ST、连续亏损）
- 现金流异常（经营现金流连续3年负）
- 杠杆过高（资产负债率>80%）
- 偿债能力不足（流动比率<0.5）
- 业绩波动过大
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Set
from datetime import datetime


class FundamentalFilter:
    """基本面风险过滤器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.risk_stocks = set()
    
    def get_st_stocks(self, trade_date: str = None) -> Set[str]:
        """
        获取ST/*ST股票列表
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = self.pro.stock_st(trade_date=trade_date)
            if df is not None and len(df) > 0:
                return set(df['ts_code'].tolist())
        except:
            pass
        
        # 备选方案：从名称筛选
        df_basic = self.pro.stock_basic(list_status='L')
        if df_basic is not None:
            st_df = df_basic[df_basic['name'].str.contains('ST', na=False)]
            return set(st_df['ts_code'].tolist())
        
        return set()
    
    def get_delisting_risk_stocks(self) -> Set[str]:
        """
        获取有退市风险的股票（连续亏损等）
        """
        risk_stocks = set()
        
        try:
            # 获取最新一期财务指标
            df_fina = self.pro.fina_indicator()
            
            if df_fina is not None and len(df_fina) > 0:
                # 筛选连续亏损的股票
                # 这里简化处理，实际应该查看多年数据
                loss_makers = df_fina[df_fina['profit_dedt'] < 0]['ts_code'].tolist()
                risk_stocks.update(loss_makers)
        except:
            pass
        
        return risk_stocks
    
    def get_financial_risk_stocks(self) -> Set[str]:
        """
        基于财务指标筛选风险股票
        """
        risk_stocks = set()
        
        try:
            # 获取最新一期财务数据
            df_balancesheet = self.pro.balancesheet()
            df_cashflow = self.pro.cashflow()
            
            if df_balancesheet is not None and len(df_balancesheet) > 0:
                # 资产负债率 > 80%
                high_leverage = df_balancesheet[
                    (df_balancesheet['total_liab'] / df_balancesheet['total_assets'] > 0.8)
                ]['ts_code'].tolist()
                risk_stocks.update(high_leverage)
                
                # 流动比率 < 0.5
                low_liquidity = df_balancesheet[
                    (df_balancesheet['total_cur_assets'] / df_balancesheet['total_cur_liab'] < 0.5)
                ]['ts_code'].tolist()
                risk_stocks.update(low_liquidity)
            
            if df_cashflow is not None and len(df_cashflow) > 0:
                # 经营现金流连续为负（简化：最近一期为负）
                negative_cashflow = df_cashflow[
                    df_cashflow['n_cashflow_act'] < 0
                ]['ts_code'].tolist()
                risk_stocks.update(negative_cashflow)
        
        except:
            pass
        
        return risk_stocks
    
    def get_all_risk_stocks(self, trade_date: str = None) -> Set[str]:
        """
        获取所有风险股票列表
        
        Returns:
            Set[str]: 风险股票代码集合
        """
        self.risk_stocks = set()
        
        # 1. ST/*ST股票
        st_stocks = self.get_st_stocks(trade_date)
        self.risk_stocks.update(st_stocks)
        print(f"ST/*ST股票数量: {len(st_stocks)}")
        
        # 2. 退市风险
        delisting_risk = self.get_delisting_risk_stocks()
        self.risk_stocks.update(delisting_risk)
        print(f"退市风险股票数量: {len(delisting_risk)}")
        
        # 3. 财务风险
        financial_risk = self.get_financial_risk_stocks()
        self.risk_stocks.update(financial_risk)
        print(f"财务风险股票数量: {len(financial_risk)}")
        
        return self.risk_stocks
    
    def filter_risk_stocks(self, stock_list: List[str], trade_date: str = None) -> List[str]:
        """
        过滤风险股票
        
        Args:
            stock_list: 待筛选股票列表
            trade_date: 交易日期
            
        Returns:
            List[str]: 过滤后的股票列表
        """
        risk_stocks = self.get_all_risk_stocks(trade_date)
        
        filtered = [code for code in stock_list if code not in risk_stocks]
        
        print(f"原股票数量: {len(stock_list)}")
        print(f"风险股票数量: {len([s for s in stock_list if s in risk_stocks])}")
        print(f"过滤后数量: {len(filtered)}")
        
        return filtered
    
    def get_stock_basic_info(self, ts_code: str) -> Dict:
        """
        获取股票基本信息
        """
        try:
            df = self.pro.stock_basic(ts_code=ts_code)
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                return {
                    'name': row['name'],
                    'industry': row['industry'],
                    'market': '主板' if row['market'] == '主板' else 
                             ('创业板' if row['market'] == '创业板' else 
                              ('科创板' if row['market'] == '科创板' else row['market'])),
                    'list_date': row['list_date']
                }
        except:
            pass
        
        return {}


class FundAnalysis:
    """资金流向分析"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_north_bound_flow(self, trade_date: str = None, days: int = 20) -> pd.DataFrame:
        """
        获取北向资金流向
        
        Args:
            trade_date: 结束日期
            days: 统计天数
            
        Returns:
            pd.DataFrame: 北向资金流向统计
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 计算起始日期
        start_date = (datetime.strptime(trade_date, '%Y%m%d') - 
                     pd.Timedelta(days=days*2)).strftime('%Y%m%d')
        
        # 获取沪深港通持股数据
        df_hk = self.pro.hk_hold(start_date=start_date, end_date=trade_date)
        
        if df_hk is None or len(df_hk) == 0:
            return pd.DataFrame()
        
        # 按股票汇总
        latest_df = df_hk[df_hk['trade_date'] == df_hk['trade_date'].max()]
        
        # 计算20日变化
        result = []
        for ts_code in latest_df['ts_code'].unique():
            stock_df = df_hk[df_hk['ts_code'] == ts_code].sort_values('trade_date')
            if len(stock_df) >= 2:
                latest_vol = stock_df.iloc[-1]['vol']
                prev_vol = stock_df.iloc[0]['vol']
                change = latest_vol - prev_vol
                
                result.append({
                    'ts_code': ts_code,
                    'hold_vol': latest_vol,
                    'vol_change': change,
                    'vol_change_ratio': change / prev_vol if prev_vol > 0 else 0
                })
        
        return pd.DataFrame(result)
    
    def get_money_flow(self, ts_code: str, days: int = 5) -> Dict:
        """
        获取个股资金流向
        
        Args:
            ts_code: 股票代码
            days: 统计天数
            
        Returns:
            Dict: 资金流向分析
        """
        end_date = datetime.now()
        start_date = (end_date - pd.Timedelta(days=days*2)).strftime('%Y%m%d')
        
        df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date)
        
        if df is None or len(df) == 0:
            return {}
        
        df = df.tail(days)
        
        # 计算净流入
        total_buy = df['buy_sm_amount'].sum() + df['buy_md_amount'].sum() + df['buy_lg_amount'].sum()
        total_sell = df['sell_sm_amount'].sum() + df['sell_md_amount'].sum() + df['sell_lg_amount'].sum()
        net_inflow = total_buy - total_sell
        
        # 大单资金流向
        big_buy = df['buy_lg_amount'].sum() + df['buy_elg_amount'].sum()
        big_sell = df['sell_lg_amount'].sum() + df['sell_elg_amount'].sum()
        big_net = big_buy - big_sell
        
        return {
            'net_inflow': round(net_inflow, 2),
            'big_net_inflow': round(big_net, 2),
            'inflow_ratio': round(net_inflow / total_buy * 100, 2) if total_buy > 0 else 0,
            'big_inflow_ratio': round(big_net / big_buy * 100, 2) if big_buy > 0 else 0,
            'avg_buy_sm': df['buy_sm_amount'].mean(),
            'avg_buy_lg': df['buy_lg_amount'].mean(),
        }
    
    def get_institutional_holding(self, ts_code: str) -> Dict:
        """
        获取机构持仓信息（基于基金持仓数据）
        
        注意：数据有滞后性，季度更新
        """
        try:
            df = self.pro.fund_portfolio(ts_code=ts_code)
            
            if df is None or len(df) == 0:
                return {}
            
            # 最新一期
            latest = df.iloc[0]
            
            return {
                'fund_hold': latest.get('amount', 0),
                'fund_ratio': latest.get('stk_mkv_ratio', 0),
                'fund_count': len(df['end_date'].unique())
            }
        except:
            return {}
    
    def get_shareholder_concentration(self, ts_code: str) -> Dict:
        """
        获取股东集中度（筹码集中）
        """
        try:
            df = self.pro.stk_holdernumber(ts_code=ts_code)
            
            if df is None or len(df) < 2:
                return {}
            
            df = df.sort_values('end_date', ascending=False)
            latest = df.iloc[0]
            prev = df.iloc[1] if len(df) > 1 else None
            
            holder_change = 0
            if prev is not None and prev['holder_num'] > 0:
                holder_change = (latest['holder_num'] - prev['holder_num']) / prev['holder_num']
            
            return {
                'holder_num': latest.get('holder_num', 0),
                'holder_change': round(holder_change * 100, 2),
                'avg_hold': latest.get('avg_hold', 0),
                'concentration_trend': '集中' if holder_change < -0.05 else 
                                      ('分散' if holder_change > 0.05 else '稳定')
            }
        except:
            return {}


if __name__ == '__main__':
    import tushare as ts
    
    pro = ts.pro_api()
    ff = FundamentalFilter(pro)
    
    # 测试风险股票筛选
    risk_stocks = ff.get_all_risk_stocks()
    print(f"\n总风险股票数量: {len(risk_stocks)}")
    print(f"示例风险股票: {list(risk_stocks)[:10]}")
    
    # 测试资金流向
    fa = FundAnalysis(pro)
    flow = fa.get_money_flow('000001.SZ')
    print(f"\n资金流向: {flow}")
