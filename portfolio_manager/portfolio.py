#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合管理模块

基于现代投资组合理论的组合分析与管理系统。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
import sys
import os

# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter, retry_on_rate_limit


class PortfolioManager:
    """组合管理器"""
    
    def __init__(self, pro_api):
        """
        初始化
        
        Args:
            pro_api: Tushare pro_api 实例
        """
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def load_portfolio(self, filepath: str) -> Dict:
        """
        从文件加载组合
        
        Args:
            filepath: 组合文件路径
        
        Returns:
            组合字典
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # 获取最新价格
        for holding in data['holdings']:
            latest_price = self._get_latest_price(holding['ts_code'])
            holding['current_price'] = latest_price
            holding['market_value'] = holding['quantity'] * latest_price
        
        # 计算总市值
        total_market_value = sum(h['market_value'] for h in data['holdings'])
        data['total_market_value'] = total_market_value + data.get('cash', 0)
        
        # 计算权重
        for holding in data['holdings']:
            holding['weight'] = holding['market_value'] / data['total_market_value']
        
        return data
    
    def _get_latest_price(self, ts_code: str) -> float:
        """获取最新价格"""
        try:
            @self.limiter.rate_limit
            def fetch():
                df = self.pro.daily(ts_code=ts_code, limit=1)
                if df is not None and not df.empty:
                    return float(df.iloc[0]['close'])
                return 0.0
            return fetch()
        except:
            return 0.0
    
    def analyze_portfolio(self, portfolio: Dict) -> Dict:
        """
        分析组合
        
        Args:
            portfolio: 组合字典
        
        Returns:
            分析结果
        """
        results = {}
        
        # 1. 基础信息
        results['summary'] = self._analyze_summary(portfolio)
        
        # 2. 收益分析
        results['returns'] = self._analyze_returns(portfolio)
        
        # 3. 风险分析
        results['risk'] = self._analyze_risk(portfolio)
        
        # 4. 行业分布
        results['sector'] = self._analyze_sector(portfolio)
        
        # 5. 相关性分析
        results['correlation'] = self._analyze_correlation(portfolio)
        
        return results
    
    def _analyze_summary(self, portfolio: Dict) -> Dict:
        """分析组合概况"""
        total_cost = sum(h['quantity'] * h['cost'] for h in portfolio['holdings'])
        total_market = sum(h['market_value'] for h in portfolio['holdings'])
        cash = portfolio.get('cash', 0)
        total_capital = portfolio.get('total_capital', total_cost + cash)
        
        total_pnl = total_market - total_cost
        total_return = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'total_capital': total_capital,
            'total_market_value': total_market + cash,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'cash': cash,
            'cash_ratio': cash / (total_market + cash) * 100,
            'holding_count': len(portfolio['holdings'])
        }
    
    def _analyze_returns(self, portfolio: Dict) -> Dict:
        """分析收益"""
        # 获取历史价格计算收益率
        returns_data = []
        
        for holding in portfolio['holdings']:
            try:
                @self.limiter.rate_limit
                def fetch():
                    return self.pro.daily(ts_code=holding['ts_code'], limit=252)
                
                df = fetch()
                if df is not None and not df.empty:
                    df = df.sort_values('trade_date')
                    df['return'] = df['close'].pct_change()
                    returns_data.append(df[['trade_date', 'return']].set_index('trade_date'))
            except:
                continue
        
        if not returns_data:
            return {'error': '无法获取历史数据'}
        
        # 合并计算组合收益率
        returns_df = pd.concat(returns_data, axis=1).dropna()
        weights = [h['weight'] for h in portfolio['holdings']]
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        # 计算指标
        total_return = (portfolio_returns + 1).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe = annual_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return * 100,
            'annual_return': annual_return * 100,
            'volatility': volatility * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown * 100
        }
    
    def _analyze_risk(self, portfolio: Dict) -> Dict:
        """分析风险"""
        # 计算VaR
        # 简化处理，使用正态分布假设
        var_95 = -1.645 * 0.16  # 假设16%年化波动
        var_99 = -2.326 * 0.16
        
        # 集中度风险
        weights = [h['weight'] for h in portfolio['holdings']]
        herfindahl = sum(w**2 for w in weights)
        
        return {
            'var_95': var_95 * 100,
            'var_99': var_99 * 100,
            'concentration_index': herfindahl * 100,
            'concentration_level': '高' if herfindahl > 0.15 else '中' if herfindahl > 0.1 else '低'
        }
    
    def _analyze_sector(self, portfolio: Dict) -> Dict:
        """分析行业分布"""
        sector_map = {}
        
        for holding in portfolio['holdings']:
            try:
                @self.limiter.rate_limit
                def fetch():
                    return self.pro.stock_basic(ts_code=holding['ts_code'])
                
                df = fetch()
                if df is not None and not df.empty:
                    industry = df.iloc[0].get('industry', '未知')
                    sector_map[industry] = sector_map.get(industry, 0) + holding['market_value']
            except:
                continue
        
        total = sum(sector_map.values())
        sector_pct = {k: v/total*100 for k, v in sector_map.items()}
        
        # 检查集中度
        max_sector = max(sector_pct.items(), key=lambda x: x[1]) if sector_pct else ('无', 0)
        
        return {
            'sector_weights': sector_pct,
            'max_sector': max_sector[0],
            'max_sector_weight': max_sector[1],
            'concentration_risk': max_sector[1] > 30
        }
    
    def _analyze_correlation(self, portfolio: Dict) -> Dict:
        """分析相关性"""
        # 简化处理
        price_data = {}
        
        for holding in portfolio['holdings'][:10]:  # 限制数量
            try:
                @self.limiter.rate_limit
                def fetch():
                    return self.pro.daily(ts_code=holding['ts_code'], limit=60)
                
                df = fetch()
                if df is not None and not df.empty:
                    price_data[holding['ts_code']] = df.set_index('trade_date')['close']
            except:
                continue
        
        if len(price_data) < 2:
            return {'high_corr_pairs': []}
        
        # 计算相关性
        prices_df = pd.DataFrame(price_data)
        returns_df = prices_df.pct_change().dropna()
        corr_matrix = returns_df.corr()
        
        # 找出高相关性组合
        high_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if corr_val > 0.8:
                    high_corr.append({
                        'code1': corr_matrix.columns[i],
                        'code2': corr_matrix.columns[j],
                        'correlation': corr_val
                    })
        
        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'high_corr_pairs': high_corr
        }
    
    def get_rebalance_suggestion(self, portfolio: Dict, target_weights: Dict = None) -> Dict:
        """
        获取再平衡建议
        
        Args:
            portfolio: 当前组合
            target_weights: 目标权重，默认等权
        
        Returns:
            再平衡建议
        """
        if target_weights is None:
            # 默认等权
            n = len(portfolio['holdings'])
            target_weights = {h['ts_code']: 100/n for h in portfolio['holdings']}
        
        suggestions = []
        total_value = portfolio['total_market_value']
        
        for holding in portfolio['holdings']:
            code = holding['ts_code']
            current_weight = holding['weight'] * 100
            target_weight = target_weights.get(code, 0)
            
            deviation = current_weight - target_weight
            
            if abs(deviation) > 5:  # 偏离超过5%
                action = '减仓' if deviation > 0 else '加仓'
                amount = abs(deviation) / 100 * total_value
                
                suggestions.append({
                    'code': code,
                    'name': holding['name'],
                    'action': action,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'deviation': deviation,
                    'amount': amount
                })
        
        # 按偏离度排序
        suggestions.sort(key=lambda x: abs(x['deviation']), reverse=True)
        
        return {
            'suggestions': suggestions,
            'needs_rebalance': len(suggestions) > 0
        }
    
    def print_report(self, analysis: Dict):
        """打印报告"""
        print("=" * 80)
        print("组合分析报告")
        print("=" * 80)
        print(f"报告时间: {datetime.now().strftime('%Y-%m-%d')}")
        print()
        
        # 概况
        summary = analysis.get('summary', {})
        print("【组合概况】")
        print(f"初始本金: {summary.get('total_capital', 0)/10000:.1f}万")
        print(f"当前市值: {summary.get('total_market_value', 0)/10000:.1f}万")
        print(f"累计盈亏: {summary.get('total_pnl', 0)/10000:+.1f}万 ({summary.get('total_return', 0):+.2f}%)")
        print(f"现金比例: {summary.get('cash_ratio', 0):.1f}%")
        print()
        
        # 收益
        returns = analysis.get('returns', {})
        if 'error' not in returns:
            print("【收益指标】")
            print(f"总收益率: {returns.get('total_return', 0):.2f}%")
            print(f"年化收益: {returns.get('annual_return', 0):.2f}%")
            print(f"年化波动: {returns.get('volatility', 0):.2f}%")
            print(f"夏普比率: {returns.get('sharpe_ratio', 0):.2f}")
            print(f"最大回撤: {returns.get('max_drawdown', 0):.2f}%")
            print()
        
        # 行业
        sector = analysis.get('sector', {})
        print("【行业分布】")
        for sector_name, weight in sorted(sector.get('sector_weights', {}).items(), key=lambda x: -x[1]):
            warning = " ⚠️" if weight > 30 else ""
            print(f"  {sector_name}: {weight:.1f}%{warning}")
        print()
        
        # 相关性
        corr = analysis.get('correlation', {})
        high_corr = corr.get('high_corr_pairs', [])
        if high_corr:
            print("【相关性警告】")
            for pair in high_corr:
                print(f"  {pair['code1']} ↔ {pair['code2']}: {pair['correlation']:.2f} ⚠️")
            print()
        
        print("=" * 80)


if __name__ == '__main__':
    # 示例用法
    print("组合管理模块")
    print("使用方法: python run.py --portfolio portfolio.json")
