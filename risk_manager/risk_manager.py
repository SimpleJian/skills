#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理模块

提供止损追踪、回撤监控、风险预算等功能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import sys
import os

_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter


class RiskManager:
    """风险管理器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
    
    def scan_portfolio_risk(self, holdings: List[Dict]) -> Dict:
        """
        扫描组合风险
        
        Args:
            holdings: 持仓列表 [{ts_code, quantity, cost}]
        
        Returns:
            风险扫描结果
        """
        warnings = []
        alerts = []
        
        for holding in holdings:
            code = holding['ts_code']
            quantity = holding['quantity']
            cost_price = holding['cost']
            
            # 获取最新价格
            latest_price = self._get_latest_price(code)
            if latest_price == 0:
                continue
            
            market_value = quantity * latest_price
            cost_value = quantity * cost_price
            pnl_pct = (latest_price - cost_price) / cost_price * 100
            
            # 止损检查
            stop_loss_levels = {
                'tight': -5,      # -5% 严格止损
                'normal': -8,     # -8% 常规止损
                'loose': -12      # -12% 宽松止损
            }
            
            stop_loss_triggered = False
            for level, threshold in stop_loss_levels.items():
                if pnl_pct <= threshold:
                    alerts.append({
                        'code': code,
                        'level': 'danger',
                        'message': f'跌破{level}止损线 ({pnl_pct:.1f}%)',
                        'action': '建议立即止损'
                    })
                    stop_loss_triggered = True
                    break
            
            if not stop_loss_triggered and pnl_pct <= -3:
                warnings.append({
                    'code': code,
                    'level': 'warning',
                    'message': f'接近止损线 ({pnl_pct:.1f}%)',
                    'action': '密切关注'
                })
            
            # 单一仓位风险
            # 简化处理，假设总市值已知
            # 实际应该传入total_value
        
        return {
            'alerts': alerts,
            'warnings': warnings,
            'alert_count': len(alerts),
            'warning_count': len(warnings)
        }
    
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
    
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算VaR (Value at Risk)
        
        Args:
            returns: 收益率序列
            confidence: 置信度
        
        Returns:
            VaR值
        """
        return np.percentile(returns, (1 - confidence) * 100)
    
    def calculate_expected_shortfall(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算ES (Expected Shortfall)
        
        Args:
            returns: 收益率序列
            confidence: 置信度
        
        Returns:
            ES值
        """
        var = self.calculate_var(returns, confidence)
        return returns[returns <= var].mean()
    
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        凯利公式计算最优仓位
        
        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损
        
        Returns:
            最优仓位比例
        """
        if avg_loss == 0:
            return 0
        
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
        return max(0, min(kelly, 1))  # 限制在0-1之间
    
    def print_risk_report(self, risk_result: Dict):
        """打印风险报告"""
        print("=" * 80)
        print("风险扫描报告")
        print("=" * 80)
        print(f"报告时间: {datetime.now().strftime('%Y-%m-%d')}")
        print()
        
        alerts = risk_result.get('alerts', [])
        warnings = risk_result.get('warnings', [])
        
        if alerts:
            print(f"🔴 紧急警报 ({len(alerts)}):")
            for alert in alerts:
                print(f"  {alert['code']}: {alert['message']}")
                print(f"    → {alert['action']}")
            print()
        
        if warnings:
            print(f"🟡 风险提示 ({len(warnings)}):")
            for warning in warnings:
                print(f"  {warning['code']}: {warning['message']}")
            print()
        
        if not alerts and not warnings:
            print("✓ 当前无重大风险")
        
        print("=" * 80)


if __name__ == '__main__':
    print("风险管理模块")
