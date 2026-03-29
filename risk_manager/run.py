#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理运行入口
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import tushare as ts
from risk_manager.risk_manager import RiskManager


def main():
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("请设置 TUSHARE_TOKEN 环境变量")
        sys.exit(1)
    
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 示例持仓
    holdings = [
        {'ts_code': '000001.SZ', 'quantity': 1000, 'cost': 10.5},
        {'ts_code': '600519.SH', 'quantity': 100, 'cost': 1680.0},
    ]
    
    manager = RiskManager(pro)
    result = manager.scan_portfolio_risk(holdings)
    manager.print_risk_report(result)


if __name__ == '__main__':
    main()
