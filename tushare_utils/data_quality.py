#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量检查模块

提供数据预处理、异常检测、新股/停牌过滤等功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """数据质量检查器"""
    
    def __init__(self):
        self.issues = []
    
    def check_price_data(self, df: pd.DataFrame, ts_code: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        检查价格数据质量
        
        Returns:
            (处理后的数据, 问题标签列表)
        """
        issues = []
        
        if df is None or df.empty:
            return df, ['数据为空']
        
        # 1. 检查除权缺口（未复权的价格跳空）
        if 'close' in df.columns:
            daily_change = df['close'].pct_change().abs()
            abnormal_gaps = daily_change[daily_change > 0.2]  # 单日涨跌>20%
            if len(abnormal_gaps) > 0:
                issues.append('除权缺口')
        
        # 2. 检查价格连续性（缺失交易日）
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date')
            date_diff = pd.to_datetime(df['trade_date']).diff().dt.days
            long_gaps = date_diff[date_diff > 7]  # 超过7天的跳空
            if len(long_gaps) > 2:  # 允许偶尔的节假日
                issues.append('价格 discontinuity')
        
        # 3. 检查零值/负值
        if 'close' in df.columns and (df['close'] <= 0).any():
            issues.append('价格异常值')
        
        # 4. 检查成交量异常
        if 'volume' in df.columns:
            if (df['volume'] == 0).all():
                issues.append('无成交量')
            elif (df['volume'] == 0).any():
                issues.append('部分停牌')
        
        return df, issues
    
    def check_fundamental_data(self, df: pd.DataFrame) -> List[str]:
        """
        检查财务数据异常（红旗指标）
        
        只标记，不剔除
        """
        issues = []
        
        if df is None or df.empty:
            return ['财务数据为空']
        
        try:
            # 红旗1：应收账款增速 > 营收增速×1.5
            if 'accounts_receiv' in df.columns and 'total_revenue' in df.columns:
                ar_growth = df['accounts_receiv'].pct_change()
                revenue_growth = df['total_revenue'].pct_change()
                if (ar_growth > revenue_growth * 1.5).any():
                    issues.append('应收账款异常')
            
            # 红旗2：经营现金流/净利润 < 0.6 持续多年
            if 'n_cashflow_act' in df.columns and 'net_profit' in df.columns:
                cashflow_ratio = (df['n_cashflow_act'] / df['net_profit']).mean()
                if cashflow_ratio < 0.6:
                    issues.append('现金流质量差')
            
            # 红旗3：存贷双高（货币资金>20%资产 且 有息负债>30%资产）
            if 'money_cap' in df.columns and 'total_assets' in df.columns and \
               'total_liab' in df.columns:
                cash_ratio = df['money_cap'].iloc[-1] / df['total_assets'].iloc[-1]
                debt_ratio = df['total_liab'].iloc[-1] / df['total_assets'].iloc[-1]
                if cash_ratio > 0.2 and debt_ratio > 0.3:
                    issues.append('存贷双高')
            
            # 红旗4：商誉占比过高
            if 'goodwill' in df.columns and 'total_assets' in df.columns:
                goodwill_ratio = df['goodwill'].iloc[-1] / df['total_assets'].iloc[-1]
                if goodwill_ratio > 0.3:
                    issues.append('高商誉')
            
            # 红旗5：ROE 波动过大
            if 'roe' in df.columns:
                roe_std = df['roe'].std()
                if roe_std > 10:  # ROE标准差>10
                    issues.append('盈利波动大')
                    
        except Exception as e:
            logger.warning(f"财务数据检查异常: {e}")
        
        return issues


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self, api=None):
        self.api = api
        self.quality_checker = DataQualityChecker()
    
    def filter_new_stocks(self, codes: List[str], min_listing_days: int = 60) -> Tuple[List[str], List[str]]:
        """
        过滤新股/次新股
        
        Returns:
            (合格股票列表, 被过滤股票列表)
        """
        qualified = []
        filtered = []
        
        for code in codes:
            try:
                # 获取上市日期
                stock_info = self.api.stock_basic(ts_code=code, fields='ts_code,list_date')
                if stock_info.empty:
                    continue
                
                list_date = pd.to_datetime(stock_info['list_date'].iloc[0])
                listing_days = (datetime.now() - list_date).days
                
                if listing_days >= min_listing_days:
                    qualified.append(code)
                else:
                    filtered.append(code)
                    
            except Exception as e:
                logger.warning(f"获取 {code} 上市日期失败: {e}")
                # 无法判断时默认保留
                qualified.append(code)
        
        return qualified, filtered
    
    def mark_suspended(self, df: pd.DataFrame) -> pd.DataFrame:
        """标记停牌状态"""
        if df is None or df.empty or 'volume' not in df.columns:
            return df
        
        df = df.copy()
        df['is_suspended'] = df['volume'] == 0
        
        # 最近一日是否停牌
        df['recently_suspended'] = df['is_suspended'].iloc[-5:].any() if len(df) >= 5 else False
        
        return df
    
    def calculate_volatility_tag(self, df: pd.DataFrame) -> Optional[str]:
        """计算波动率标签"""
        if df is None or df.empty or 'close' not in df.columns:
            return None
        
        try:
            returns = df['close'].pct_change().dropna()
            if len(returns) < 20:
                return None
            
            # 20日年化波动率
            volatility = returns.std() * np.sqrt(252)
            
            # 近20日最大涨跌
            max_change = returns.abs().max()
            
            if volatility > 0.6:  # 年化波动>60%
                return '极高波动'
            elif volatility > 0.4:  # 年化波动>40%
                return '高波动'
            elif max_change > 0.15:  # 单日涨跌>15%
                return '异动'
            
        except Exception as e:
            logger.warning(f"计算波动率标签失败: {e}")
        
        return None
    
    def process_stock_data(self, df: pd.DataFrame, ts_code: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        完整的股票数据预处理流程
        
        Returns:
            (处理后的数据, 问题标签列表)
        """
        issues = []
        
        # 1. 质量检查
        df, quality_issues = self.quality_checker.check_price_data(df, ts_code)
        issues.extend(quality_issues)
        
        # 2. 标记停牌
        df = self.mark_suspended(df)
        if 'recently_suspended' in df.columns and df['recently_suspended'].any():
            issues.append('近期停牌')
        
        # 3. 波动率标签
        vol_tag = self.calculate_volatility_tag(df)
        if vol_tag:
            issues.append(vol_tag)
        
        return df, issues


class FuturesDataProcessor:
    """期货数据处理器"""
    
    def __init__(self, api=None):
        self.api = api
    
    def check_contract_expiry(self, contract_code: str) -> Tuple[int, str]:
        """
        检查合约到期时间
        
        Returns:
            (剩余天数, 标签)
        """
        try:
            # 解析合约到期月份
            # 格式: RB2505.SH 表示 2025年5月到期
            import re
            match = re.search(r'(\d{4})', contract_code)
            if not match:
                return 999, ''
            
            year_month = match.group(1)
            year = 2000 + int(year_month[:2])
            month = int(year_month[2:])
            
            # 期货合约通常在到期月前一个月的某个日期到期
            # 简化处理：假设到期日为到期月的第15日
            expiry_date = datetime(year, month, 15)
            days_to_expiry = (expiry_date - datetime.now()).days
            
            if days_to_expiry < 0:
                return days_to_expiry, '已到期'
            elif days_to_expiry < 7:
                return days_to_expiry, '即将到期'
            elif days_to_expiry < 15:
                return days_to_expiry, '临近换月'
            else:
                return days_to_expiry, ''
                
        except Exception as e:
            logger.warning(f"检查合约到期时间失败 {contract_code}: {e}")
            return 999, ''
    
    def process_futures_data(self, df: pd.DataFrame, contract_code: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        期货数据预处理
        
        Returns:
            (处理后的数据, 问题标签列表)
        """
        issues = []
        
        if df is None or df.empty:
            return df, ['数据为空']
        
        # 1. 检查合约到期
        days_to_expiry, expiry_tag = self.check_contract_expiry(contract_code)
        if expiry_tag:
            issues.append(expiry_tag)
        
        # 2. 检查流动性
        if 'volume' in df.columns and 'amount' in df.columns:
            avg_volume = df['volume'].mean()
            avg_amount = df['amount'].mean()
            
            if avg_volume < 1000:  # 日均成交<1000手
                issues.append('流动性差')
            elif avg_amount < 10000000:  # 日均成交额<1000万
                issues.append('成交额低')
        
        # 3. 波动率检查
        if 'close' in df.columns:
            returns = df['close'].pct_change().dropna()
            if len(returns) >= 20:
                volatility = returns.std() * np.sqrt(252)
                if volatility > 0.5:  # 期货波动通常较大
                    issues.append('高波动')
                
                # ATR计算
                atr = self.calculate_atr(df)
                if atr and atr > df['close'].iloc[-1] * 0.05:  # ATR>5%
                    issues.append('ATR异常')
        
        return df, issues
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """计算ATR"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean().iloc[-1]
            
            return atr
        except:
            return None


def create_default_processor(api=None) -> DataPreprocessor:
    """创建默认预处理器"""
    return DataPreprocessor(api)


def create_futures_processor(api=None) -> FuturesDataProcessor:
    """创建期货预处理器"""
    return FuturesDataProcessor(api)
