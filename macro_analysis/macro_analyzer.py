#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观分析模块

基于Tushare宏观经济数据的美林投资时钟分析系统。
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
import sys
import os

# 动态获取 skills 目录路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from tushare_utils.api_utils import APIRateLimiter, retry_on_rate_limit


class MacroAnalyzer:
    """宏观经济分析器"""
    
    def __init__(self, pro_api):
        """
        初始化
        
        Args:
            pro_api: Tushare pro_api 实例
        """
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=300, period=60)
        
        # 缓存数据
        self._data_cache = {}
    
    @retry_on_rate_limit(max_retries=3, sleep_time=10)
    def _fetch_data(self, func_name: str, **kwargs) -> pd.DataFrame:
        """获取数据（带频率限制）"""
        @self.limiter.rate_limit
        def fetch():
            func = getattr(self.pro, func_name)
            return func(**kwargs)
        return fetch()
    
    def get_gdp_data(self, quarters: int = 8) -> pd.DataFrame:
        """
        获取GDP数据
        
        Args:
            quarters: 获取最近几个季度
        """
        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=quarters * 90)
            
            start_q = f"{start_date.year}Q{(start_date.month-1)//3 + 1}"
            end_q = f"{end_date.year}Q{(end_date.month-1)//3 + 1}"
            
            df = self._fetch_data('cn_gdp', start_q=start_q, end_q=end_q)
            
            if df is not None and not df.empty:
                df = df.sort_values('quarter')
                df['gdp_yoy'] = pd.to_numeric(df['gdp_yoy'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取GDP数据失败: {e}")
            return pd.DataFrame()
    
    def get_cpi_data(self, months: int = 24) -> pd.DataFrame:
        """获取CPI数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_m = start_date.strftime('%Y%m')
            end_m = end_date.strftime('%Y%m')
            
            df = self._fetch_data('cn_cpi', start_m=start_m, end_m=end_m)
            
            if df is not None and not df.empty:
                df = df.sort_values('month')
                # 全国CPI同比
                if 'nt_yoy' in df.columns:
                    df['cpi_yoy'] = pd.to_numeric(df['nt_yoy'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取CPI数据失败: {e}")
            return pd.DataFrame()
    
    def get_ppi_data(self, months: int = 24) -> pd.DataFrame:
        """获取PPI数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_m = start_date.strftime('%Y%m')
            end_m = end_date.strftime('%Y%m')
            
            df = self._fetch_data('cn_ppi', start_m=start_m, end_m=end_m)
            
            if df is not None and not df.empty:
                df = df.sort_values('month')
                if 'ppi_yoy' in df.columns:
                    df['ppi_yoy'] = pd.to_numeric(df['ppi_yoy'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取PPI数据失败: {e}")
            return pd.DataFrame()
    
    def get_pmi_data(self, months: int = 24) -> pd.DataFrame:
        """获取PMI数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_m = start_date.strftime('%Y%m')
            end_m = end_date.strftime('%Y%m')
            
            df = self._fetch_data('cn_pmi', start_m=start_m, end_m=end_m)
            
            if df is not None and not df.empty:
                df = df.sort_values('month')
                # PMI指数
                if 'pmi010000' in df.columns:
                    df['pmi'] = pd.to_numeric(df['pmi010000'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取PMI数据失败: {e}")
            return pd.DataFrame()
    
    def get_money_supply(self, months: int = 24) -> pd.DataFrame:
        """获取货币供应量数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_m = start_date.strftime('%Y%m')
            end_m = end_date.strftime('%Y%m')
            
            df = self._fetch_data('cn_m', start_m=start_m, end_m=end_m)
            
            if df is not None and not df.empty:
                df = df.sort_values('month')
                # M2同比
                if 'm2_yoy' in df.columns:
                    df['m2_yoy'] = pd.to_numeric(df['m2_yoy'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取货币供应数据失败: {e}")
            return pd.DataFrame()
    
    def get_social_finance(self, months: int = 24) -> pd.DataFrame:
        """获取社融数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_m = start_date.strftime('%Y%m')
            end_m = end_date.strftime('%Y%m')
            
            df = self._fetch_data('sf_month', start_m=start_m, end_m=end_m)
            
            if df is not None and not df.empty:
                df = df.sort_values('month')
            
            return df
        except Exception as e:
            print(f"  获取社融数据失败: {e}")
            return pd.DataFrame()
    
    def get_lpr_data(self, months: int = 24) -> pd.DataFrame:
        """获取LPR利率数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            df = self._fetch_data('shibor_lpr', start_date=start_date_str, end_date=end_date_str)
            
            if df is not None and not df.empty:
                df = df.sort_values('date')
                # 1年期LPR
                if '1y' in df.columns:
                    df['lpr_1y'] = pd.to_numeric(df['1y'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"  获取LPR数据失败: {e}")
            return pd.DataFrame()
    
    def detect_economic_phase(self) -> Tuple[str, float]:
        """
        判断经济周期阶段（美林时钟）
        
        Returns:
            (阶段名称, 置信度)
        """
        # 获取数据
        gdp_df = self.get_gdp_data(quarters=4)
        cpi_df = self.get_cpi_data(months=12)
        
        if gdp_df.empty or cpi_df.empty:
            return "数据不足", 0.0
        
        # 计算GDP趋势
        gdp_latest = gdp_df['gdp_yoy'].iloc[-1] if 'gdp_yoy' in gdp_df.columns else None
        gdp_prev = gdp_df['gdp_yoy'].iloc[-2] if len(gdp_df) >= 2 else None
        gdp_trend = "up" if gdp_latest and gdp_prev and gdp_latest > gdp_prev else "down"
        
        # 计算CPI趋势
        cpi_latest = cpi_df['cpi_yoy'].iloc[-1] if 'cpi_yoy' in cpi_df.columns else None
        cpi_prev = cpi_df['cpi_yoy'].iloc[-2] if len(cpi_df) >= 2 else None
        cpi_trend = "up" if cpi_latest and cpi_prev and cpi_latest > cpi_prev else "down"
        
        # 判断周期阶段
        phase_map = {
            ("up", "down"): "复苏期",
            ("up", "up"): "过热期",
            ("down", "up"): "滞胀期",
            ("down", "down"): "衰退期"
        }
        
        phase = phase_map.get((gdp_trend, cpi_trend), "不确定")
        
        # 计算置信度（基于数据完整性和趋势明显性）
        confidence = 0.5
        if gdp_latest is not None and cpi_latest is not None:
            confidence += 0.25
        if gdp_prev is not None and cpi_prev is not None:
            confidence += 0.25
        
        return phase, confidence
    
    def get_asset_allocation(self) -> Dict:
        """
        根据经济周期给出资产配置建议
        
        Returns:
            资产配置建议字典
        """
        phase, confidence = self.detect_economic_phase()
        
        # 美林时钟配置建议
        allocation_map = {
            "复苏期": {
                "股票": {"weight": "60-80%", "level": "超配", "score": 70},
                "债券": {"weight": "20-30%", "level": "标配", "score": 25},
                "现金": {"weight": "5-10%", "level": "低配", "score": 5},
                "商品": {"weight": "5-10%", "level": "低配", "score": 5}
            },
            "过热期": {
                "股票": {"weight": "40-60%", "level": "标配", "score": 50},
                "债券": {"weight": "10-20%", "level": "低配", "score": 15},
                "现金": {"weight": "5-10%", "level": "低配", "score": 5},
                "商品": {"weight": "20-30%", "level": "超配", "score": 30}
            },
            "滞胀期": {
                "股票": {"weight": "20-30%", "level": "低配", "score": 25},
                "债券": {"weight": "30-40%", "level": "标配", "score": 35},
                "现金": {"weight": "30-40%", "level": "超配", "score": 35},
                "商品": {"weight": "10-20%", "level": "标配", "score": 15}
            },
            "衰退期": {
                "股票": {"weight": "10-20%", "level": "低配", "score": 15},
                "债券": {"weight": "60-80%", "level": "超配", "score": 70},
                "现金": {"weight": "10-20%", "level": "标配", "score": 15},
                "商品": {"weight": "5-10%", "level": "低配", "score": 5}
            }
        }
        
        allocation = allocation_map.get(phase, allocation_map["复苏期"])
        
        # A股风格建议
        style_map = {
            "复苏期": {
                "优先": ["成长股", "周期股"],
                "关注": ["科技", "新能源", "化工"]
            },
            "过热期": {
                "优先": ["周期股", "金融股"],
                "关注": ["有色", "煤炭", "券商"]
            },
            "滞胀期": {
                "优先": ["防御股", "消费股"],
                "关注": ["医药", "公用事业", "食品饮料"]
            },
            "衰退期": {
                "优先": ["成长股", "防御股"],
                "关注": ["科技", "医药", "债券"]
            }
        }
        
        return {
            "phase": phase,
            "confidence": confidence,
            "allocation": allocation,
            "style": style_map.get(phase, {})
        }
    
    def analyze_all_indicators(self) -> Dict:
        """
        分析所有宏观指标
        
        Returns:
            指标分析结果字典
        """
        results = {}
        
        # GDP
        gdp_df = self.get_gdp_data(quarters=4)
        if not gdp_df.empty and 'gdp_yoy' in gdp_df.columns:
            latest = gdp_df.iloc[-1]
            prev = gdp_df.iloc[-2] if len(gdp_df) >= 2 else None
            results['GDP'] = {
                'value': f"{latest['gdp_yoy']:.1f}%",
                'qoq': f"{latest['gdp_yoy'] - prev['gdp_yoy']:+.1f}pp" if prev is not None else "N/A",
                'trend': self._get_trend_symbol(latest['gdp_yoy'], prev['gdp_yoy'] if prev is not None else None)
            }
        
        # CPI
        cpi_df = self.get_cpi_data(months=12)
        if not cpi_df.empty and 'cpi_yoy' in cpi_df.columns:
            latest = cpi_df.iloc[-1]
            prev = cpi_df.iloc[-2] if len(cpi_df) >= 2 else None
            results['CPI'] = {
                'value': f"{latest['cpi_yoy']:.1f}%",
                'qoq': f"{latest['cpi_yoy'] - prev['cpi_yoy']:+.1f}pp" if prev is not None else "N/A",
                'trend': self._get_trend_symbol(latest['cpi_yoy'], prev['cpi_yoy'] if prev is not None else None)
            }
        
        # PPI
        ppi_df = self.get_ppi_data(months=12)
        if not ppi_df.empty and 'ppi_yoy' in ppi_df.columns:
            latest = ppi_df.iloc[-1]
            prev = ppi_df.iloc[-2] if len(ppi_df) >= 2 else None
            results['PPI'] = {
                'value': f"{latest['ppi_yoy']:.1f}%",
                'qoq': f"{latest['ppi_yoy'] - prev['ppi_yoy']:+.1f}pp" if prev is not None else "N/A",
                'trend': self._get_trend_symbol(latest['ppi_yoy'], prev['ppi_yoy'] if prev is not None else None)
            }
        
        # PMI
        pmi_df = self.get_pmi_data(months=12)
        if not pmi_df.empty and 'pmi' in pmi_df.columns:
            latest = pmi_df.iloc[-1]
            prev = pmi_df.iloc[-2] if len(pmi_df) >= 2 else None
            results['PMI'] = {
                'value': f"{latest['pmi']:.1f}",
                'qoq': f"{latest['pmi'] - prev['pmi']:+.1f}" if prev is not None else "N/A",
                'trend': self._get_trend_symbol(latest['pmi'], prev['pmi'] if prev is not None else None)
            }
        
        # M2
        m_df = self.get_money_supply(months=12)
        if not m_df.empty and 'm2_yoy' in m_df.columns:
            latest = m_df.iloc[-1]
            prev = m_df.iloc[-2] if len(m_df) >= 2 else None
            results['M2'] = {
                'value': f"{latest['m2_yoy']:.1f}%",
                'qoq': f"{latest['m2_yoy'] - prev['m2_yoy']:+.1f}pp" if prev is not None else "N/A",
                'trend': self._get_trend_symbol(latest['m2_yoy'], prev['m2_yoy'] if prev is not None else None)
            }
        
        # 社融
        sf_df = self.get_social_finance(months=12)
        if not sf_df.empty:
            latest = sf_df.iloc[-1]
            prev = sf_df.iloc[-2] if len(sf_df) >= 2 else None
            # 社融累计同比
            if 'inc_cum_yoy' in latest:
                val = pd.to_numeric(latest['inc_cum_yoy'], errors='coerce')
                prev_val = pd.to_numeric(prev['inc_cum_yoy'], errors='coerce') if prev is not None else None
                results['社融'] = {
                    'value': f"{val:.1f}%" if val else "N/A",
                    'qoq': f"{val - prev_val:+.1f}pp" if val and prev_val else "N/A",
                    'trend': self._get_trend_symbol(val, prev_val)
                }
        
        # LPR
        lpr_df = self.get_lpr_data(months=12)
        if not lpr_df.empty and 'lpr_1y' in lpr_df.columns:
            latest = lpr_df.iloc[-1]
            prev = lpr_df.iloc[-2] if len(lpr_df) >= 2 else None
            val = latest['lpr_1y']
            prev_val = prev['lpr_1y'] if prev is not None else None
            results['LPR(1Y)'] = {
                'value': f"{val:.2f}%",
                'qoq': f"{(val - prev_val)*100:+.0f}bp" if prev_val else "N/A",
                'trend': self._get_trend_symbol(val, prev_val, inverse=True)  # 利率越低越好
            }
        
        return results
    
    def _get_trend_symbol(self, current, previous, inverse=False) -> str:
        """获取趋势符号"""
        if previous is None or pd.isna(previous) or pd.isna(current):
            return "→ 平稳"
        
        diff = current - previous
        if inverse:  # 反向指标（如利率越低越好）
            diff = -diff
        
        if diff > 0.1:
            return "↗ 回升"
        elif diff < -0.1:
            return "↘ 下行"
        else:
            return "→ 平稳"
    
    def full_analysis(self) -> Dict:
        """
        执行完整宏观分析
        
        Returns:
            完整分析结果
        """
        print("=" * 80)
        print("宏观经济分析报告")
        print("=" * 80)
        print(f"报告时间: {datetime.now().strftime('%Y-%m-%d')}")
        print()
        
        # 1. 经济周期判断
        print("【经济周期判断】")
        phase, confidence = self.detect_economic_phase()
        print(f"当前阶段: {phase}（置信度: {confidence*100:.0f}%）")
        print()
        
        # 2. 指标分析
        print("【关键指标监控】")
        indicators = self.analyze_all_indicators()
        
        print(f"{'指标':<10} {'最新值':<10} {'环比':<10} {'趋势':<10}")
        print("-" * 50)
        for name, data in indicators.items():
            print(f"{name:<10} {data['value']:<10} {data['qoq']:<10} {data['trend']:<10}")
        print()
        
        # 3. 资产配置建议
        print("【美林时钟配置建议】")
        allocation = self.get_asset_allocation()
        print(f"{phase}建议配置:")
        for asset, config in allocation['allocation'].items():
            print(f"  {asset}: {config['weight']} ({config['level']})")
        print()
        
        # 4. A股风格建议
        if allocation['style']:
            print("A股风格建议:")
            if '优先' in allocation['style']:
                print(f"  优先配置: {', '.join(allocation['style']['优先'])}")
            if '关注' in allocation['style']:
                print(f"  重点关注: {', '.join(allocation['style']['关注'])}")
        print()
        
        # 5. 风险提示
        print("【风险提示】")
        risks = []
        if 'CPI' in indicators:
            cpi_val = float(indicators['CPI']['value'].replace('%', ''))
            if cpi_val < 1:
                risks.append(f"⚠️ 通缩压力持续，CPI({cpi_val}%)低于1%需警惕")
            elif cpi_val > 3:
                risks.append(f"⚠️ 通胀压力上升，CPI({cpi_val}%)超过3%")
        
        if 'PPI' in indicators:
            ppi_val = float(indicators['PPI']['value'].replace('%', ''))
            if ppi_val < 0:
                risks.append(f"⚠️ PPI仍为负值({ppi_val}%)，企业盈利恢复需观察")
        
        if 'PMI' in indicators:
            pmi_val = float(indicators['PMI']['value'])
            if pmi_val < 50:
                risks.append(f"⚠️ PMI低于50荣枯线，经济处于收缩区间")
        
        if risks:
            for risk in risks:
                print(risk)
        else:
            print("✓ 当前宏观环境无重大风险")
        
        print()
        print("=" * 80)
        
        return {
            "phase": phase,
            "confidence": confidence,
            "indicators": indicators,
            "allocation": allocation,
            "risks": risks
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
    
    # 创建分析器并运行
    analyzer = MacroAnalyzer(pro)
    result = analyzer.full_analysis()
