#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面价值筛选模块 - 第二层筛选

核心指标：
- 期限结构：基差、月间价差、展期收益
- 成本与利润：价格-成本比、行业利润
- 库存与供需：库存历史分位数、库存消费比
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta


class FundamentalValue:
    """基本面价值筛选器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
    
    def get_fut_data(self, ts_code: str, days: int = 252) -> pd.DataFrame:
        """获取期货历史数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            df = self.pro.fut_daily(ts_code=ts_code,
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'))
            
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
        except:
            pass
        
        return pd.DataFrame()
    
    def calculate_basis(self, ts_code: str) -> Dict:
        """
        计算基差（现货价格-期货价格）
        
        由于Tushare可能不提供现货数据，这里简化处理
        使用近月合约与主力合约价差作为代理
        """
        try:
            # 获取合约信息
            df_daily = self.get_fut_data(ts_code, days=60)
            
            if len(df_daily) < 20:
                return {'basis_score': 0}
            
            latest = df_daily.iloc[-1]
            
            # 使用期限结构斜率作为基差代理
            # 如果近月价格 > 远月价格，说明现货紧张（Backwardation）
            # 这里简化处理，使用价格相对历史位置
            price = latest['close']
            price_mean = df_daily['close'].mean()
            price_std = df_daily['close'].std()
            
            # 价格处于历史低位，基差可能为正
            price_percentile = (df_daily['close'] < price).sum() / len(df_daily)
            
            # 基差评分（满分30分）
            if price_percentile < 0.1:  # 历史最低10%
                basis_score = 30
                basis_status = '深度贴水/现货升水'
            elif price_percentile < 0.2:  # 历史最低20%
                basis_score = 25
                basis_status = '明显贴水'
            elif price_percentile < 0.3:
                basis_score = 20
                basis_status = '轻度贴水'
            else:
                basis_score = 10
                basis_status = '升水或平水'
            
            return {
                'price': price,
                'price_mean': round(price_mean, 2),
                'price_percentile': round(price_percentile * 100, 1),
                'basis_score': basis_score,
                'basis_status': basis_status
            }
        
        except:
            return {'basis_score': 0}
    
    def calculate_inventory_score(self, ts_code: str) -> Dict:
        """
        计算库存评分
        
        通过价格行为间接反映库存状况
        价格处于历史低位通常对应库存高企或需求疲弱
        """
        try:
            df = self.get_fut_data(ts_code, days=252)
            
            if len(df) < 60:
                return {'inventory_score': 0}
            
            # 价格历史分位数
            current_price = df.iloc[-1]['close']
            price_1y_low = df['close'].min()
            price_1y_high = df['close'].max()
            
            # 价格位置（0=最低，100=最高）
            price_position = (current_price - price_1y_low) / (price_1y_high - price_1y_low) * 100
            
            # 库存推断：价格低位通常库存高（供应过剩）或需求弱
            # 但如果价格低位且开始反弹，可能库存开始去化
            
            # 近期趋势
            recent_return = (df.iloc[-1]['close'] / df.iloc[-20]['close'] - 1) * 100
            
            # 库存评分逻辑（满分25分）
            # 价格极低+开始反弹 = 库存去化中，利好（高分）
            # 价格极低+继续下跌 = 库存累积中，观望（中低分）
            
            if price_position < 10:  # 历史最低10%
                if recent_return > -5:  # 跌势放缓或反弹
                    inventory_score = 25
                    inventory_status = '价格极端低位，库存可能开始去化'
                else:
                    inventory_score = 15
                    inventory_status = '价格极端低位，库存仍高'
            elif price_position < 20:
                if recent_return > -3:
                    inventory_score = 20
                    inventory_status = '价格低位，库存改善中'
                else:
                    inventory_score = 12
                    inventory_status = '价格低位，库存压力仍存'
            elif price_position < 30:
                inventory_score = 10
                inventory_status = '价格偏低'
            else:
                inventory_score = 5
                inventory_status = '价格中等或偏高'
            
            return {
                'price_position': round(price_position, 1),
                'price_1y_low': round(price_1y_low, 2),
                'price_1y_high': round(price_1y_high, 2),
                'recent_return': round(recent_return, 2),
                'inventory_score': inventory_score,
                'inventory_status': inventory_status
            }
        
        except:
            return {'inventory_score': 0}
    
    def calculate_cost_support(self, ts_code: str) -> Dict:
        """
        计算成本支撑评分
        
        通过历史价格分布估算成本支撑
        价格跌破历史75%分位可能触及高成本产能成本线
        """
        try:
            df = self.get_fut_data(ts_code, days=252*3)  # 3年数据
            
            if len(df) < 252:
                return {'cost_score': 0}
            
            current_price = df.iloc[-1]['close']
            
            # 历史分位数
            p10 = df['close'].quantile(0.10)
            p25 = df['close'].quantile(0.25)
            p50 = df['close'].quantile(0.50)
            p75 = df['close'].quantile(0.75)
            
            # 成本支撑评分（满分25分）
            if current_price <= p10:  # 跌破90%分位成本线
                cost_score = 25
                cost_status = '跌破高成本线，强成本支撑'
            elif current_price <= p25:  # 跌破75%分位
                cost_score = 22
                cost_status = '接近高成本线，成本支撑有效'
            elif current_price <= p50:  # 低于历史中位数
                cost_score = 15
                cost_status = '低于平均成本，中等支撑'
            elif current_price <= p75:
                cost_score = 8
                cost_status = '中等成本区间'
            else:
                cost_score = 0
                cost_status = '高成本区间，无成本支撑'
            
            return {
                'current_price': round(current_price, 2),
                'p10': round(p10, 2),
                'p25': round(p25, 2),
                'p50': round(p50, 2),
                'cost_score': cost_score,
                'cost_status': cost_status
            }
        
        except:
            return {'cost_score': 0}
    
    def check_term_structure(self, ts_code: str) -> Dict:
        """
        检查期限结构
        
        通过连续合约价格变化判断期限结构
        """
        try:
            df = self.get_fut_data(ts_code, days=60)
            
            if len(df) < 30:
                return {'term_score': 0}
            
            # 近期价格趋势 vs 远期（用不同时间段代理）
            near_return = (df.iloc[-1]['close'] / df.iloc[-20]['close'] - 1) * 100
            far_return = (df.iloc[-1]['close'] / df.iloc[-40]['close'] - 1) * 100
            
            # 近月跌幅小于远月 = Backwardation结构（现货强）
            # 近月跌幅大于远月 = Contango结构（现货弱）
            
            spread = near_return - far_return
            
            # 期限结构评分（满分20分）
            if spread > 5:  # 近月明显强于远月
                term_score = 20
                term_status = 'Backwardation，现货紧张'
            elif spread > 0:
                term_score = 15
                term_status = '轻度Backwardation'
            elif spread > -5:
                term_score = 10
                term_status = '接近平水'
            else:
                term_score = 5
                term_status = 'Contango，现货宽松'
            
            return {
                'near_return': round(near_return, 2),
                'far_return': round(far_return, 2),
                'spread': round(spread, 2),
                'term_score': term_score,
                'term_status': term_status
            }
        
        except:
            return {'term_score': 0}
    
    def comprehensive_fundamental_check(self, ts_code: str) -> Dict:
        """
        综合基本面价值检查
        """
        basis = self.calculate_basis(ts_code)
        inventory = self.calculate_inventory_score(ts_code)
        cost = self.calculate_cost_support(ts_code)
        term = self.check_term_structure(ts_code)
        
        # 基本面总评分（满分100分）
        total_score = (
            basis.get('basis_score', 0) +
            inventory.get('inventory_score', 0) +
            cost.get('cost_score', 0) +
            term.get('term_score', 0)
        )
        
        return {
            'ts_code': ts_code,
            'fundamental_score': total_score,
            'basis': basis,
            'inventory': inventory,
            'cost': cost,
            'term_structure': term
        }
    
    def filter_fundamental_value(self, df_oversold: pd.DataFrame, min_score: int = 50) -> pd.DataFrame:
        """
        第二层筛选：基本面价值
        """
        print()
        print("=" * 70)
        print("第二层筛选：基本面价值")
        print("=" * 70)
        print(f"筛选条件: 基本面评分≥{min_score}")
        print()
        
        results = []
        
        for idx, row in df_oversold.iterrows():
            ts_code = row.get('ts_code')
            name = row.get('name', '')
            
            try:
                check = self.comprehensive_fundamental_check(ts_code)
                
                if check['fundamental_score'] >= min_score:
                    results.append({
                        'ts_code': ts_code,
                        'name': name,
                        'fundamental_score': check['fundamental_score'],
                        'basis_score': check['basis']['basis_score'],
                        'inventory_score': check['inventory']['inventory_score'],
                        'cost_score': check['cost']['cost_score'],
                        'term_score': check['term_structure']['term_score'],
                        'price_percentile': check['basis']['price_percentile'],
                        'cost_status': check['cost']['cost_status']
                    })
            
            except Exception as e:
                continue
        
        if len(results) == 0:
            print("没有品种通过基本面筛选")
            return pd.DataFrame()
        
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values('fundamental_score', ascending=False).reset_index(drop=True)
        
        print(f"通过基本面筛选: {len(df_result)}只")
        print()
        print("价值品种列表（前15）：")
        print(df_result.head(15)[['ts_code', 'name', 'fundamental_score', 'price_percentile', 'cost_status']].to_string(index=False))
        
        return df_result


if __name__ == '__main__':
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    fv = FundamentalValue(pro)
    
    # 测试
    result = fv.comprehensive_fundamental_check('CU.SHF')
    print(f"沪铜基本面评分: {result['fundamental_score']}")
    print(f"基差评分: {result['basis']}")
    print(f"成本评分: {result['cost']}")
