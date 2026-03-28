#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分模型

四因子模型：
- 趋势强度分（40%）
- 资金认可度分（30%）
- 主线契合度分（20%）
- 风险调整分（10%）
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

from technical_indicators import TechnicalIndicators
from fundamental_filter import FundAnalysis


class MultiFactorScorer:
    """多因子评分器"""
    
    def __init__(self, pro_api):
        self.pro = pro_api
        self.tech = TechnicalIndicators(pro_api)
        self.fund = FundAnalysis(pro_api)
    
    def calculate_trend_score(self, ts_code: str) -> Dict:
        """
        计算趋势强度分 (满分40分)
        
        构成：
        - 均线排列 (10分)
        - MACD位置 (15分)
        - 突破幅度 (10分)
        - 趋势一致性 (5分)
        """
        result = self.tech.get_technical_score(ts_code)
        
        if 'error' in result:
            return {'score': 0, 'details': {}}
        
        scores = result['detail_scores']
        
        # 映射到满分40分
        trend_score = (
            scores.get('ma_score', 0) * 0.4 +           # 25分 -> 10分
            scores.get('macd_score', 0) * 0.6 +         # 25分 -> 15分
            scores.get('break_score', 0) * 0.5 +        # 20分 -> 10分
            scores.get('trend_score', 0) * 0.33         # 15分 -> 5分
        )
        
        return {
            'score': round(trend_score, 2),
            'details': {
                'ma_score': scores.get('ma_score', 0) * 0.4,
                'macd_score': scores.get('macd_score', 0) * 0.6,
                'break_score': scores.get('break_score', 0) * 0.5,
                'trend_consistency': scores.get('trend_score', 0) * 0.33
            },
            'ma_info': result.get('ma_info', {}),
            'macd_info': result.get('macd_info', {}),
            'break_info': result.get('break_info', {}),
            'risks': result.get('risks', [])
        }
    
    def calculate_fund_score(self, ts_code: str) -> Dict:
        """
        计算资金认可度分 (满分30分)
        
        构成：
        - 成交量放大 (10分)
        - 机构持仓变化 (10分)
        - 北向资金流向 (10分)
        """
        scores = {}
        details = {}
        
        # 1. 成交量放大评分 (10分)
        try:
            end_date = datetime.now()
            start_date = (end_date - pd.Timedelta(days=30)).strftime('%Y%m%d')
            
            df = self.pro.daily(ts_code=ts_code, start_date=start_date)
            if df is not None and len(df) > 20:
                latest_vol = df.iloc[0]['vol']
                avg_vol_20 = df['vol'].tail(20).mean()
                volume_ratio = latest_vol / avg_vol_20 if avg_vol_20 > 0 else 0
                
                if volume_ratio >= 3:
                    scores['volume'] = 10
                elif volume_ratio >= 2:
                    scores['volume'] = 8
                elif volume_ratio >= 1.5:
                    scores['volume'] = 6
                elif volume_ratio >= 1:
                    scores['volume'] = 4
                else:
                    scores['volume'] = 2
                
                details['volume_ratio'] = round(volume_ratio, 2)
            else:
                scores['volume'] = 0
                details['volume_ratio'] = 0
        except:
            scores['volume'] = 0
            details['volume_ratio'] = 0
        
        # 2. 机构持仓变化评分 (10分) - 基于基金持仓
        try:
            fund_info = self.fund.get_institutional_holding(ts_code)
            fund_ratio = fund_info.get('fund_ratio', 0)
            
            if fund_ratio >= 10:
                scores['institution'] = 10
            elif fund_ratio >= 5:
                scores['institution'] = 8
            elif fund_ratio >= 3:
                scores['institution'] = 6
            elif fund_ratio >= 1:
                scores['institution'] = 4
            else:
                scores['institution'] = 2
            
            details['fund_ratio'] = fund_ratio
        except:
            scores['institution'] = 0
            details['fund_ratio'] = 0
        
        # 3. 北向资金流向评分 (10分)
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - pd.Timedelta(days=30)).strftime('%Y%m%d')
            
            df_hk = self.pro.hk_hold(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df_hk is not None and len(df_hk) >= 2:
                df_hk = df_hk.sort_values('trade_date')
                latest_vol = df_hk.iloc[-1]['vol']
                first_vol = df_hk.iloc[0]['vol']
                change = (latest_vol - first_vol) / first_vol if first_vol > 0 else 0
                
                if change >= 0.5:  # 增持50%以上
                    scores['north_bound'] = 10
                elif change >= 0.3:
                    scores['north_bound'] = 8
                elif change >= 0.1:
                    scores['north_bound'] = 6
                elif change >= 0:
                    scores['north_bound'] = 4
                else:
                    scores['north_bound'] = 2
                
                details['north_change'] = round(change * 100, 2)
            else:
                scores['north_bound'] = 5
                details['north_change'] = 0
        except:
            scores['north_bound'] = 5
            details['north_change'] = 0
        
        total = sum(scores.values())
        return {
            'score': round(total, 2),
            'details': scores,
            'indicators': details
        }
    
    def calculate_theme_score(self, ts_code: str, industry_concentration: pd.DataFrame) -> Dict:
        """
        计算主线契合度分 (满分20分)
        
        构成：
        - 板块集中度排名 (10分)
        - 题材催化强度 (10分)
        """
        scores = {}
        details = {}
        
        try:
            # 获取股票所属行业
            df_basic = self.pro.stock_basic(ts_code=ts_code)
            if df_basic is None or len(df_basic) == 0:
                return {'score': 0, 'details': {}}
            
            industry = df_basic.iloc[0]['industry']
            
            # 1. 板块集中度排名评分 (10分)
            if industry_concentration is not None and len(industry_concentration) > 0:
                # 找到该行业在集中度排名中的位置
                industry_row = industry_concentration[
                    industry_concentration['industry_name'].str.contains(industry, na=False)
                ]
                
                if len(industry_row) > 0:
                    rank = industry_row.index[0]
                    total = len(industry_concentration)
                    percentile = rank / total
                    
                    if percentile < 0.1:  # 前10%
                        scores['concentration_rank'] = 10
                    elif percentile < 0.2:  # 前20%
                        scores['concentration_rank'] = 8
                    elif percentile < 0.3:
                        scores['concentration_rank'] = 6
                    elif percentile < 0.5:
                        scores['concentration_rank'] = 4
                    else:
                        scores['concentration_rank'] = 2
                    
                    details['industry_rank'] = rank + 1
                    details['industry_total'] = total
                    details['concentration_value'] = industry_row.iloc[0]['concentration']
                else:
                    scores['concentration_rank'] = 5
                    details['industry_rank'] = 'unknown'
            else:
                scores['concentration_rank'] = 5
            
            # 2. 题材催化强度评分 (10分)
            # 简化：基于涨停家数、上涨比例等
            if industry_concentration is not None and len(industry_concentration) > 0:
                industry_row = industry_concentration[
                    industry_concentration['industry_name'].str.contains(industry, na=False)
                ]
                
                if len(industry_row) > 0:
                    limit_up = industry_row.iloc[0]['limit_up_count']
                    up_ratio = industry_row.iloc[0]['up_ratio']
                    
                    # 涨停家数评分
                    if limit_up >= 10:
                        scores['catalyst'] = 10
                    elif limit_up >= 5:
                        scores['catalyst'] = 8
                    elif limit_up >= 3:
                        scores['catalyst'] = 6
                    elif limit_up >= 1:
                        scores['catalyst'] = 4
                    else:
                        scores['catalyst'] = 2
                    
                    details['limit_up_count'] = limit_up
                    details['up_ratio'] = round(up_ratio * 100, 2)
                else:
                    scores['catalyst'] = 5
            else:
                scores['catalyst'] = 5
        
        except Exception as e:
            scores = {'concentration_rank': 0, 'catalyst': 0}
            details = {'error': str(e)}
        
        total = sum(scores.values())
        return {
            'score': round(total, 2),
            'details': scores,
            'indicators': details
        }
    
    def calculate_risk_score(self, ts_code: str) -> Dict:
        """
        计算风险调整分 (满分10分)
        
        构成：
        - 波动率水平 (5分)
        - 流动性评估 (5分)
        """
        scores = {}
        details = {}
        
        try:
            # 获取历史数据
            end_date = datetime.now()
            start_date = (end_date - pd.Timedelta(days=30)).strftime('%Y%m%d')
            
            df = self.pro.daily(ts_code=ts_code, start_date=start_date)
            
            if df is not None and len(df) > 20:
                # 1. 波动率评分 (5分) - 波动率越低得分越高
                df['returns'] = df['close'].pct_change()
                volatility = df['returns'].std() * np.sqrt(252) * 100  # 年化波动率
                
                if volatility < 20:
                    scores['volatility'] = 5
                elif volatility < 30:
                    scores['volatility'] = 4
                elif volatility < 40:
                    scores['volatility'] = 3
                elif volatility < 50:
                    scores['volatility'] = 2
                else:
                    scores['volatility'] = 1
                
                details['volatility_20d'] = round(volatility, 2)
                
                # 2. 流动性评分 (5分) - 日均成交额
                avg_amount = df['amount'].mean()
                
                if avg_amount >= 10:  # 10亿以上
                    scores['liquidity'] = 5
                elif avg_amount >= 5:
                    scores['liquidity'] = 4
                elif avg_amount >= 2:
                    scores['liquidity'] = 3
                elif avg_amount >= 1:
                    scores['liquidity'] = 2
                else:
                    scores['liquidity'] = 1
                
                details['avg_amount'] = round(avg_amount, 2)
            else:
                scores = {'volatility': 2.5, 'liquidity': 2.5}
                details = {'note': '数据不足'}
        
        except:
            scores = {'volatility': 2.5, 'liquidity': 2.5}
            details = {'note': '计算错误'}
        
        total = sum(scores.values())
        return {
            'score': round(total, 2),
            'details': scores,
            'indicators': details
        }
    
    def calculate_total_score(self, ts_code: str, industry_concentration: pd.DataFrame = None) -> Dict:
        """
        计算综合评分
        
        Returns:
            Dict: 包含总分和各维度评分
        """
        # 各维度评分
        trend = self.calculate_trend_score(ts_code)
        fund = self.calculate_fund_score(ts_code)
        theme = self.calculate_theme_score(ts_code, industry_concentration)
        risk = self.calculate_risk_score(ts_code)
        
        # 加权总分 (满分100)
        total_score = (
            trend['score'] * 0.4 +    # 40%
            fund['score'] +           # 30% (已映射到30分)
            theme['score'] +          # 20% (已映射到20分)
            risk['score']             # 10% (已映射到10分)
        )
        
        return {
            'ts_code': ts_code,
            'total_score': round(total_score, 2),
            'trend_score': trend,
            'fund_score': fund,
            'theme_score': theme,
            'risk_score': risk
        }
    
    def rank_stocks(self, stock_list: List[str], industry_concentration: pd.DataFrame = None) -> pd.DataFrame:
        """
        对股票列表进行评分排名
        
        Args:
            stock_list: 股票代码列表
            industry_concentration: 行业集中度数据
            
        Returns:
            pd.DataFrame: 评分排名结果
        """
        results = []
        
        for ts_code in stock_list:
            try:
                score = self.calculate_total_score(ts_code, industry_concentration)
                
                # 获取基本信息
                df_basic = self.pro.stock_basic(ts_code=ts_code)
                if df_basic is not None and len(df_basic) > 0:
                    name = df_basic.iloc[0]['name']
                    industry = df_basic.iloc[0]['industry']
                else:
                    name = ''
                    industry = ''
                
                results.append({
                    'ts_code': ts_code,
                    'name': name,
                    'industry': industry,
                    'total_score': score['total_score'],
                    'trend_score': score['trend_score']['score'],
                    'fund_score': score['fund_score']['score'],
                    'theme_score': score['theme_score']['score'],
                    'risk_score': score['risk_score']['score'],
                    'risks': ','.join(score['trend_score'].get('risks', []))
                })
            except Exception as e:
                print(f"评分失败 {ts_code}: {e}")
                continue
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        return df


if __name__ == '__main__':
    import tushare as ts
    
    pro = ts.pro_api()
    scorer = MultiFactorScorer(pro)
    
    # 测试评分
    result = scorer.calculate_total_score('000001.SZ')
    print(f"综合评分: {result['total_score']}")
    print(f"趋势评分: {result['trend_score']['score']}")
    print(f"资金评分: {result['fund_score']['score']}")
    print(f"主题评分: {result['theme_score']['score']}")
    print(f"风险评分: {result['risk_score']['score']}")
